# CashFlow IQ – Viva Notes

## 1. One-minute pitch
CashFlow IQ is a **rule-based expert system** that diagnoses the liquidity and cash-flow
health of a small/medium Pakistani business. Like a doctor it goes
**symptoms → tests (ratios) → diagnosis (problems) → treatment (decisions)**.
It has **95 IF-THEN rules**, a custom **forward-chaining inference engine**, **MYCIN
certainty factors**, a **step-by-step consultation wizard** for first-time users,
a plain-English report, a **HOW/WHY explanation facility**, **data-sufficiency rules** that refuse to conclude
without data, and a **knowledge-acquisition** page. Python + Streamlit, deployed on
Streamlit Community Cloud. No machine learning, no AI APIs – every conclusion is traceable.

## 2. The six components (and where they are in the code)

| Component | File(s) | What it does |
|---|---|---|
| **User Interface** | `app.py`, `views/consultation.py`, `views/quick_diagnosis.py`, `ui/fields.py`, `ui/report.py` | Step-by-step Consultation wizard or one-page Quick Diagnosis; one shared report |
| **Knowledge Base** | `knowledge_base/rules.py`, `problems.py`, `formulas.py`, `questions.py`, `thresholds.json` | Expert knowledge stored as *data* |
| **Working Memory** | `engine/working_memory.py` | Input facts, derived facts, problems (with CF), strengths, missing facts, warnings |
| **Inference Engine** | `engine/inference_engine.py` | Forward chaining: match → conflict resolution → fire → repeat (or HALT) |
| **Explanation Facility** | `engine/explanation.py`, `engine/consultation.py` | HOW (trace) and WHY (questions & decisions) |
| **Knowledge Acquisition** | `views/admin.py` | Expert edits thresholds in the browser; download/upload JSON |

## 3. How a rule is represented
```python
Rule("R17", G2, "Runway under 30 days: cash runs out within a month.",
     (C("runway_days", "<", T("crisis_runway_days")),),          # IF
     (Assert("runway_band", "critical"),                          # THEN
      RaiseProblem("cash_runs_out_within_month")),
     0.95,        # certainty factor of the expert
     P_BAND)      # priority (90) for conflict resolution
```
- `T("crisis_runway_days")` is looked up in `thresholds.json` **at match time** – no hard-coded numbers.
- `RaiseProblem("...")` refers to the **problem catalog** (severity, description, decisions).
- Action types: `Compute`, `Assert`, `RaiseProblem`, `AddStrength`, `Recommend`,
  and for data checks `FlagMissing`, `Warn`, `Halt`.
- Condition operators: `< <= > >= == != in` plus `known`, `unknown`, `missing`, `empty`.

**Rule groups (95):** Data Sufficiency 13 · Ratio Analysis 14 · Cash Runway 9 · Receivables 10 ·
Inventory 7 · Payables 7 · Debt 6 · Seasonal & Business Type 6 · Symptoms 11 · Final Status 12.
By type: 13 data-check, 16 compute, 50 decision, 15 classification/status.
(The data-sufficiency group is R82–R94 and the debt-free rule is R95, numbered last so that the original IDs R01–R81 stayed stable.)

## 4. Forward chaining in our engine
Forward chaining is **data-driven**: start from known facts, fire every rule whose IF part
is satisfied, add the conclusions as new facts, repeat until nothing new can be inferred.

```
while True:
    conflict_set = [rules not yet fired whose conditions are ALL true]   # MATCH
    if conflict_set is empty: stop
    rule = pick one (priority, specificity, order)                       # RESOLVE
    execute rule's actions, log to trace                                  # FIRE
    if the rule executed HALT: stop
```
- **Refraction:** a rule fires at most once → at most N cycles → **guaranteed termination**.
- **HALT:** R93 stops the engine when essential data is missing (like CLIPS `(halt)`).
- **Chaining example (Hamza Textiles):** R40 computes CCC = 100 days → R41 asserts
  `ccc_band = long` → R62 (`sales_up_cash_down = Yes` AND `ccc_band = long`) → *Overtrading*.
  Other chains: R08 → R10 → R37, and R17 + R21 → R22 → R73 (Crisis).
- **None-safety:** a formula that cannot be computed (division by zero) gives `None`; any
  condition on a `None` fact is false, so dependent rules don't fire.

