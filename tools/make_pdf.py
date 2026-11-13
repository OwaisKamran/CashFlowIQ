"""Build CashFlowIQ_Code_Explanation.pdf (python-docx document, converted to PDF by Word)."""
import argparse
import inspect
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from docx import Document                                            # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT                      # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK             # noqa: E402
from docx.opc.constants import RELATIONSHIP_TYPE                    # noqa: E402
from docx.oxml import OxmlElement                                   # noqa: E402
from docx.oxml.ns import qn                                         # noqa: E402
from docx.shared import Cm, Pt, RGBColor                            # noqa: E402

from engine import certainty, consultation, diagnosis, explanation  # noqa: E402
from engine import inference_engine, working_memory                 # noqa: E402
from engine.diagnosis import diagnose                               # noqa: E402
from knowledge_base import formulas, load_threshold_table, questions, rule_model  # noqa: E402
from knowledge_base.problems import PROBLEMS                        # noqa: E402
from knowledge_base.rules import RULES, RULE_GROUPS                 # noqa: E402
from sample_cases import SAMPLE_CASES                               # noqa: E402
from ui import components                                           # noqa: E402

LIVE_URL = "https://cashflow-iq.streamlit.app/"
GITHUB_URL = "https://github.com/OwaisKamran/CashFlowIQ"
NAVY = RGBColor(0x1E, 0x3A, 0x5F)          # ui/styles.py NAVY
TEAL = "0F766E"                            # ui/styles.py TEAL (links)
DARK = RGBColor(0x26, 0x26, 0x26)
GREY = RGBColor(0x59, 0x59, 0x59)
LINE_NO = RGBColor(0x8A, 0x93, 0x9F)
EXAMPLE = "Hamza Textiles Wholesale (Watch)"
STUDENT = "Muhammad Owais Kamran Khania"
ROLL_NO = "CT-24085"
SUBMITTED_TO = "Sir Wasiq Noor"

# Word: update the table of contents and fields, then export the PDF
WORD_PS = r"""
param([string]$Docx, [string]$Pdf)
$w = New-Object -ComObject Word.Application
$w.Visible = $false; $w.DisplayAlerts = 0
try {
    $d = $w.Documents.Open($Docx)
    foreach ($id in -20, -21) {
        $s = $d.Styles.Item($id); $s.Font.Name = "Calibri"; $s.Font.Size = 11; $s.Font.Bold = $false
        $s.ParagraphFormat.SpaceAfter = 5
    }
    $d.Styles.Item(-21).ParagraphFormat.LeftIndent = 11
    $d.Fields.Update() | Out-Null
    foreach ($t in $d.TablesOfContents) { $t.Update() }
    $d.Repaginate()
    foreach ($t in $d.TablesOfContents) { $t.Update() }
    $d.Save()
    $d.ExportAsFixedFormat($Pdf, 17, $false, 0, 0, 1, 1, 0, $true)
    "pages: " + $d.ComputeStatistics(2)
    $d.Close($false)
} finally { $w.Quit() }
"""


# ---- small document helpers
def set_font(element, name):
    rpr = element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts"); rpr.insert(0, fonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(attr), None)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)


def smart(text):
    """Curly quotes, as Word would type them."""
    out, open_q = [], True
    for ch in text:
        if ch == '"':
            out.append("“" if open_q else "”"); open_q = not open_q
        else:
            out.append("’" if ch == "'" else ch)
    return "".join(out)


