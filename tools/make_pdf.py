"""
make_pdf.py - Build CashFlowIQ_Code_Explanation.pdf (development tool, needs reportlab).

    python tools/make_pdf.py --url https://your-app.streamlit.app

The rule list, problem catalog, thresholds, code excerpts and sample-case results
are generated LIVE from the project code, so the PDF always matches the program.
"""
import argparse
import inspect
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reportlab.lib import colors                                     # noqa: E402
from reportlab.lib.enums import TA_CENTER                            # noqa: E402
from reportlab.lib.pagesizes import A4                               # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm                                   # noqa: E402
from reportlab.pdfbase import pdfmetrics                             # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont                         # noqa: E402
from reportlab.platypus import (                                     # noqa: E402
    PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from engine import certainty, consultation, inference_engine, working_memory  # noqa: E402,F401
from engine.diagnosis import diagnose                                # noqa: E402
from knowledge_base import formulas, load_threshold_table            # noqa: E402
from knowledge_base.problems import PROBLEMS                         # noqa: E402
from knowledge_base.rule_model import RaiseProblem                   # noqa: E402
from knowledge_base.rules import RULES, RULE_GROUPS                  # noqa: E402
from sample_cases import SAMPLE_CASES                                # noqa: E402

TEAL = colors.HexColor("#0F766E")
LIGHT = colors.HexColor("#E6F2F1")


# ----------------------------------------------------------------------
# Fonts: use a Unicode TTF if available (for →, ≥, ×), else Helvetica
# ----------------------------------------------------------------------
def _register_fonts():
    candidates = [
        ("Body", ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                  "/Library/Fonts/Arial Unicode.ttf"]),
        ("Body-Bold", ["C:/Windows/Fonts/arialbd.ttf",
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]),
        ("Mono", ["C:/Windows/Fonts/consola.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]),
    ]
    found = {}
    for name, paths in candidates:
        for p in paths:
            if Path(p).exists():
                pdfmetrics.registerFont(TTFont(name, p))
                found[name] = name
                break
    body = found.get("Body", "Helvetica")
    bold = found.get("Body-Bold", "Helvetica-Bold")
    mono = found.get("Mono", "Courier")
    if body == "Body" and bold == "Body-Bold":
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                      italic="Body", boldItalic="Body-Bold")
    return body, bold, mono, body != "Helvetica"


BODY, BOLD, MONO, UNICODE = _register_fonts()


def clean(text: str) -> str:
    """Remove emoji / non-BMP characters; ASCII-fy arrows if no Unicode font."""
    text = "".join(ch for ch in str(text) if ord(ch) < 0x2600 or ch in "→≥≤×−")
    if not UNICODE:
        for a, b in {"→": "->", "≥": ">=", "≤": "<=", "×": "x", "−": "-"}.items():
            text = text.replace(a, b)
    return text


def md_inline(text: str) -> str:
    """Escape for reportlab and convert **bold** / `code` markdown."""
    text = escape(clean(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", rf"<font face='{MONO}'>\1</font>", text)
    return text


# ----------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------
ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontName=BOLD, fontSize=24, leading=30,
                            textColor=TEAL),
    "subtitle": ParagraphStyle("st", parent=ss["Normal"], fontName=BODY, fontSize=13, leading=18,
                               alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName=BOLD, fontSize=16, textColor=TEAL,
                         spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=BOLD, fontSize=12.5, spaceBefore=8,
                         spaceAfter=4),
    "body": ParagraphStyle("b", parent=ss["Normal"], fontName=BODY, fontSize=10, leading=14,
                           spaceAfter=5),
    "bullet": ParagraphStyle("bl", parent=ss["Normal"], fontName=BODY, fontSize=10, leading=14,
                             leftIndent=14, bulletIndent=4, spaceAfter=2),
    "cell": ParagraphStyle("c", parent=ss["Normal"], fontName=BODY, fontSize=7.6, leading=9.4),
    "cellb": ParagraphStyle("cb", parent=ss["Normal"], fontName=BOLD, fontSize=7.8, leading=9.6,
                            textColor=colors.white),
    "code": ParagraphStyle("code", parent=ss["Code"], fontName=MONO, fontSize=7.4, leading=9,
                           backColor=colors.HexColor("#F5F7F7"), borderPadding=5,
                           borderColor=colors.HexColor("#d9dee3"), borderWidth=0.5,
                           spaceBefore=4, spaceAfter=8),
}


def P(text, style="body"):
    return Paragraph(md_inline(text), S[style])


def bullets(items):
    return [Paragraph(md_inline(i), S["bullet"], bulletText="•") for i in items]


def table(header, rows, widths, font_size=None):
    data = [[Paragraph(md_inline(h), S["cellb"]) for h in header]]
    data += [[Paragraph(md_inline(c), S["cell"]) for c in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c5ccd3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def code_block(obj_or_text, max_lines=60):
    src = obj_or_text if isinstance(obj_or_text, str) else inspect.getsource(obj_or_text)
    lines = clean(src).rstrip().splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["    ..."]
    return Preformatted("\n".join(lines), S["code"])


def then_text(rule):
    parts = []
    for a in rule.actions:
        if isinstance(a, RaiseProblem):
            parts.append(f"PROBLEM: {PROBLEMS[a.key]['title']} [{PROBLEMS[a.key]['severity']}]")
        else:
            parts.append(a.describe())
    return "; ".join(parts)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm, "CashFlow IQ – Code Explanation · For educational purposes only "
                      "– not financial advice")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ----------------------------------------------------------------------
# Content
# ----------------------------------------------------------------------
def build(url: str, out: Path):
    kinds = Counter(r.kind for r in RULES)
    W = A4[0] - 4 * cm
    story = []

    # ---------------- Title page ----------------
    story += [Spacer(1, 4 * cm), P("CashFlow IQ", "title"),
              P("Business Liquidity & Cash Flow Decision Expert System", "subtitle"),
              Spacer(1, 0.6 * cm),
              P("Code Explanation – Rule-Based Expert System in Python with a Streamlit UI",
                "subtitle"),
              Spacer(1, 1.5 * cm)]
    info = [
        ["Live application", url],
        ["Rules", f"{len(RULES)} (unique IDs R01–R{len(RULES):02d}) in {len(RULE_GROUPS)} groups"],
        ["Rule types", f"{kinds['COMPUTE']} COMPUTE · {kinds['DECISION']} DECISION · "
                       f"{kinds['CLASSIFY'] + kinds['STATUS']} classification/status"],
        ["Problem catalog", f"{len(PROBLEMS)} problems with severity and decisions"],
        ["Reasoning", "Forward chaining (custom engine) + MYCIN certainty factors"],
        ["Interfaces", "Step-by-step Consultation wizard and one-page Quick Diagnosis"],
        ["Technology", "Python 3.12+, Streamlit, pandas, pytest"],
        ["Student", "______________________________"],
        ["Roll number", "______________________________"],
        ["Date", date.today().strftime("%d %B %Y")],
    ]
    story.append(table(["Item", "Details"], info, [4.5 * cm, W - 4.5 * cm]))
    story.append(PageBreak())

    # ---------------- 1. Overview ----------------
    story += [P("1. Project overview", "h1"),
              P("CashFlow IQ is a **rule-based expert system** for small and medium businesses in "
                "Pakistan (currency PKR). It works like a *doctor for business cash flow*: the owner "
                "enters figures and answers Yes / No / Not sure symptom questions; the system computes ratios "
                "(derived facts), diagnoses liquidity problems, and recommends cash-management "
                "decisions, each with a confidence percentage and an explanation."),
              P("**Symptoms/figures → derived facts (ratios) → diagnosis (problems) → treatment "
                "(decisions)**"),
              P("It uses **no machine learning and no AI services**. Every conclusion comes from "
                "explicit IF-THEN rules that can be listed, traced and explained. The inference engine "
                "is written from scratch (the `experta` library is not used)."),
              P("Inputs", "h2")]
    story += bullets([
        "Business profile: name, type (retail, wholesale, manufacturing, services, restaurant, "
        "trading) and season (peak, normal, off-season).",
        "Figures: cash in hand, bank balance, receivables + collection days, payables + payment "
        "days, inventory + days to sell stock, monthly sales, gross margin %, fixed expenses, "
        "short-term loans, monthly installment, other current liabilities.",
        "Nine symptom questions answered Yes / No / Not sure (nothing pre-selected), e.g. "
        "delaying suppliers, customers paying late, stock piling up, sales up but cash down, "
        "using personal money, planning expansion, one customer > 40% of sales, overdue tax, "
        "running finance fully used.",
    ])
    story += [P("Outputs", "h2")]
    story += bullets([
        "Status: **Healthy / Watch / Risky / Crisis** and a health score (0–100) – or "
        "**Insufficient data** (no score) when essential facts are missing.",
        "Ten key ratios (current, quick and cash ratio, cash runway, net monthly cash flow, cash "
        "conversion cycle, debt-service ratio, receivables/sales, inventory/sales, working capital).",
        "Diagnosed problems with severity and confidence; ranked decisions with reasons.",
        "HOW explanation (rule-firing trace) and WHY explanations.",
    ])

    # ---------------- 2. Architecture ----------------
    story += [P("2. Architecture – the six expert-system components", "h1")]
    comp = [
        ["User Interface", "app.py, views/, ui/fields.py, ui/report.py", "Consultation wizard "
         "(6 steps + review) and Quick Diagnosis (sidebar: For business owners), Knowledge Base "
         "and Knowledge Acquisition (For experts), About (Info); one shared plain-English report."],
        ["Knowledge Base", "knowledge_base/", f"rules.py ({len(RULES)} rules as data), problems.py "
         "(catalog), formulas.py (zero-safe formulas), questions.py (questions with ask_if), "
         "thresholds.json (all numbers)."],
        ["Working Memory", "engine/working_memory.py", "Fact base: input facts (CF 1.0), derived "
         "facts, problems with combined CF, strengths, missing facts, warnings – each tagged with "
         "its source rule."],
        ["Inference Engine", "engine/inference_engine.py", "Forward chaining: match → conflict "
         "resolution → fire, repeated until no rule matches or a rule HALTs. Keeps a full trace."],
        ["Explanation Facility", "engine/explanation.py, engine/consultation.py", "HOW: ordered "
         "trace with matched facts. WHY: why each question is asked (from the rule base) and why "
         "each action was recommended."],
        ["Knowledge Acquisition", "views/admin.py", "Edit and validate thresholds in the browser; "
         "download/upload thresholds.json."],
    ]
    story.append(table(["Component", "Code", "Responsibility"], comp,
                       [3.4 * cm, 4.2 * cm, W - 7.6 * cm]))
    story += [Spacer(1, 6), P("Data flow", "h2"),
              code_block("User → UI (consultation or form) → WorkingMemory(input facts)\n"
                         "        → InferenceEngine(RULES, thresholds).run(wm)\n"
                         "             data checks first (G0); HALT if essentials are missing\n"
                         "             repeat: MATCH → RESOLVE → FIRE (update wm, append trace)\n"
                         "        → diagnosis.py packages: status, score, problems, decisions\n"
                         "        → explanation.py: HOW table, WHY text → UI"),
              P("**Why separate knowledge from the engine?** The engine is generic (it knows "
                "nothing about cash flow), so knowledge can be changed without touching code, "
                "the same engine could run another domain, rules can be displayed and explained, "
                "and each part can be tested independently.")]
    story.append(PageBreak())

    # ---------------- 3. Code walkthrough ----------------
    story += [P("3. Code walkthrough", "h1"),
              P("3.1 Rule representation (knowledge_base/rule_model.py)", "h2"),
              P("A rule is a frozen dataclass: `id`, `group`, `description`, `conditions` "
                "(all must be true – AND), `actions`, certainty factor `cf` and `priority`. "
                "Conditions compare a fact with a constant, a threshold reference `T(name)` or "
                "another fact `F(name)`."),
              code_block(inspect.getsource(sys.modules["knowledge_base.rule_model"].Rule), 40),
              P("Example rules from rules.py:", "body"),
              code_block('Rule("R17", G2, "Runway under 30 days: cash runs out within a month.",\n'
                         '     (C("runway_days", "<", T("crisis_runway_days")),),\n'
                         '     (Assert("runway_band", "critical"),\n'
                         '      RaiseProblem("cash_runs_out_within_month")), 0.95, P_BAND),\n\n'
                         'Rule("R22", G2, "Burning cash AND under 30 days of runway = imminent crisis",\n'
                         '     (C("cf_band", "==", "negative"), C("runway_band", "==", "critical")),\n'
                         '     (RaiseProblem("imminent_cash_crisis"),), 0.95, P_CHAIN),'),
              P("3.2 Zero-safe formulas (knowledge_base/formulas.py)", "h2"),
              P("COMPUTE rules call named formulas. Every division uses `safe_div`, which returns "
                "`None` when the denominator is 0; conditions on a `None` fact are false, so "
                "dependent rules simply do not fire."),
              code_block(formulas.safe_div),
              code_block(formulas.runway_days),
              code_block(formulas.health_score),
              P("3.3 Working memory (engine/working_memory.py)", "h2"),
              P("When a problem is raised a second time, the CFs are combined instead of overwritten. "
                "The problem is also stored as a fact `problem:<key>` so chained rules can test it."),
              code_block(working_memory.WorkingMemory.add_problem),
              P("3.4 Inference engine (engine/inference_engine.py)", "h2"),
              P("The recognise-act cycle. `match` builds the conflict set, `resolve` applies the "
                "conflict-resolution strategy, `fire` executes actions and records the trace."),
              code_block(inference_engine.evaluate_condition),
              code_block(inference_engine.InferenceEngine.match),
              code_block(inference_engine.InferenceEngine.resolve),
              code_block(inference_engine.InferenceEngine.run),
              P("3.5 Certainty factors (engine/certainty.py)", "h2"),
              code_block(certainty.conclusion_cf),
              code_block(certainty.combine),
              P("Example: R28 gives *Weak credit control* CF 0.60 and R59 gives 0.50 → "
                "0.60 + 0.50 × (1 − 0.60) = **0.80**."),
              P("**\"Not sure\" answers.** Each warning-sign question offers Yes / No / Not sure "
                "with nothing pre-selected; Next and Run diagnosis are blocked until each shown "
                "question is answered (questions skipped by ask_if still default to No). "
                "\"Not sure\" is stored as the value `not_sure` with CF = `not_sure_cf` (0.5, in "
                "thresholds.json). The `yes` condition matches it, so the existing rule "
                "conclusion CF = rule CF × min(CF of matched facts) halves the conclusion – "
                "e.g. R69 overdue tax 0.90 → 0.45. Rules needing \"No\" (`not_yes`) do not fire. "
                "It combines as usual: R28 0.60 with R59 on Not sure (0.25) → **0.70**. A problem "
                "raised only from Not-sure answers is shown as *Possible* with \"You weren't sure "
                "about this — worth checking.\", and the HOW trace shows *Not sure (CF 0.50)* "
                "and the reduced CF."),
              ]
    story += [P("3.6 Conflict resolution and priorities", "h2"),
              table(["Priority", "Rule kind", "Purpose"], [
                  ["220 / 210", "Data check / sanity", "Essential facts present? Inputs consistent?"],
                  ["200", "Data verdict", "R93: Insufficient data + HALT; R94: data_sufficient"],
                  ["100", "COMPUTE", "Derived facts must exist before they are tested"],
                  ["90", "Band", "Classify ratios (critical/short/moderate/comfortable ...)"],
                  ["70 / 60", "Diagnosis / Symptom", "Raise problems from facts / Yes-No answers"],
                  ["40", "Chained", "Use conclusions of other rules (forward chaining)"],
                  ["6", "Crisis override", "R73: imminent crisis forces Crisis"],
                  ["5", "Scoring", "Health score and problem counts – after ALL diagnosis"],
                  ["4 / 3", "Status / status decisions", "Healthy, Watch, Risky, Crisis; final advice"],
              ], [2.2 * cm, 4 * cm, W - 6.2 * cm]),
              Spacer(1, 4),
              P("Ties are broken by **specificity** (more conditions first) and then by **rule "
                "order**. Refraction (each rule fires once) guarantees termination in at most "
                f"{len(RULES)} cycles."),
              P("3.7 Status safety rules", "h2")]
    story += bullets([
        "**R76** – any Critical problem caps the status at Risky (never Watch/Healthy).",
        "**R78** – score ≥ 75 but a High problem exists → Watch.",
        "**R79** – Healthy requires zero Critical and zero High problems.",
        "**R73** – an imminent cash crisis forces Crisis regardless of score.",
    ])
    story += [P("3.8 Data sufficiency (Group 0)", "h2"),
              P("An expert must not conclude without data. R82–R87 (priority 220) flag missing "
                "essentials – cash in hand, bank balance, monthly sales > 0, gross margin, fixed "
                "expenses, at least one current liability (unless the owner ticks \"I don't owe "
                "anything right now\" - then R95 records the strength \"No short-term debt\" instead). "
                "R88–R92 (210) are sanity warnings. "
                "R93 (200) sets *Insufficient data* and executes **HALT**, so no score or diagnosis "
                "is produced; R94 otherwise asserts `data_sufficient`, which the scoring rules "
                "require. A blank value is *missing*; 0 is real data."),
              code_block('Rule("R87", G0, "At least one current liability is needed ...",\n'
                         '     (C("accounts_payable", "empty"), C("short_term_loans", "empty"),\n'
                         '      C("other_current_liabilities", "empty")),\n'
                         '     (FlagMissing("current_liabilities", "At least one current liability ..."),),\n'
                         '     1.0, P_MISSING),\n\n'
                         'Rule("R93", G0, "If any essential fact is missing: Insufficient data and STOP.",\n'
                         '     (C("missing_facts_count", ">", 0),),\n'
                         '     (Assert("status", "Insufficient data"), Halt()), 1.0, P_VERDICT),'),
              P("3.9 Consultation wizard (engine/consultation.py)", "h2"),
              P("The Consultation is a step-by-step wizard: Welcome → 1 Your business → 2 Cash → "
                "3 Customers who owe you → 4 Stock → 5 Suppliers & loans → 6 Warning signs → "
                "Review → Report. Questions live in `questions.py` with a step, a plain-language "
                "label, an example value, `required`, `ask_if` conditions (same language as rule "
                "conditions, evaluated by the same `evaluate_condition`) and a plain `skip_text`."),
              code_block('Question("payment_days", "How many days do you usually take to pay suppliers?",\n'
                         '         "Days you take to pay suppliers", "days", 5, ..., required=True,\n'
                         '         ask_if=(C("accounts_payable", ">", 0),),\n'
                         '         skip_text="Not asked because you owe suppliers nothing."),'),
              P("`resolve()` decides which questions are shown or skipped and fills defaults; a step "
                "with nothing to ask is skipped as a whole. `validate_step()` blocks **Next** until "
                "the required answers are given (business name, cash, sales > 0, at least one "
                "liability) and returns plain-words messages shown under each field."),
              code_block(consultation.resolve),
              code_block(consultation.validate_step, 40),
              P("**Why are you asking?** (a small link under every question) is shown by "
                "`ui/fields.py: why_text()`, which calls `why_asking()` in engine/consultation.py. "
                "`why_asking()` uses `rules_using_fact()` (engine/explanation.py) to list the rules "
                "that test the fact directly and those it feeds through derived facts, and "
                "`ask_reason()` to say in plain words why the question is shown (its ask_if "
                "condition)."),
              code_block(consultation.ask_reason),
              code_block(consultation.why_asking),
              P("3.10 Plain-English report (engine/explanation.py)", "h2"),
              P("`plain_summary()` builds 2–3 sentences from working-memory facts and the problems "
                "the rules raised – no AI: fixed templates filled with facts, plus each problem's "
                "plain 'concern' phrase from the catalog. `figure_meaning()` gives every key "
                "figure a one-line meaning. The report then shows the top three actions, the "
                "problems found, the key figures, and the collapsed rule trace. Owners see plain "
                "words (\"Do this now\", \"Very likely\"); a \"Show technical details\" switch reveals "
                "the certainty factors and rule IDs behind every action and problem."),
              code_block(sys.modules["engine.explanation"].plain_summary, 45),
              P("3.11 Knowledge sources & limitations", "h2"),
              P("**Sources.** The rules come from standard financial ratio analysis as taught in "
                "accounting and financial management (current, quick and cash ratio, cash "
                "conversion cycle, debt service ratio) and from common bank credit-assessment "
                "practice (cash cover, repayment capacity, working capital). Thresholds are general "
                "rules of thumb that vary by industry; they are kept in `thresholds.json` so an "
                "expert can tune them on the Knowledge Acquisition page without changing "
                "code. Certainty factors were assigned by the knowledge engineer according to how "
                "strong each warning sign is, just as MYCIN's certainty factors came from expert "
                "judgment.")]
    story += bullets([
        "**Self-reported data** – the diagnosis is only as accurate as the figures entered.",
        "**Single point-in-time snapshot** – no history, so trends are not detected.",
        "**Not industry-benchmarked** – one set of thresholds for all businesses unless tuned.",
        "**Advisory, not predictive** – it flags risks and suggests actions; it does not forecast.",
    ])
    story.append(PageBreak())

    # ---------------- 4. Rules ----------------
    story += [P(f"4. Complete knowledge base – {len(RULES)} rules", "h1"),
              P("Generated directly from `knowledge_base/rules.py`. Threshold names refer to "
                "`thresholds.json` (section 6).")]
    rows = [[r.id, r.group.split(". ", 1)[1], r.if_text().replace("  AND  ", " AND "),
             then_text(r), f"{r.cf:.2f}"] for r in RULES]
    story.append(table(["ID", "Group", "IF", "THEN", "CF"], rows,
                       [1.0 * cm, 2.4 * cm, 6.0 * cm, W - 10.5 * cm, 1.1 * cm]))
    story.append(PageBreak())

    # ---------------- 5. Problem catalog ----------------
    story += [P(f"5. Problem catalog – {len(PROBLEMS)} problems", "h1")]
    rows = [[v["title"], v["severity"], " | ".join(d["text"] for d in v["decisions"])]
            for v in PROBLEMS.values()]
    story.append(table(["Problem", "Severity", "Recommended decisions"], rows,
                       [4.6 * cm, 1.6 * cm, W - 6.2 * cm]))

    # ---------------- 6. Thresholds ----------------
    story += [P("6. Thresholds (thresholds.json)", "h1")]
    rows = [[k, f"{v['value']:g}", v["description"]] for k, v in load_threshold_table().items()]
    story.append(table(["Threshold", "Default", "Meaning"], rows, [4.6 * cm, 1.6 * cm, W - 6.2 * cm]))
    story.append(PageBreak())

    # ---------------- 7. Results ----------------
    story += [P("7. Sample cases and test results", "h1"),
              P("Results below were produced by running the engine on each demo business with "
                "the default thresholds while generating this document.")]
    rows = []
    for name, case in SAMPLE_CASES.items():
        r = diagnose(case["inputs"])
        top = ", ".join(p["title"] for p in r.problems[:3]) or "-"
        rows.append([name.split(" (")[0], case["expected_status"], r.status,
                     f"{r.health_score:.0f}", str(r.rules_fired), top])
    story.append(table(["Business", "Expected", "Result", "Score", "Rules fired", "Top problems"],
                       rows, [3.6 * cm, 1.8 * cm, 1.5 * cm, 1.2 * cm, 1.5 * cm, W - 9.6 * cm]))
    story += [Spacer(1, 6), P("Automated tests (pytest)", "h2")]
    story += bullets([
        "**test_rules.py** – rule count ≥ 50, unique sequential IDs, valid CFs, every threshold / "
        "problem / formula reference exists, threshold validation.",
        "**test_engine.py** – termination & refraction, conflict resolution order, forward-chaining "
        "propagation, MYCIN maths, CF combination, symptom rules working alone, status safety "
        "caps (R76, R78), crisis override (R73), division-by-zero inputs, input validation, "
        "collection/debt bands, threshold edits changing conclusions.",
        "**test_sample_cases.py** – each sample reaches its expected status; all four statuses "
        "covered; decisions ranked and explained.",
        "**test_data_sufficiency.py** – empty input → Insufficient data with no score; partial "
        "input lists exactly the missing facts; zero sales / no liabilities; sanity warnings.",
        "**test_consultation_logic.py** – required business name, per-field step validation, "
        "liability check, skipped steps and defaults, navigation, amount parsing, WHY from the "
        "rule base, plain summary and figure meanings.",
        "**test_not_sure.py** – unanswered questions block Next; Not sure fires the Yes-rule at "
        "half CF (and uses not_sure_cf from thresholds); Not sure + a numeric rule combine "
        "(MYCIN); No fires no symptom rule; Not sure is not a No; skipped questions default to No.",
        "**test_app.py** – headless Streamlit AppTest: full wizard run to the report, Next blocked "
        "on empty name / empty cash step, bad amount message, thousand separators, service "
        "business skipping Stock, follow-up questions appearing, back/edit from review, the Why "
        "link, every sample through Quick Diagnosis, required name there too, warning signs "
        "with no default (blocked until answered, Not sure shown as Possible) in both modes.",
    ])

    # ---------------- 8. Deployment ----------------
    story += [P("8. Running and deployment", "h1"), P("Local", "h2"),
              code_block("python -m venv .venv\n.venv\\Scripts\\activate\n"
                         "pip install -r requirements-dev.txt\npytest -q\nstreamlit run app.py"),
              P("Streamlit Community Cloud", "h2")]
    story += bullets([
        "Push the project to a public GitHub repository (app.py and requirements.txt at the root).",
        "Sign in at share.streamlit.io with GitHub → Create app → choose repository, branch "
        "`main`, main file `app.py`.",
        "Advanced settings → Python version **3.12** → Deploy.",
        f"Live URL: **{url}**",
    ])

    # ---------------- 9. Viva Q&A ----------------
    notes = (ROOT / "VIVA_NOTES.md").read_text(encoding="utf-8")
    notes = notes.split("## 10.", 1)[-1]          # only the viva-questions section
    qa = re.findall(r"^\d+\. \*\*(.+?)\*\* (.+?)(?=^\d+\. \*\*|^\*\*Bonus|\Z)", notes,
                    flags=re.S | re.M)
    if qa:
        story += [PageBreak(), P("9. Likely viva questions", "h1")]
        for i, (q, a) in enumerate(qa, 1):
            story += [P(f"**Q{i}. {q}**"), P(" ".join(a.split()))]

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="CashFlow IQ – Code Explanation", author="CashFlow IQ")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="(add the Streamlit Cloud URL after deployment)")
    parser.add_argument("--out", default=str(ROOT / "CashFlowIQ_Code_Explanation.pdf"))
    args = parser.parse_args()
    print("Written:", build(args.url, Path(args.out)))