## 5. Conflict resolution strategy
1. **Priority** (higher first): data check 220 → sanity 210 → data verdict 200 → COMPUTE 100 →
   band 90 → diagnosis 70 → symptom 60 → chained 40 → crisis override 6 → scoring 5 →
   status 4 → status decisions 3.
2. **Specificity** – more conditions = more specific = preferred.
3. **Rule order** – lower rule ID wins (deterministic).

Why it matters: data checks must run **before** anything else; the health score
(priority 5) must run **after** all diagnosis because it sums every problem.

## 6. Certainty factors (MYCIN)
- **Conclusion CF** = rule CF × min(CF of the matched facts).
- **Combining** two rules that support the same problem: `CF = CF1 + CF2 × (1 − CF1)`.
  Example: R28 (slow collections) 0.60 and R59 (customers pay late) 0.50 → **0.80**.
- Full formula (also implemented): both negative `CF1 + CF2(1 + CF1)`; mixed
  `(CF1 + CF2) / (1 − min(|CF1|, |CF2|))`.

### 6b. "Not sure" answers (uncertain evidence)
- Every warning-sign question offers **Yes / No / Not sure** with **nothing pre-selected**.
  Before, an unanswered question silently counted as a real "No". Now **Next** (and **Run
  diagnosis**) is blocked until each shown question is answered: *"Please choose an answer
  (pick 'Not sure' if you don't know)."* Questions skipped by `ask_if` still default to No.
- "Not sure" is stored as the fact value `not_sure` with **CF = `not_sure_cf` = 0.5**
  (in `thresholds.json`, editable on the Knowledge Acquisition page) instead of 1.0.
- Rules that test **"symptom = Yes"** (the `yes` condition) also match "Not sure"; no new
  maths is needed – the existing rule **conclusion CF = rule CF × min(CF of matched facts)**
  halves the conclusion. Example: R69 (overdue tax, CF 0.90) on "Not sure" → **0.45**.
  Rules that need "No" (`not_yes`) do **not** fire on "Not sure" – unsure is not a No.
- It **combines** with other evidence as usual: Hamza Textiles' slow collections give R28
  0.60; "Not sure" about late customers gives R59 0.50 × 0.5 = 0.25 →
  0.60 + 0.25 × (1 − 0.60) = **0.70** (with a firm Yes it would be 0.80).
- **Report:** a problem raised *only* from "Not sure" answers shows as **Possible** with
  *"You weren't sure about this — worth checking."*; the summary says "You weren't sure
  whether … – worth checking" instead of stating it as fact. The **HOW** trace shows the
  answer as *Not sure (CF 0.50)* and the reduced CF of the rule.
- Safety caps stay cautious: a Critical problem counts for R76 even when it is only Possible.

## 7. Data sufficiency (Group 0)
An expert must not conclude without data. Before: an empty form scored "Healthy 100",
because no problem rule fired. Now:
- **R82–R87** (priority 220) flag missing essentials: cash in hand, bank balance,
  monthly sales (> 0), gross margin, fixed expenses, and at least one current liability –
  unless the owner ticks **"I don't owe anything right now"** (fact `owes_nothing`).
  Missing = not entered (`None`); 0 is real data (zero cash is a valid – alarming – fact).
- **R88–R92** (priority 210) are **sanity checks**: e.g. receivables but zero sales,
  0% gross margin with sales, stock value with 0 stock days. They warn, they don't block.
- **R93** (priority 200): if anything is missing → status *Insufficient data* and **HALT**:
  no ratios judged, no health score. **R94**: otherwise assert `data_sufficient = True`,
  which the scoring rules R70–R72 require.
- Two layers: the wizard's `validate_step()` catches missing answers *before* the diagnosis
  (friendly messages under the fields); the G0 rules are the knowledge-base safety net that
  guarantees no conclusion is ever drawn from incomplete facts, whatever the interface.

## 8. Consultation wizard (designed for a first-time user)
- **Welcome** (what it does, ~3 minutes, what you get) → **6 steps** → **Review** → **Report**:
  1 Your business (name *required*, type, season) · 2 Cash · 3 Customers who owe you ·
  4 Stock · 5 Suppliers & loans · 6 Warning signs (Yes / No / Not sure, none pre-selected).
- `questions.py` holds the **ordered questions**, each with its step, a plain-language label
  (e.g. *"Money customers owe you (receivables)"*), an example value, `required`, `ask_if`
  conditions and a plain `skip_text`.
- `ask_if` uses the **same condition language as the rules** and the same
  `evaluate_condition()`. Examples: payment days only if `accounts_payable > 0`; installment
  and running finance only if `short_term_loans > 0`; the whole Stock step is skipped when
  `business_type == services` ("Step 4 – Stock was skipped because you run a service business").
- `engine/consultation.py` (pure Python, unit-tested):
  `resolve(answers)` decides shown/skipped questions and fills defaults;
  `validate_step(step, answers)` returns plain error messages per field
  (e.g. "Please enter your business name.", "Monthly sales must be more than 0.");
  `next_step` / `previous_step` jump over skipped steps.
- **Next** is blocked until the step validates; the error is shown under the field and
  disappears as soon as it is fixed. **Edit** on the review screen returns to the review.
- Amounts are typed with thousand separators ("1,250,000") and parsed by `parse_amount()`.
- **Keyboard friendly:** Enter saves a box and moves to the next one; on the last box of a
  step it presses Next and puts the cursor in the first box of the new step (a small script
  in `ui/components.py` – it changes navigation only, never the reasoning).
- At the end the **same `diagnose()`** runs and the same report is shown.

**Sidebar sections** (`st.navigation` with a dict in `app.py`): **For business owners** –
Consultation, Quick Diagnosis; **For experts** – Knowledge Base, Knowledge Acquisition (each
starts with "This page is for experts and the knowledge engineer, not for business owners");
**Info** – About. Owners never need the expert pages; the examiner can find them at once.

## 9. The report (plain English first)
1. **Summary** – 2–3 sentences generated by `plain_summary()` from working-memory facts and
   the problems the rules raised, e.g. *"Hamza Textiles Wholesale is on WATCH … Your cash covers
   about 106 days … The main concern is that sales are growing faster than your cash."*
   Each problem in the catalog has a plain "concern" phrase with fact placeholders.
2. **What you should do** – the top three ranked actions with one-line reasons; the rest in
   "Show all actions".
3. **What we found** – problems by severity with confidence.
4. **Key figures** – each ratio with a one-line meaning from `figure_meaning()`, e.g.
   *"Current ratio 0.24 – you owe more in the short term than you have in short-term assets."*
5. **How the system reached this** – collapsed: HOW trace, WHY per action, working memory.

Business owners see **plain words** ("Do this now", "Serious", "Very likely"); a switch
**"Show technical details"** reveals the expert-system view for the examiner: severity, the
exact certainty factor (e.g. CF 0.95) and the rule IDs behind every action and problem.
The health score shows a coloured number and a marker on the bar, so it is visible even at 0.

## 9b. The WHY facility
- **Why are you asking?** (under every question) – generated from the rule base.
  Call chain: `ui/fields.py: why_text()` → `engine/consultation.py: why_asking()`, which
  combines `rules_using_fact()` (in `engine/explanation.py`: the rules that test the fact
  directly, and the rules it feeds through derived facts, e.g. cash → liquid_cash →
  current ratio) with `ask_reason()` (the plain reason the question is shown: "I am asking
  because you told us customers owe you money", plus its `ask_if` condition). Nothing is
  hand-written, so it always matches the rules.
- **Why was this action recommended?** – the problem it treats, every rule that raised it
  with the facts that matched, and the CF combination arithmetic.
- **HOW** – the full trace: each cycle's fired rule, matched facts, conclusions, CF and
  conflict-set size.

## 9c. Knowledge sources & limitations
**Sources**
- **Standard financial ratio analysis** as taught in accounting / financial management:
  current, quick and cash ratio, cash conversion cycle, debt service ratio.
- **Common bank credit-assessment practice**: checks on cash cover, repayment capacity and
  working capital that a lender makes before extending credit.
- **Thresholds** are general rules of thumb and vary by industry. They live in
  `thresholds.json`, so an expert can tune them on the Knowledge Acquisition page
  without changing any code.
- **Certainty factors** were assigned by the knowledge engineer according to how strong each
  warning sign is – just as MYCIN's CFs came from expert judgment, not from statistics.

**Limitations**
- **Self-reported data** – only as accurate as the figures the owner enters.
- **Single point-in-time snapshot** – no history, so trends are not detected.
- **Not industry-benchmarked** – one set of thresholds for all businesses unless tuned.
- **Advisory, not predictive** – it flags risks and suggests actions; it does not forecast.

## 10. Twenty likely viva questions

1. **What is an expert system?** A program that solves problems in a narrow domain using
   expert knowledge stored as rules, plus an inference engine that reasons with them and
   can explain its reasoning.
2. **Why is this an expert system and not just an if-else program?** Knowledge is data
   separate from a generic engine; rules are matched dynamically, chained, weighted by
   certainty and explained – adding a rule needs no change to the engine.
3. **Forward vs backward chaining – which and why?** Forward (data-driven): we want every
   problem the figures imply. The consultation *feels* goal-driven, but it only decides which
   facts to collect; the reasoning itself is forward chaining.
4. **How does your engine stop?** When the conflict set is empty (refraction guarantees this
   within N cycles), or when a rule executes HALT (R93, insufficient data).
5. **What is the conflict set?** All rules whose conditions are true in the current cycle and
   that have not fired yet.
6. **How do you resolve conflicts?** Priority, then specificity, then rule order.
7. **What happens with an empty form?** The data-sufficiency rules flag every missing essential,
   R93 sets *Insufficient data* and halts – no score, no diagnosis. An expert does not guess.
8. **What is a certainty factor?** A belief measure from MYCIN. Conclusion CF = rule CF × weakest
   premise; parallel evidence is combined with CF1 + CF2(1 − CF1).
9. **Show CF combination.** 0.6 and 0.5 → 0.6 + 0.5(1 − 0.6) = 0.8 (*Weak credit control*).
10. **How does the wizard decide what to ask?** `resolve()` walks the ordered questions and
    tests each one's `ask_if` with the same condition evaluator as the rules; a step with no
    question left to ask is skipped as a whole, and `validate_step()` blocks Next until the
    step's required answers (e.g. the business name) are given.
11. **How is "Why are you asking?" produced?** By searching the rule base for rules whose
    conditions use the fact (directly or through derived facts) – generated, not typed.
12. **How is the plain-English summary produced – is it AI?** No. `plain_summary()` fills
    fixed sentence templates with facts from working memory (runway days, monthly cash
    left over) and the "concern" phrase of the most serious problems the rules raised.
13. **What is the cash conversion cycle?** Stock days + collection days − payment days.
14. **How do you avoid division by zero?** `safe_div` returns `None`; conditions on `None` are
    false. Inputs are validated (no negatives, days ≤ 365/730, percentages ≤ 100), and the
    data-sufficiency rules require sales > 0 and at least one current liability.
15. **Where is knowledge acquisition?** The **Knowledge Acquisition** page (sidebar section
    *For experts*) edits and validates thresholds for the session; JSON download/upload
    preserves them (Streamlit Cloud storage is temporary).
16. **Can a business be Healthy with a serious problem?** No. R76 caps any Critical problem at
    Risky; R78/R79 require zero Critical and zero High problems for Healthy.
17. **How did you test it?** 115 pytest tests: rule-base integrity, engine termination and
    conflict resolution, CF maths, safety caps, zero-division, data sufficiency, wizard step
    validation (required business name, missing cash fields, liabilities), skipping and
    navigation, the plain summary, every sample case, "Not sure" answers (half CF, MYCIN
    combination with a numeric rule, No fires nothing, unanswered blocks Next), and headless
    UI tests (AppTest) for the full wizard, blocked Next, back/edit, the Why link and Quick
    Diagnosis.
18. **Why a problem catalog?** One place for each problem's severity, description and decisions;
    several rules can raise the same problem and each works on its own.
19. **Limitations?** General rule-of-thumb thresholds, user-entered averages, no time series,
    CF values are expert estimates; educational, not financial advice.
20. **How would you extend it?** Add rules (no engine change), industry-specific threshold sets,
    a sliding certainty for answers ("probably yes" = 0.7), monthly history to detect trends.
21. **What if the owner does not know an answer?** They pick **Not sure**. It is stored with
    CF 0.5 (`not_sure_cf`), so "symptom = Yes" rules still fire but at half certainty via
    rule CF × min(premise CFs) – e.g. overdue tax 0.90 → 0.45, shown as *Possible – worth
    checking*. Nothing is pre-selected, so silence is never mistaken for a "No".

**Bonus quick answers**
- *Why not `experta`?* Unmaintained and breaks on new Python versions; our own engine
  (under 250 lines, heavily commented) is fully explainable.
- *Why Streamlit?* Pure-Python UI, free public hosting on Streamlit Community Cloud.
- *Why are R82–R94 numbered last if they run first?* Execution order comes from priority,
  not from the ID; keeping R01–R81 unchanged kept all earlier references valid.