class Doc:
    def __init__(self):
        self.d = Document()
        self.tables = 0
        sec = self.d.sections[0]
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, side, Cm(2.54))
        sec.header_distance = sec.footer_distance = Cm(1.25)
        styles = self.d.styles
        normal = styles["Normal"]
        normal.font.size = Pt(11); normal.font.color.rgb = RGBColor(0, 0, 0)
        set_font(normal.element, "Calibri")
        pf = normal.paragraph_format
        pf.line_spacing, pf.space_after, pf.alignment = 1.15, Pt(6), WD_ALIGN_PARAGRAPH.JUSTIFY
        for name, size, before, after in (("Heading 1", 16, 18, 6), ("Heading 2", 13, 12, 6)):
            st = styles[name]
            st.font.size, st.font.bold, st.font.italic, st.font.color.rgb = Pt(size), True, False, NAVY
            set_font(st.element, "Cambria")
            st.paragraph_format.space_before, st.paragraph_format.space_after = Pt(before), Pt(after)
            st.paragraph_format.keep_with_next = True
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            st.paragraph_format.line_spacing = 1.15
        cap = styles["Caption"]
        cap.font.size, cap.font.italic, cap.font.bold, cap.font.color.rgb = Pt(9), True, False, DARK
        set_font(cap.element, "Calibri")
        cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        lb = styles["List Bullet"]
        set_font(lb.element, "Calibri"); lb.font.size = Pt(11)
        lb.paragraph_format.space_after = Pt(3); lb.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        self._header_footer(sec)

    # header "CashFlow IQ – Code Explanation" and footer "Page X of Y" (not on the cover)
    def _header_footer(self, sec):
        sec.different_first_page_header_footer = True
        hp = sec.header.paragraphs[0]; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run("CashFlow IQ – Code Explanation"); r.font.size = Pt(9); r.font.color.rgb = GREY
        set_font(r._element, "Calibri")
        fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for piece in ("Page ", ("PAGE", "1"), " of ", ("NUMPAGES", "1")):
            if isinstance(piece, tuple):
                self.field(fp, *piece)
            else:
                fp.add_run(piece)
        for r in fp.runs:
            r.font.size = Pt(9); r.font.color.rgb = GREY; set_font(r._element, "Calibri")

    def field(self, par, instr, placeholder=""):
        def mark(kind):
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), kind); return el
        par.add_run()._element.append(mark("begin"))
        t = OxmlElement("w:instrText"); t.set(qn("xml:space"), "preserve"); t.text = f" {instr} "
        par.add_run()._element.append(t)
        par.add_run()._element.append(mark("separate"))
        par.add_run(placeholder)
        par.add_run()._element.append(mark("end"))

    def runs(self, par, text, size=None):
        """Markup: **bold**, *italic*, `code`."""
        for part in re.split(r"(\*\*.+?\*\*|`.+?`|\*.+?\*)", text):
            if not part:
                continue
            if part.startswith("**"):
                run = par.add_run(smart(part[2:-2])); run.bold = True
            elif part.startswith("`"):
                run = par.add_run(part[1:-1]); set_font(run._element, "Consolas")
                run.font.size = Pt((size or 11) - 1.5)
                continue
            elif part.startswith("*"):
                run = par.add_run(smart(part[1:-1])); run.italic = True
            else:
                run = par.add_run(smart(part))
            if size:
                run.font.size = Pt(size)
        return par

    def p(self, text, align=None, after=None):
        par = self.runs(self.d.add_paragraph(), text)
        if align is not None:
            par.alignment = align
        if after is not None:
            par.paragraph_format.space_after = Pt(after)
        return par

    def bullets(self, items):
        for item in items:
            self.runs(self.d.add_paragraph(style="List Bullet"), item)

    def h(self, text, level):
        text = re.sub(r"^(\d+(?:\.\d+)?)\s+", r"\1 ", text)          # "1 How to Run"
        self.d.add_heading(text, level=level)

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def link(self, par, url, text, size=None, bold=False):
        rid = par.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
        h = OxmlElement("w:hyperlink"); h.set(qn("r:id"), rid)
        r = OxmlElement("w:r"); rpr = OxmlElement("w:rPr")
        for tag, val in (("w:color", TEAL), ("w:u", "single")):
            el = OxmlElement(tag); el.set(qn("w:val"), val); rpr.append(el)
        if bold:
            rpr.append(OxmlElement("w:b"))
        if size:
            sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size * 2))); rpr.append(sz)
        r.append(rpr); t = OxmlElement("w:t"); t.text = text; r.append(t); h.append(r)
        par._p.append(h)

    def _borders(self, table, color="BFBFBF"):
        b = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:space", "0"), ("w:color", color)):
                e.set(qn(k), v)
            b.append(e)
        table._element.tblPr.append(b)

    def _shade(self, cell, fill):
        shd = OxmlElement("w:shd")
        for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", fill)):
            shd.set(qn(k), v)
        cell._element.get_or_add_tcPr().append(shd)

    def caption(self, text):
        self.tables += 1
        c = self.d.add_paragraph(style="Caption")
        c.add_run("Table "); self.field(c, "SEQ Table \\* ARABIC", str(self.tables))
        c.add_run(f": {smart(text)}")
        c.paragraph_format.keep_with_next = True
        c.paragraph_format.space_before = Pt(2); c.paragraph_format.space_after = Pt(4)

    def table(self, header, rows, widths, caption=None, size=10):
        if caption:
            self.caption(caption)
        t = self.d.add_table(rows=1 + len(rows), cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
        self._borders(t)
        for i, values in enumerate([header] + rows):
            row = t.rows[i]
            if i == 0:
                th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); row._tr.get_or_add_trPr().append(th)
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for j, value in enumerate(values):
                cell = row.cells[j]; cell.width = Cm(widths[j])
                par = cell.paragraphs[0]
                par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                par.paragraph_format.space_before = Pt(1)
                par.paragraph_format.space_after = Pt(1); par.paragraph_format.line_spacing = 1.0
                par.paragraph_format.keep_with_next = i < len(rows)      # keep the table on one page
                self.runs(par, str(value), size=size)
                if i == 0:
                    self._shade(cell, "1E3A5F")
                    for r in par.runs:
                        r.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for j, w in enumerate(widths):
            for cell in t.columns[j].cells:
                cell.width = Cm(w)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)

    def cover_table(self, rows):
        """Borderless details table on the cover (bold labels, 12 pt)."""
        info = self.d.add_table(rows=len(rows), cols=2); info.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, (k, v) in enumerate(rows):
            for j, w in enumerate((4.0, 8.6)):
                cell = info.rows[i].cells[j]; cell.width = Cm(w)
                par = cell.paragraphs[0]; par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                par.paragraph_format.space_after = Pt(4)
                if j == 0:
                    run = par.add_run(k); run.bold = True; run.font.size = Pt(12)
                elif v.startswith("http"):
                    self.link(par, v, v, size=12)
                else:
                    run = par.add_run(v); run.font.size = Pt(12)

    def code(self, lines, start=1, title=None):
        """Code excerpt: Consolas 9 pt on light grey, with line numbers."""
        if title:
            cap = self.d.add_paragraph()
            r = cap.add_run(title); r.font.size = Pt(9); r.font.color.rgb = DARK; r.italic = True
            cap.paragraph_format.space_after = Pt(2); cap.paragraph_format.keep_with_next = True
        t = self.d.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._borders(t, "D9DEE3")
        t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))   # never split an excerpt
        cell = t.rows[0].cells[0]; cell.width = Cm(15.9); self._shade(cell, "F3F4F6")
        width = len(str(start + len(lines)))
        for k, line in enumerate(lines):
            par = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf = par.paragraph_format
            pf.space_after = Pt(0); pf.line_spacing = 1.0
            pf.left_indent = Cm(0.75 + 0.19 * width); pf.first_line_indent = -Cm(0.75 + 0.19 * width)
            n = par.add_run(f"{start + k:>{width}}   "); n.font.color.rgb = LINE_NO
            body = par.add_run(line.rstrip("\n").replace("\t", "    ") or " ")
            for r in (n, body):
                r.font.size = Pt(9); set_font(r._element, "Consolas")
        self.d.add_paragraph().paragraph_format.space_after = Pt(0)

    def source(self, obj, title, max_lines=34, skip_doc=False):
        lines, start = inspect.getsourcelines(obj)
        if len(lines) > max_lines:
            lines = lines[:max_lines - 1] + ["    ...\n"]
        self.code(lines, start, title)

    def save(self, path):
        self.d.core_properties.title = "CashFlow IQ – Code Explanation"
        self.d.core_properties.author = "Muhammad Owais Kamran Khania"
        self.d.save(path)


