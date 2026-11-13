# 💧 CashFlow IQ – Business Liquidity & Cash Flow Decision Expert System

**Live app:** https://cashflow-iq.streamlit.app/  
**Source code:** https://github.com/OwaisKamran/CashFlowIQ

A **rule-based expert system** (no machine learning, no AI APIs) that acts like a
*doctor for business cash flow* for small and medium businesses in Pakistan (PKR).

> **Symptoms & figures → derived facts (ratios) → diagnosis (liquidity problems) →
> treatment (cash-management decisions)**, each with a confidence % and an explanation.

| | |
|---|---|
| Rules | **95** (unique IDs R01–R95) in 10 groups, incl. 13 data-sufficiency rules |
| Problem catalog | 43 problems, each with severity, description and decisions |
| Inference | Custom **forward-chaining** engine (match → resolve → fire, HALT), MYCIN certainty factors |
| Explanation | **HOW** (full rule-firing trace) and **WHY** (questions & decisions) |
| UI | Streamlit (5 pages in 3 sidebar sections) – **For business owners:** Consultation, Quick Diagnosis · **For experts:** Knowledge Base, Knowledge Acquisition · **Info:** About |
| Tests | 122 pytest tests (engine, rules, data sufficiency, wizard steps, samples, UI) |

---

## 1. Features

- **Consultation** (default page) – a step-by-step wizard for first-time users:
  Welcome → Your business → Cash → Customers who owe you → Stock → Suppliers & loans →
  Warning signs → Review → Report. Plain-language questions with example values,
  amounts with thousand separators, "Next" blocked until required answers (including the
  business name) are given, errors shown under the field, skipped steps/questions explained,
  and a **Why are you asking?** link under every question (generated from the rule base).
- **Quick Diagnosis** – all steps on one page, 5 one-click sample businesses, the same
  questions, validation and report.
- **Report** (both modes) – plain English first: a 2–3 sentence generated summary, the top
  three actions ("What you should do"), problems found, key figures each with a one-line
  meaning, and a collapsed "How the system reached this" (HOW trace, WHY, working memory).
- **Data sufficiency** – with missing essential facts the system answers
  *Insufficient data* and halts instead of guessing; sanity rules flag odd inputs.
- **Knowledge Base** – all rules (ID, group, IF, THEN, CF, priority) with filters,
  counts by rule type, the problem catalog, and a rule inspector.
- **Knowledge Acquisition** – edit every threshold in the browser, with
  validation; download / upload `thresholds.json`.
- **About** – the six expert-system components and an architecture diagram.

The sidebar groups the pages into three sections: **For business owners** (Consultation,
Quick Diagnosis), **For experts** (Knowledge Base, Knowledge Acquisition – both marked
"This page is for experts and the knowledge engineer, not for business owners") and
**Info** (About). This uses `st.navigation` with a dict in `app.py`.

## 2. Run locally

Requires **Python 3.12+** (tested on 3.12 and 3.14).

```bash
# 1. create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

# 2. install dependencies (dev file adds pytest + python-docx)
pip install -r requirements-dev.txt

# 3. run the tests
pytest -q

# 4. start the app  ->  http://localhost:8501
streamlit run app.py
```

## 3. Folder structure

```
CashFlowIQ/
├── app.py                      # Streamlit entry point: page config, navigation, footer
├── views/                      # Streamlit pages
│   ├── consultation.py         #   one-question-at-a-time interview (default page)
│   ├── quick_diagnosis.py      #   all-in-one form + sample cases
│   ├── knowledge_base.py       #   rule browser & counts
│   ├── admin.py                #   knowledge acquisition (thresholds)
│   └── about.py                #   components + architecture diagram
├── knowledge_base/             # ---- KNOWLEDGE (data, no reasoning) ----
│   ├── rules.py                #   95 rules as data objects
│   ├── rule_model.py           #   Rule / Condition / Action data classes
│   ├── problems.py             #   PROBLEM CATALOG (severity, description, decisions)
│   ├── formulas.py             #   named, zero-safe formulas for COMPUTE rules
│   ├── questions.py            #   ordered questions with ask_if conditions, validation
│   ├── thresholds.json         #   every numeric threshold
│   └── __init__.py             #   threshold loading & validation
├── engine/                     # ---- REASONING (generic, domain-free) ----
│   ├── working_memory.py       #   fact base
│   ├── inference_engine.py     #   forward chaining + conflict resolution + trace
│   ├── certainty.py            #   MYCIN certainty-factor maths
│   ├── explanation.py          #   HOW & WHY
│   ├── consultation.py         #   wizard logic: steps, ask_if skipping, validation, WHY (why_asking)
│   └── diagnosis.py            #   one-call facade used by UI and tests
├── ui/
│   ├── styles.py               #   colour palette (named constants), type scale and CSS
│   ├── logo.svg                #   sidebar logo
│   ├── components.py           #   header band, pills, formatting (Rs 1,250,000), score bar, stepper
│   ├── fields.py               #   one question -> input, error, "Why are you asking?"
│   └── report.py               #   the diagnosis report shared by both modes
├── sample_cases.py             # 5 demo businesses
├── tests/                      # pytest suite
├── tools/make_pdf.py           # builds CashFlowIQ_Code_Explanation.pdf (via Word)
├── .streamlit/config.toml      # theme
├── requirements.txt            # runtime deps (pinned) – used by Streamlit Cloud
├── requirements-dev.txt        # + pytest, python-docx (local only)
├── README.md
└── VIVA_NOTES.md
```

