"""About page - explains the expert-system components and how a consultation works."""
from collections import Counter

import streamlit as st

from knowledge_base.problems import PROBLEMS
from knowledge_base.questions import QUESTIONS
from knowledge_base.rules import RULES
from ui.components import section

kinds = Counter(r.kind for r in RULES)

st.markdown("<div class='cf-eyebrow'>About</div>", unsafe_allow_html=True)
st.title("About CashFlow IQ")
st.markdown(
    "CashFlow IQ is a rule-based **expert system** that diagnoses the liquidity and cash-flow "
    "health of small and medium businesses in Pakistan. It works like a doctor: "
    "**symptoms and figures → derived facts (ratios) → diagnosis (problems) → treatment "
    "(cash-management decisions)**, each with a confidence level and an explanation.")
st.markdown("<p class='cf-muted'>No machine learning and no AI services are used. Every "
            "conclusion comes from explicit IF-THEN rules that can be listed, traced and "
            "explained.</p>", unsafe_allow_html=True)

section("Architecture")
st.graphviz_chart("""
digraph G {
  rankdir=TB; bgcolor="transparent"; nodesep=0.5; ranksep=0.45;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12,
        fillcolor="#F3F5F8", color="#1F3A5F", fontcolor="#1F2937"];
  edge [color="#6B7280", fontname="Helvetica", fontsize=9, fontcolor="#4B5563"];

  user   [label="Business owner", shape=ellipse, fillcolor="#FFFFFF"];
  expert [label="Domain expert", shape=ellipse, fillcolor="#FFFFFF"];
  ui     [label="1. User interface\\nConsultation · Quick diagnosis"];
  wm     [label="3. Working memory\\ninput + derived facts"];
  ie     [label="4. Inference engine\\nforward chaining\\nmatch → resolve → fire"];
  kb     [label="2. Knowledge base\\nrules · problem catalog\\nformulas · thresholds · questions"];
  ex     [label="5. Explanation facility\\nHOW trace · WHY"];
  ka     [label="6. Knowledge acquisition\\nKnowledge Acquisition page"];

  user -> ui [label="answers"];
  ui -> wm [label="assert facts"];
  wm -> ie [dir=both, label="read / add facts"];
  kb -> ie [label="rules"];
  kb -> ui [label="questions + ask_if", style=dashed];
  ie -> ex [label="trace"];
  ex -> ui [label="report, explanations"];
  expert -> ka;
  ka -> kb [label="edit thresholds"];
  {rank=same; user; expert}
  {rank=same; wm; kb}
}
""", width="content")

section("The six components")
components = [
    ("1. User interface", "app.py, views/",
     "Two ways to consult the system: a guided step-by-step Consultation and a one-page "
     "Quick Diagnosis. Both use the same questions, validation and report."),
    ("2. Knowledge base", "knowledge_base/",
     f"{len(RULES)} IF-THEN rules stored as data ({kinds['DATA CHECK']} data-check, "
     f"{kinds['COMPUTE']} compute, {kinds['DECISION']} decision, "
     f"{kinds['CLASSIFY'] + kinds['STATUS']} classification/status), a catalog of "
     f"{len(PROBLEMS)} problems, named formulas, {len(QUESTIONS)} questions and thresholds.json."),
    ("3. Working memory", "engine/working_memory.py",
     "The fact base: input facts, derived facts, problems with combined certainty factors, "
     "strengths, missing facts and warnings - each tagged with the rule that produced it."),
    ("4. Inference engine", "engine/inference_engine.py",
     "Forward chaining: match all rules, resolve conflicts (priority, specificity, rule order), "
     "fire one rule, repeat until nothing new can be inferred or a rule halts the engine. "
     "Certainty factors are combined MYCIN-style: CF = CF1 + CF2 × (1 − CF1)."),
    ("5. Explanation facility", "engine/explanation.py, engine/consultation.py",
     "HOW: the full rule-firing trace with the facts each rule matched. WHY: why a question is "
     "asked (why_asking() in engine/consultation.py, built from rules_using_fact() and "
     "ask_reason()) and why an action was recommended - both generated from the rule base."),
    ("6. Knowledge acquisition", "views/admin.py",
     "A domain expert edits thresholds in the browser; they are validated and can be "
     "downloaded or uploaded as thresholds.json."),
]
for title, where, text in components:
    st.markdown(f"**{title}** <span class='cf-muted'>· <code>{where}</code></span><br>{text}",
                unsafe_allow_html=True)