def file_lines(path, start_pattern, end_pattern=None, count=None, after=0):
    """Lines of a file from the first match of start_pattern (1-based start number)."""
    text = (ROOT / path).read_text(encoding="utf-8").splitlines()
    i = next(k for k, line in enumerate(text) if re.search(start_pattern, line))
    j = i + (count or 1)
    if end_pattern:
        j = next(k for k in range(i + 1, len(text)) if re.search(end_pattern, text[k])) + after
    return text[i:j], i + 1


def rule_lines(rule_id):
    lines, start = file_lines("knowledge_base/rules.py", rf'Rule\("{rule_id}"', r'^\s*Rule\("R\d+"|^\]')
    while lines and (not lines[-1].strip() or lines[-1].strip().startswith("#")):   # drop trailing comments
        lines.pop()
    return lines, start


def test_counts():
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    passed = re.search(r"(\d+) passed", out)
    failed = re.search(r"(\d+) failed", out)
    listing = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                             cwd=ROOT, capture_output=True, text=True).stdout
    per_file = Counter(line.split("::")[0].replace("tests/", "") for line in listing.splitlines() if "::" in line)
    return (int(passed.group(1)) if passed else 0), (int(failed.group(1)) if failed else 0), per_file


# ---- content
def build(doc: Doc, url: str):
    d = doc.d
    kinds = Counter(r.kind for r in RULES)
    table = load_threshold_table()
    passed, failed, per_file = test_counts()
    total_tests = sum(per_file.values())

    # cover (reference layout: title, subtitle, three centred lines, details table)
    def centre(text, size, after, font="Calibri", bold=False, color=None):
        par = d.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_before, par.paragraph_format.space_after = Pt(0), Pt(after)
        if text:
            r = par.add_run(text); r.font.size = Pt(size); r.bold = bold
            if color is not None:
                r.font.color.rgb = color
            set_font(r._element, font)

    for _ in range(5):
        centre("", 11, 6)
    centre("CashFlow IQ", 26, 10, "Cambria", True, NAVY)
    centre("Business Liquidity & Cash Flow Decision Expert System", 14, 40, "Cambria", color=DARK)
    centre("Code Explanation", 12, 4)
    centre("CT-262 Introduction to Artificial Intelligence (IAI)", 12, 4)
    centre("NED University of Engineering & Technology", 12, 48)
    doc.cover_table([("Student name", STUDENT), ("Roll No", ROLL_NO), ("Submitted to", SUBMITTED_TO),
                     ("Date", f"{date.today():%d %B %Y}"), ("Live application", url),
                     ("GitHub repository", GITHUB_URL)])
    doc.page_break()

    # table of contents
    t = d.add_paragraph(); r = t.add_run("Table of Contents"); r.bold = True; r.font.size = Pt(16)
    r.font.color.rgb = NAVY; set_font(r._element, "Cambria"); t.paragraph_format.space_after = Pt(12)
    t.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.field(d.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u', "Update the field to build the table of contents.")
    doc.page_break()

    # 1 how to run
    doc.h("1  How to Run", 1)
    doc.h("1.1  Live application", 2)
    par = doc.p("The application is deployed on Streamlit Community Cloud and can be opened in any web "
                "browser, on a computer or a phone, without installing anything: ")
    doc.link(par, url, url, bold=True)
    doc.p("The source code is on GitHub: ").add_run()
    doc.link(d.paragraphs[-1], GITHUB_URL, GITHUB_URL)
    doc.p("Free Streamlit apps go to sleep after a period of no use. If the page says the app is asleep, "
          "click the button to wake it up and wait about a minute.")
    doc.h("1.2  Run it on Windows", 2)
    doc.p("Install **Python 3.12** from python.org (tick *Add python.exe to PATH*). Unzip the project, open "
          "*Command Prompt* in the `CashFlowIQ` folder and run:")
    doc.code(["python -m venv .venv", ".venv\\Scripts\\activate", "pip install -r requirements.txt",
              "streamlit run app.py"], 1, "Command Prompt")
    doc.p("Streamlit opens the app in the browser at `http://localhost:8501`. Press *Ctrl + C* in the "
          "Command Prompt to stop it.")
    doc.h("1.3  Run the tests", 2)
    doc.code(["pip install -r requirements-dev.txt", "pytest -q"], 1, "Command Prompt (with .venv active)")
    doc.p(f"All {total_tests} tests should pass. `requirements-dev.txt` adds *pytest* and *python-docx* "
          "(used only to build this document).")

    # 2 structure
    doc.h("2  Project Structure", 1)
    doc.h("2.1  Folder tree", 2)
    doc.code([
        "CashFlowIQ/",
        "├── app.py                    entry point: page setup, sidebar, navigation",
        "├── sample_cases.py           five demo businesses (one per status)",
        "├── requirements.txt          packages for the app",
        "├── requirements-dev.txt      + pytest, python-docx (development only)",
        "├── .streamlit/config.toml    theme (colours, fonts)",
        "├── knowledge_base/           THE KNOWLEDGE (data, no reasoning)",
        "│   ├── rule_model.py         what a rule, condition and action look like",
        f"│   ├── rules.py              the {len(RULES)} IF-THEN rules",
        f"│   ├── problems.py           catalog of {len(PROBLEMS)} problems and their advice",
        "│   ├── formulas.py           named, zero-safe formulas for the ratios",
        f"│   ├── questions.py          the {len(questions.QUESTIONS)} questions and input checks",
        f"│   └── thresholds.json       {len(table)} numeric limits used by the rules",
        "├── engine/                   THE REASONING (knows nothing about cash flow)",
        "│   ├── working_memory.py     the fact base",
        "│   ├── inference_engine.py   forward chaining: match, resolve, fire",
        "│   ├── certainty.py          MYCIN certainty factors",
        "│   ├── diagnosis.py          diagnose(): runs the engine, packs the result",
        "│   ├── consultation.py       wizard logic, ask_if, Why are you asking?",
        "│   └── explanation.py        HOW trace, WHY text, plain-English summary",
        "├── ui/                       shared look and widgets",
        "│   ├── styles.py             colour palette and CSS",
        "│   ├── components.py         header, chips, stepper, score ring, page scripts",
        "│   ├── fields.py             one question -> one input box",
        "│   ├── report.py             the diagnosis report (dashboard)",
        "│   └── logo.svg              sidebar logo",
        "├── views/                    the five pages",
        "│   ├── consultation.py       step-by-step wizard (default page)",
        "│   ├── quick_diagnosis.py    all questions on one page, sample businesses",
        "│   ├── knowledge_base.py     browse every rule and problem",
        "│   ├── admin.py              Knowledge Acquisition: edit thresholds",
        "│   └── about.py              how the system works",
        f"└── tests/                    {total_tests} automated tests (pytest)",
    ], 1, "Project folder")
    doc.h("2.2  Expert system components", 2)
    doc.p("The program follows the classic structure of an expert system. Knowledge is kept separate from "
          "the reasoning code, so rules can be added or changed without touching the inference engine.")
    doc.table(["Component", "File(s)", "What it does"], [
        ["Knowledge base", "`knowledge_base/rules.py`, `problems.py`, `thresholds.json`",
         f"{len(RULES)} rules, {len(PROBLEMS)} problems with advice, {len(table)} thresholds"],
        ["Working memory", "`engine/working_memory.py`", "Holds the facts of one case and their certainty"],
        ["Inference engine", "`engine/inference_engine.py`, `certainty.py`",
         "Forward chaining with conflict resolution, refraction, HALT and MYCIN CFs"],
        ["Explanation facility", "`engine/explanation.py`, `consultation.py`",
         "HOW (rule trace) and WHY (why a question is asked, why an action is advised)"],
        ["User interface", "`app.py`, `views/`, `ui/`", "Consultation wizard, Quick Diagnosis, report, expert pages"],
        ["Knowledge acquisition", "`views/admin.py`", "An expert edits and validates the thresholds in the browser"],
    ], [3.4, 5.6, 6.9], "Expert system components and their files")

    # 3 file by file
    doc.h("3  File-by-File Explanation", 1)
    doc.p("Each part below explains one file in plain English, shows a short excerpt of the real code "
          "(with its line numbers in the file) and explains what the excerpt does.")

    doc.h("3.1  rule_model.py – how a rule is written", 2)
    doc.p("A rule is stored as **data**, not as an if/else statement. It has an ID, a group, a description, "
          "a tuple of conditions (all must be true), a tuple of actions, a certainty factor and a priority.")
    doc.source(rule_model.Rule, "knowledge_base/rule_model.py – the Rule class", max_lines=21)
    doc.p("`specificity` (the number of conditions) is used to break ties between rules of equal priority. "
          "Conditions use a small language: comparisons (`<`, `>=`, `in` ...), checks such as `known` or "
          "`missing`, and `yes` for warning signs. Values such as `T(\"crisis_runway_days\")` are looked up "
          "in `thresholds.json` when the rule is matched, so no number is hard-coded in a rule.")

    doc.h("3.2  rules.py – the knowledge base", 2)
    groups = Counter(r.group for r in RULES)
    doc.p(f"`rules.py` holds all {len(RULES)} rules in ten groups (G0–G9). By type there are "
          f"{kinds['DATA CHECK']} data-check, {kinds['COMPUTE']} compute, {kinds['DECISION']} decision, "
          f"{kinds['CLASSIFY']} classification and {kinds['STATUS']} status rules. Three example rules:")
    for rid, title in (("R17", "R17 – a band and diagnosis rule"), ("R22", "R22 – a chained rule"),
                       ("R93", "R93 – data sufficiency: stop if essential data is missing")):
        lines, start = rule_lines(rid)
        doc.code(lines, start, f"knowledge_base/rules.py – {title}")
    doc.p("**R17** fires when the cash runway is below the crisis limit (30 days): it classifies the runway as "
          "critical and raises the problem *Cash runs out within a month* with CF 0.95. **R22** is chained: it "
          "uses conclusions of other rules (a negative cash flow band and a critical runway band) to raise "
          "*Imminent cash crisis*. **R93** has the highest priority group: if any essential fact is missing it "
          "sets the status to *Insufficient data* and executes **HALT**, so the system never guesses.")
    doc.table(["Group", "Rules", "Group", "Rules"], [
        [RULE_GROUPS[i], groups[RULE_GROUPS[i]], RULE_GROUPS[i + 5], groups[RULE_GROUPS[i + 5]]]
        for i in range(5)], [5.0, 2.95, 5.0, 2.95], "Rule groups")

    doc.h("3.3  problems.py – the problem catalog", 2)
    doc.p("Rules only name a problem (for example `RaiseProblem(\"cash_runs_out_within_month\")`). Its title, "
          "severity, description and recommended decisions are written once in this catalog. "
          f"There are {len(PROBLEMS)} problems: "
          + ", ".join(f"{n} {s}" for s, n in Counter(p['severity'] for p in PROBLEMS.values()).most_common())
          + ". The file also holds one plain-English *concern* phrase per problem for the summary.")
    lines, start = file_lines("knowledge_base/problems.py", r'"cash_runs_out_within_month": _p\(',
                              r'^\s{4}"\w+": _p\(')
    doc.code(lines, start, "knowledge_base/problems.py – one catalog entry")

    doc.h("3.4  thresholds.json – numeric limits", 2)
    doc.p(f"All {len(table)} limits used by the rules live in this JSON file, each with a value, a group and a "
          "description. The Knowledge Acquisition page edits them, so an expert can tune the system "
          "without changing code.")
    lines, start = file_lines("knowledge_base/thresholds.json", r'"crisis_runway_days"', count=3)
    doc.code(lines, start, "knowledge_base/thresholds.json – the cash runway limits")

    doc.h("3.5  formulas.py – ratios and safe division", 2)
    doc.p("COMPUTE rules call named formulas. Every division goes through `safe_div()`: if the divisor is 0 "
          "or a value is missing, the result is `None` (\"not computable\"). Any condition that tests a `None` "
          "fact is false, so dependent rules simply do not fire and the program never crashes.")
    doc.source(formulas.safe_div, "knowledge_base/formulas.py – safe division")
    doc.source(formulas.runway_days, "knowledge_base/formulas.py – cash runway")
    doc.source(formulas.health_score, "knowledge_base/formulas.py – health score")
    doc.p("The health score starts at 100 and loses *severity weight × CF* for every problem (Critical 30, "
          "High 15, Medium 8, Low 4), plus a small bonus for each strength found.")

    doc.h("3.6  working_memory.py – the fact base", 2)
    doc.p("Working memory stores every fact with its value, its certainty factor and its source (the user, or "
          "the rule that derived it). It also keeps the problems, strengths, decisions, missing facts and "
          "warnings. When a second rule raises the same problem, the two CFs are combined instead of "
          "overwritten:")
    doc.source(working_memory.WorkingMemory.add_problem, "engine/working_memory.py – add_problem")
    doc.p("The problem is also stored as a fact `problem:<key>`, so chained rules can test it.")

    doc.h("3.7  certainty.py – certainty factor maths", 2)
    doc.source(certainty.conclusion_cf, "engine/certainty.py – CF of a conclusion")
    doc.source(certainty.combine, "engine/certainty.py – MYCIN combination")
    doc.p("A conclusion is only as certain as its weakest premise: *CF = rule CF × min(CF of the facts)*. "
          "Two rules that support the same problem are combined with *CF1 + CF2 × (1 − CF1)*, so "
          "evidence adds up but never goes above 1. A *Not sure* answer is stored with CF 0.5 "
          "(`not_sure_cf`), so a rule that needs that answer to be Yes still fires, at half strength.")

    doc.h("3.8  inference_engine.py – forward chaining", 2)
    doc.p("The engine is generic: it knows nothing about cash flow. It repeats the *recognise–act* cycle:")
    doc.source(inference_engine.InferenceEngine.run, "engine/inference_engine.py – the forward chaining loop")
    doc.bullets([
        "**Match** – `match()` builds the *conflict set*: every rule that has not fired yet and whose "
        "conditions are all true.",
        "**Conflict resolution** – `resolve()` picks one rule: highest priority first, then the more "
        "specific rule (more conditions), then the smaller rule ID.",
        "**Fire** – `fire()` carries out the actions and records a trace step.",
        "**Refraction** – each rule fires at most once (`self.fired`), so the loop always ends.",
        "**HALT** – a rule such as R93 can stop the engine early (`wm.halted`).",
    ])
    doc.source(inference_engine.InferenceEngine.match, "engine/inference_engine.py – match")
    doc.source(inference_engine.InferenceEngine.resolve, "engine/inference_engine.py – conflict resolution")
    doc.source(inference_engine.evaluate_condition, "engine/inference_engine.py – testing one condition")
    doc.p("`evaluate_condition()` is shared by the rules and by the questions' `ask_if` conditions, so the "
          "wizard and the engine use exactly the same condition language. A condition on a missing or "
          "not-computable value returns False.")

    doc.h("3.9  diagnosis.py – putting it together", 2)
    doc.source(diagnosis.diagnose, "engine/diagnosis.py – diagnose()", max_lines=14)
    doc.p("`diagnose()` loads the answers into working memory (giving *Not sure* answers CF 0.5), runs the "
          "engine with all rules and thresholds, then sorts the problems by severity and certainty, removes "
          "duplicate decisions and ranks them for the report.")

    doc.h("3.10  questions.py and consultation.py – the wizard", 2)
    doc.p(f"`questions.py` lists the {len(questions.QUESTIONS)} questions in order. Each has a step, a "
          "plain-language label, an example, and optional `ask_if` conditions written in the same language "
          "as the rules:")
    lines, start = file_lines("knowledge_base/questions.py", r'Question\("payment_days"', r'skip_text=', after=1)
    doc.code(lines, start, "knowledge_base/questions.py – a question that is asked only when needed")
    doc.source(consultation.resolve, "engine/consultation.py – deciding which questions to ask")
    doc.p("`resolve()` walks the questions in order and asks only those whose `ask_if` holds; skipped ones get "
          "their default, and a step with nothing to ask is skipped. `validate_step()` blocks *Next* until "
          "the required answers are given. The *Why are you asking?* link is generated from the rule base:")
    doc.source(consultation.why_asking, "engine/consultation.py – why_asking()")
    doc.source(questions.parse_amount, "knowledge_base/questions.py – reading a money amount", max_lines=22)
    doc.p("Amounts may be typed with commas (\"1,250,000\"). Decimals are rounded to the nearest whole rupee, "
          "and letters are rejected both in the browser and here on the server.")

    doc.h("3.11  explanation.py – HOW trace and summary", 2)
    doc.source(explanation.how_table, "engine/explanation.py – one row per fired rule")
    doc.p("The HOW table lists every rule that fired with the facts it matched, its conclusion and CF. "
          "`plain_summary()` writes the 2–3 sentence summary from fixed templates filled with facts "
          "(runway days, monthly cash left over) and the *concern* phrase of the main problems – no "
          "text is generated freely.")

    doc.h("3.12  User interface files", 2)
    doc.bullets([
        "**app.py** – sets up the page, the sidebar and the navigation (three sections: *For business "
        "owners*, *For experts*, *Info*).",
        "**views/consultation.py** – the step-by-step wizard: welcome, six steps, review and report.",
        "**views/quick_diagnosis.py** – all questions in tabs, with five sample businesses to load.",
        "**views/knowledge_base.py** and **views/admin.py** – the expert pages: browse rules and problems; "
        "edit, validate, download and upload thresholds.",
        "**ui/fields.py** – draws one question as an input box with its error and *Why?* link.",
        "**ui/report.py** – the report: status card with score ring, cash runway, key figures, chart, "
        "actions, problems and the HOW section.",
        "**ui/components.py** and **ui/styles.py** – shared helpers, the colour palette and CSS, plus two "
        "small browser scripts (Enter key moves to the next box; number boxes accept only digits).",
    ])
    doc.source(components.score_ring, "ui/components.py – the health score ring")

    # 4 worked example
    case = SAMPLE_CASES[EXAMPLE]
    inputs = case["inputs"]
    result = diagnose(inputs)
    doc.h(f"4  Worked Example: {inputs['business_name']}", 1)
    doc.p(f"This section follows one sample business through the system, using the real output of the "
          f"program. {case['story']}")
    doc.h("4.1  Inputs", 2)
    rs = lambda v: f"Rs {v:,.0f}"
    doc.table(["Question", "Answer", "Question", "Answer"], [
        ["Business type", inputs["business_type"].title(), "Monthly sales", rs(inputs["monthly_sales"])],
        ["Cash in hand", rs(inputs["cash_in_hand"]), "Gross margin", f"{inputs['gross_margin_pct']}%"],
        ["Bank balance", rs(inputs["bank_balance"]), "Fixed monthly costs", rs(inputs["monthly_fixed_expenses"])],
        ["Receivables", rs(inputs["accounts_receivable"]), "Days customers take", f"{inputs['collection_days']}"],
        ["Payables", rs(inputs["accounts_payable"]), "Days to pay suppliers", f"{inputs['payment_days']}"],
        ["Stock", rs(inputs["inventory_value"]), "Days to sell stock", f"{inputs['stock_days']}"],
        ["Short-term loans", rs(inputs["short_term_loans"]), "Monthly installment", rs(inputs["monthly_installment"])],
        ["Other bills due", rs(inputs["other_current_liabilities"]), "Warning signs = Yes",
         ", ".join(k.replace("_", " ") for k in ("late_customers", "big_customer", "sales_up_cash_down")
                   if inputs[k])],
    ], [3.6, 3.6, 3.9, 4.8], "Inputs of the worked example")
    doc.h("4.2  Computed ratios", 2)
    m = result.metrics
    doc.table(["Figure", "Value", "Figure", "Value"], [
        ["Current ratio", f"{m['current_ratio']:.2f}", "Cash runway", f"{m['runway_days']:.0f} days"],
        ["Quick ratio", f"{m['quick_ratio']:.2f}", "Net monthly cash flow", rs(m["net_monthly_cash_flow"])],
        ["Cash ratio", f"{m['cash_ratio']:.2f}", "Cash conversion cycle", f"{m['cash_conversion_cycle']:.0f} days"],
        ["Working capital", rs(m["working_capital"]), "Debt service ratio", f"{m['debt_service_ratio']:.2f}"],
    ], [3.8, 3.4, 4.6, 4.1], "Ratios computed by the COMPUTE rules")
    doc.h("4.3  Rules fired", 2)
    doc.p(f"The engine ran **{result.cycles} cycles** and fired **{result.rules_fired} of {len(RULES)} rules**, "
          "one per cycle, in this order:")
    rows = []
    for step in result.trace:
        concl = step.conclusions[0] if step.conclusions else ""
        concl = re.sub(r"\s+\[.*\]$", "", concl)                      # drop the formula text
        concl = re.sub(r"CF [\d.]+ combined with [\d.]+ -> ([\d.]+)", r"(combined CF \1)", concl)
        rows.append([step.cycle, step.rule_id, step.group.split(". ", 1)[-1], concl[:62], f"{step.cf:.2f}"])
    doc.table(["#", "Rule", "Group", "Conclusion", "CF"], rows, [0.8, 1.2, 3.3, 9.3, 1.3],
              "Rules fired, in order (first conclusion of each rule)", size=9)
    doc.h("4.4  Problems and status", 2)
    doc.table(["Problem", "Severity", "Supporting rules (CF)", "Combined CF"], [
        [p["title"], p["severity"], ", ".join(f"{rid} ({cf:.2f})" for rid, cf, _ in p["evidence"]), f"{p['cf']:.2f}"]
        for p in result.problems], [5.6, 2.0, 5.3, 3.0], "Problems diagnosed")
    wc = next(p for p in result.problems if p["key"] == "weak_credit_control")
    th = {k: v["value"] for k, v in table.items()}
    weights = {"Critical": th["weight_critical"], "High": th["weight_high"], "Medium": th["weight_medium"],
               "Low": th["weight_low"]}
    penalty = sum(weights[p["severity"]] * p["cf"] for p in result.problems)
    bonus = min(len(result.strengths) * th["strength_bonus"], th["max_strength_bonus"])
    status_step = next(s for s in result.trace if any(c.startswith("status = ") for c in s.conclusions))
    doc.p(f"*Weak credit control* is supported by two rules: "
          + " and ".join(f"{rid} with CF {cf:.2f}" for rid, cf, _ in wc["evidence"])
          + f". MYCIN combination gives 0.60 + 0.50 × (1 − 0.60) = **{wc['cf']:.2f}**.")
    doc.p(f"**Health score** = 100 − {penalty:.1f} (severity weight × CF of the {len(result.problems)} "
          f"problems) + {bonus:.0f} (bonus for {len(result.strengths)} strengths) = **{result.health_score:.1f}**. "
          f"The score is between {th['watch_score']:.0f} and {th['healthy_score']:.0f} and there is no Critical "
          f"problem, so rule **{status_step.rule_id}** sets the status to **{result.status}**. The top "
          f"recommended action is: *{result.decisions[0]['text']}*.")

    # 5 testing
    doc.h("5  Testing", 1)
    doc.p(f"The project has **{total_tests} automated tests** written with pytest. In the final run "
          f"**{passed} passed** and {failed} failed. The user-interface tests use Streamlit's headless "
          "*AppTest*, so the pages are tested without a browser.")
    about = {
        "test_engine.py": "termination and refraction, conflict resolution, forward chaining, MYCIN maths, "
                          "safety caps, division by zero, input validation, threshold edits",
        "test_app.py": "full wizard run, blocked Next, validation messages, skipped steps, back/edit, Why link, "
                       "Quick Diagnosis with every sample",
        "test_consultation_logic.py": "step validation, skipped steps and defaults, navigation, WHY text, plain "
                                      "summary, amount parsing and rounding",
        "test_data_sufficiency.py": "empty input gives Insufficient data, missing facts listed, sanity warnings, "
                                    "debt-free business",
        "test_rules.py": "at least 50 rules, unique sequential IDs, valid CFs, every threshold and problem used",
        "test_not_sure.py": "unanswered question blocks Next, Not sure at half CF, combination with a numeric "
                            "rule, No fires nothing",
        "test_sample_cases.py": "each sample reaches its expected status; decisions ranked and explained",
    }
    doc.table(["Test file", "Tests", "What is checked"],
              [[f"`{f}`", n, about.get(f, "")] for f, n in per_file.most_common()] + [["**Total**", f"**{total_tests}**", ""]],
              [5.3, 1.3, 9.3], "Automated tests")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=LIVE_URL)
    parser.add_argument("--out", default=str(ROOT / "CashFlowIQ_Code_Explanation.pdf"))
    parser.add_argument("--docx", help="also keep the Word file at this path")
    args = parser.parse_args()
    doc = Doc()
    build(doc, args.url)
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = Path(args.docx) if args.docx else Path(tmp) / "CashFlowIQ_Code_Explanation.docx"
        doc.save(docx_path)
        script = Path(tmp) / "export.ps1"
        script.write_text(WORD_PS, encoding="ascii")
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                                  "-Docx", str(docx_path), "-Pdf", str(Path(args.out).resolve())],
                                 capture_output=True, text=True, timeout=600)
            ok = res.returncode == 0 and Path(args.out).exists()
        except (OSError, subprocess.SubprocessError):
            ok, res = False, None
        if ok:
            print(f"Written: {args.out}  ({res.stdout.strip()})")
        else:
            keep = ROOT / "CashFlowIQ_Code_Explanation.docx"
            doc.save(keep)
            print(f"Microsoft Word was not available, so no PDF was made. Open {keep} in Word and "
                  "export it as PDF.")


if __name__ == "__main__":
    main()