## 4. Deploy to Streamlit Community Cloud (step by step)

### Step 1 – Put the project on GitHub
1. Create a free account at <https://github.com> (if you don't have one).
2. Click **New repository** → name it e.g. `cashflow-iq` → **Public** → *Create repository*
   (do not add a README; we already have one).
3. In a terminal inside the `CashFlowIQ` folder:
   ```bash
   git init
   git add .
   git commit -m "CashFlow IQ expert system"
   git branch -M main
   git remote add origin https://github.com/<your-username>/cashflow-iq.git
   git push -u origin main
   ```
   `.gitignore` already excludes `.venv/` and caches. Make sure `app.py` and
   `requirements.txt` are at the **root** of the repository.

   **No Git installed?** Either install [Git for Windows](https://git-scm.com/download/win)
   / [GitHub Desktop](https://desktop.github.com), or on the new repository page click
   **"uploading an existing file"** and drag in everything inside `CashFlowIQ/`
   **except the `.venv` folder** (keep the folder structure: `engine/`, `knowledge_base/`,
   `views/`, `ui/`, `tests/`, `tools/`, `.streamlit/`), then *Commit changes*.
   Note: the web uploader may hide the `.streamlit` folder – if so, create
   `.streamlit/config.toml` with **Add file → Create new file** and paste its contents.

### Step 2 – Create the app on Streamlit Cloud
1. Go to <https://share.streamlit.io> and **Sign in with GitHub**
   (authorise Streamlit to read your repositories).
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `OwaisKamran/CashFlowIQ`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** choose a name, e.g. `cashflow-iq` → `https://cashflow-iq.streamlit.app`
4. Open **Advanced settings** → **Python version** → select **3.12** → *Save*.
5. Click **Deploy**. The first build takes 2–4 minutes (it installs `requirements.txt`).

### Step 3 – Check and share
1. When the app opens, go to **Quick Diagnosis → Sample business → Lahore Spice Kitchen →
   Run diagnosis**; you should see status **Crisis**. Then go through a Consultation.
2. Copy the public URL and paste it into this README, the PDF (see below) and your submission.
3. Every `git push` to `main` redeploys automatically.

**Troubleshooting**
- *ModuleNotFoundError* → the package is missing from `requirements.txt`, or the
  main file path is wrong.
- *App sleeping* → free apps sleep after inactivity; open the URL and click
  **"Yes, get this app back up"** a few minutes before your viva.
- Threshold edits on the Knowledge Acquisition page are **per session** (Cloud storage is not
  permanent) – use Download/Upload to keep them.

## 5. Build the code-explanation PDF

```bash
python tools/make_pdf.py
```
This builds `CashFlowIQ_Code_Explanation.pdf` with the live link. The code excerpts, the
worked example and the test counts are taken from the code each time, so the PDF always
matches the program. The document is written with python-docx and converted to PDF by
Microsoft Word (Windows); without Word, the `.docx` is kept for you to export by hand.

## 6. Submission checklist
- [ ] Zip of the project folder (exclude `.venv/`)
- [ ] `CashFlowIQ_Code_Explanation.pdf` (rebuilt with the live link)
- [ ] Live Streamlit URL

---
*For educational purposes only — not financial advice.*