section("Pages")
st.markdown("""
The sidebar groups the pages into three sections:

- **For business owners** - *Consultation* (step-by-step) and *Quick Diagnosis* (one page).
- **For experts** - *Knowledge Base* (all rules and the problem catalog) and *Knowledge
  Acquisition* (edit thresholds). These are for experts and the knowledge engineer, not for
  business owners.
- **Info** - *About* (this page).
""")

section("Consultation (step-by-step wizard)")
st.markdown("""
The Consultation page guides a first-time user through six short steps:
**Your business → Cash → Customers who owe you → Stock → Suppliers & loans → Warning signs**,
then a **review** screen and the **report**.

- Every question is in plain language with an example value; amounts are typed with
  thousand separators (e.g. 1,250,000).
- **Next** is blocked until the step's required answers are given (e.g. business name,
  cash, sales); the error appears under the field in plain words.
- Each question has **ask_if conditions** in the same condition language as the rules.
  *Payment days* is asked only if you owe suppliers; the whole *Stock* step is skipped for a
  service business. A short line explains every skip.
- **Why are you asking?** under each question lists the rules that use the answer,
  generated from the rule base.
- Back, Edit (from the review) and Start again are always available; changing an answer
  automatically re-decides which later questions are needed.
""")

section("The report")
st.markdown("""
Plain English first: a 2–3 sentence summary generated from the facts and the problems the
rules found, then **What you should do** (top three actions), **What we found**, and the
**Key figures** with a one-line meaning each. *How the system reached this* (the rule trace)
is kept at the bottom for anyone who wants the reasoning.
""")

section("Data sufficiency")
st.markdown("""
An expert must not conclude without data. Before any analysis, the **Group 0 rules
(R82–R94, highest priority)** check that the essential facts are present: cash in hand,
bank balance, monthly sales (> 0), gross margin, fixed expenses and at least one current
liability - unless the owner ticks "I don't owe anything right now". A debt-free business is
not missing data: rule **R95** records it as a strength ("No short-term debt"), because the
liquidity ratios cannot be computed when there is nothing to divide by. If anything is missing, rule **R93** sets the status to *Insufficient data* and
**halts** the inference engine, so no health score or diagnosis is produced. Sanity rules
(R88–R92) warn about inconsistent inputs, such as receivables with zero sales.
""")

section("Status logic")
st.markdown("""
After all diagnosis rules have fired, the health score is computed
(100 − Σ severity weight × CF + strength bonus). Status rules then decide *Healthy*, *Watch*,
*Risky* or *Crisis*, with safety caps: any Critical problem limits the status to Risky at
best, and Healthy requires zero Critical and zero High problems.
""")

section("Knowledge sources & limitations")
st.markdown("""
**Where the knowledge comes from**

- **Standard financial ratio analysis** as taught in accounting and financial management:
  current ratio, quick ratio, cash ratio, cash conversion cycle and debt service ratio.
- **Common bank credit-assessment practice** - the kind of checks a lender makes on cash
  cover, repayment capacity and working capital before giving a business credit.
- **Thresholds** (for example "a current ratio of 1.5 or more is safe") are general rules of
  thumb; the right values vary by industry. They are kept in `thresholds.json`, so a domain
  expert can tune them on the **Knowledge Acquisition** page without changing code.
- **Certainty factors** were assigned by the knowledge engineer according to how strong each
  warning sign is - in the same way MYCIN's certainty factors came from expert judgment.

**Limitations**

- **Self-reported data** - the diagnosis is only as accurate as the figures entered.
- **A single snapshot** - one point in time, so trends (improving or getting worse) are not seen.
- **Not industry-benchmarked** - the same thresholds apply to every business unless an expert
  adjusts them.
- **Advisory, not predictive** - it points out risks and suggests actions; it does not forecast
  what will happen.
""")

section("Technology")
st.markdown("Python 3.12+, Streamlit, pandas, pytest. The inference engine is written from "
            "scratch (no `experta`), so every line can be explained.")
