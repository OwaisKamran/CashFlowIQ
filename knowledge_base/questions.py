"""
questions.py - What the system asks the user, in plain language.

One ordered list of Question objects drives BOTH user interfaces:
  * Consultation    - a step-by-step wizard (one STEP per screen)
  * Quick Diagnosis - every step on a single page

ask_if uses the SAME Condition objects as the rules (evaluated by the same
function in the inference engine), e.g. "ask payment days only if the business
owes suppliers money". When a question is skipped, its `default` is used and
`skip_text` tells the user why, in plain words.
"""
from dataclasses import dataclass, field

from knowledge_base.rule_model import NOT_SURE, Condition as C

BUSINESS_TYPES = ["retail", "wholesale", "manufacturing", "services", "restaurant", "trading"]
BUSINESS_TYPE_LABELS = {
    "retail": "Retail shop", "wholesale": "Wholesale", "manufacturing": "Manufacturing / factory",
    "services": "Services (no stock)", "restaurant": "Restaurant / food", "trading": "Trading / import-export",
}
SEASONS = ["peak", "normal", "off-season"]
SEASON_LABELS = {"peak": "Busy season", "normal": "Normal", "off-season": "Slow season"}

MAX_AMOUNT = 50_000_000_000      # Rs 50 billion - sensible upper bound for an SME
MAX_DAYS = 365                   # collection / payment days
MAX_STOCK_DAYS = 730             # stock can sit up to 2 years (dead stock)

# Wizard steps: number -> (title, one-line explanation for the user)
STEPS = {
    1: ("Your business", "Tell us who you are. This only takes a few seconds."),
    2: ("Cash", "Your cash, sales and costs in a normal month. Rough figures are fine."),
    3: ("Customers who owe you", "Money you are waiting to receive from customers."),
    4: ("Stock", "Goods you hold for sale (or ingredients, for a restaurant)."),
    5: ("Suppliers & loans", "What you owe suppliers, the bank and others in the next year."),
    6: ("Warning signs", "Quick questions about how things are going. Answer Yes, No or Not sure."),
}
LIABILITY_STEP = 5


@dataclass(frozen=True)
class Question:
    key: str                 # fact name in working memory
    text: str                # plain-language label shown to the user
    label: str               # short name for the review table / transcript
    kind: str                # "text" | "choice" | "amount" | "days" | "percent" | "yesno" | "checkbox"
    #                          yesno = Yes / No / Not sure, no pre-selected answer
    step: int
    help: str = ""           # one-line hint (shown as a tooltip)
    example: str = ""        # example value shown inside the empty field
    required: bool = False   # must be answered when the question is shown
    options: tuple = ()
    min: float = 0
    max: float = MAX_AMOUNT
    ask_if: tuple = field(default_factory=tuple)   # Conditions - ALL must hold
    skip_text: str = ""                            # plain reason shown when skipped
    default: object = 0.0                          # value used when skipped / left blank


_has_ar = C("accounts_receivable", ">", 0)
_has_ap = C("accounts_payable", ">", 0)
_has_stock = C("inventory_value", ">", 0)
_has_loans = C("short_term_loans", ">", 0)
_NO_CUSTOMER_CREDIT = "Not asked because no customers owe you money."
_NO_STOCK = "Not asked because you hold no stock."
_NO_LOANS = "Not asked because you have no loans or running finance."
_owes_something = C("owes_nothing", "not_yes")
_OWES_NOTHING = "Not asked because you said you don't owe anything right now."

QUESTIONS = [
    # ---------------- Step 1: Your business ----------------
    Question("business_name", "Business name", "Business name", "text", 1,
             "Used as the title of your report.", "e.g. Al-Noor General Store", required=True,
             default=""),
    Question("business_type", "What kind of business is it?", "Type of business", "choice", 1,
             "Different businesses have different normal payment and stock cycles.",
             options=tuple(BUSINESS_TYPES), default="retail"),
    Question("season", "Which season is it for your business right now?", "Season", "choice", 1,
             "Many businesses need extra cash to get through the slow season.",
             options=tuple(SEASONS), default="normal"),
    # ---------------- Step 2: Cash ----------------
    Question("cash_in_hand", "Cash in hand (in the shop or office)", "Cash in hand", "amount", 2,
             "Notes and coins you hold at the business today. Enter 0 if none.",
             "e.g. 150,000", required=True),
    Question("bank_balance", "Money in your business bank account(s)", "Bank balance", "amount", 2,
             "Total balance today across all business accounts. Enter 0 if none.",
             "e.g. 850,000", required=True),
    Question("monthly_sales", "Sales in a normal month", "Monthly sales", "amount", 2,
             "Total sales, cash and credit, in a typical month.", "e.g. 2,000,000", required=True),
    Question("gross_margin_pct", "Profit margin on what you sell (%)", "Profit margin", "percent", 2,
             "If you buy for Rs 80 and sell for Rs 100, your margin is 20%.", "e.g. 20",
             required=True, max=100),
    Question("monthly_fixed_expenses", "Fixed monthly costs (rent, salaries, bills)",
             "Fixed monthly costs", "amount", 2,
             "Costs you pay every month even if you sell nothing.", "e.g. 300,000", required=True),
    # ---------------- Step 3: Customers who owe you ----------------
    Question("accounts_receivable", "Money customers owe you (receivables)", "Money customers owe you",
             "amount", 3, "Unpaid amounts for goods or work already delivered. "
             "Leave blank if you only sell for cash.", "e.g. 400,000 (blank if none)"),
    Question("collection_days", "How many days do customers usually take to pay?",
             "Days customers take to pay", "days", 3,
             "An average is fine, e.g. most customers pay after about 30 days.", "e.g. 30",
             required=True, max=MAX_DAYS, ask_if=(_has_ar,), skip_text=_NO_CUSTOMER_CREDIT),
    # ---------------- Step 4: Stock ----------------
    Question("inventory_value", "Value of the stock you hold (at cost)", "Value of stock",
             "amount", 4, "What you paid for the goods on your shelves or in your warehouse. "
             "Leave blank if none.", "e.g. 1,200,000 (blank if none)",
             ask_if=(C("business_type", "!=", "services"),),
             skip_text="Skipped because you run a service business."),
    Question("stock_days", "How many days does stock usually take to sell?",
             "Days to sell stock", "days", 4,
             "For a restaurant: how many days ingredients are kept before use.", "e.g. 45",
             required=True, max=MAX_STOCK_DAYS, ask_if=(_has_stock,), skip_text=_NO_STOCK),
    # ---------------- Step 5: Suppliers & loans ----------------
    Question("owes_nothing", "I don't owe anything right now", "Owes nothing right now",
             "checkbox", 5, "Tick this if you have no unpaid supplier bills, no loans and no "
             "other bills due. The questions below will then be skipped.", default=False),
    Question("accounts_payable", "Money you owe suppliers (payables)", "Money owed to suppliers",
             "amount", 5, "Unpaid bills for goods you have already received. Leave blank if none.",
             "e.g. 600,000 (blank if none)", ask_if=(_owes_something,), skip_text=_OWES_NOTHING),
    Question("payment_days", "How many days do you usually take to pay suppliers?",
             "Days you take to pay suppliers", "days", 5, "An average is fine.", "e.g. 30",
             required=True, max=MAX_DAYS, ask_if=(_has_ap,),
             skip_text="Not asked because you owe suppliers nothing."),
    Question("short_term_loans", "Short-term loans or running finance owed to the bank",
             "Short-term loans", "amount", 5,
             "Amount still owed on loans due within a year, including overdraft / running finance.",
             "e.g. 500,000 (blank if none)", ask_if=(_owes_something,), skip_text=_OWES_NOTHING),
    Question("monthly_installment", "Total loan installment you pay each month",
             "Monthly loan installment", "amount", 5, "Principal plus markup paid every month.",
             "e.g. 60,000", ask_if=(_has_loans,), skip_text=_NO_LOANS),
    Question("rf_maxed", "Is your running finance (overdraft) limit fully used?",
             "Running finance fully used", "yesno", 5, "Answer No if you have no running finance.",
             ask_if=(_has_loans,), skip_text=_NO_LOANS, default=False),
    Question("other_current_liabilities", "Other bills due within a year (taxes, advances)",
             "Other bills due", "amount", 5, "For example tax payable or advances taken from customers.",
             "e.g. 100,000 (blank if none)", ask_if=(_owes_something,), skip_text=_OWES_NOTHING),
    # ---------------- Step 6: Warning signs ----------------
    Question("late_customers", "Do customers often pay you late?", "Customers often pay late",
             "yesno", 6, ask_if=(_has_ar,), skip_text=_NO_CUSTOMER_CREDIT, default=False),
    Question("big_customer", "Does one customer bring in more than 40% of your sales?",
             "One customer > 40% of sales", "yesno", 6,
             ask_if=(C("business_type", "in", ("wholesale", "manufacturing", "services", "trading")),),
             skip_text="Not asked because shops and restaurants rarely depend on one customer.",
             default=False),
    Question("stock_piling", "Is unsold stock piling up?", "Unsold stock piling up", "yesno", 6,
             ask_if=(_has_stock,), skip_text=_NO_STOCK, default=False),
    Question("delaying_suppliers", "Are you paying suppliers later than agreed?",
             "Paying suppliers late", "yesno", 6, ask_if=(_has_ap,),
             skip_text="Not asked because you owe suppliers nothing.", default=False),
    Question("overdue_tax", "Do you have unpaid taxes that are overdue?", "Overdue taxes",
             "yesno", 6, default=False),
    Question("sales_up_cash_down", "Are sales growing but your cash going down?",
             "Sales up, cash down", "yesno", 6, default=False),
    Question("personal_money", "Are you putting in personal or family money to keep the business going?",
             "Using personal money", "yesno", 6, default=False),
    Question("planning_expansion", "Are you planning a big purchase or expansion soon?",
             "Planning expansion", "yesno", 6, default=False),
]

QUESTION_BY_KEY = {q.key: q for q in QUESTIONS}
NUMERIC_FIELDS = {q.key: q for q in QUESTIONS if q.kind in ("amount", "days", "percent")}
SYMPTOMS = {q.key: q.text for q in QUESTIONS if q.kind in ("yesno", "checkbox")}
YES_NO_ANSWERS = {"Yes": True, "No": False, "Not sure": NOT_SURE}     # label -> stored value
NO_ANSWER_ERROR = "Please choose an answer (pick 'Not sure' if you don't know)."


def questions_in_step(step: int) -> list:
    return [q for q in QUESTIONS if q.step == step]


def parse_amount(text):
    """'1,250,000' / 'Rs 1,250,000' -> (1250000.0, None);  '' -> (None, None);  bad -> (None, error)."""
    if text is None:
        return None, None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text), None
    cleaned = str(text).lower().replace("rs", "").replace(",", "").replace(" ", "").strip()
    if cleaned == "":
        return None, None
    try:
        value = float(cleaned)
    except ValueError:
        return None, "Please enter a number, for example 250,000."
    if value < 0:
        return None, "The amount cannot be negative."
    if value > MAX_AMOUNT:
        return None, f"That is more than Rs {MAX_AMOUNT:,.0f} - please check the amount."
    return value, None


def default_inputs() -> dict:
    """An EMPTY form: numbers and Yes/No/Not sure answers are None (= not answered)."""
    data = {"business_name": "", "business_type": "retail", "season": "normal"}
    data.update({k: None for k in NUMERIC_FIELDS})
    data.update({k: None if QUESTION_BY_KEY[k].kind == "yesno" else False for k in SYMPTOMS})
    return data


def fill_optional_blanks(data: dict) -> dict:
    """Blank OPTIONAL numbers mean 'none' (0). Blank REQUIRED numbers stay None,
    so the data-sufficiency rules can report them as missing."""
    out = dict(data)
    for key, q in NUMERIC_FIELDS.items():
        if out.get(key) is None and not q.required:
            out[key] = q.default
    return out


def validate_inputs(data: dict) -> list:
    """Range/type errors (empty values are allowed - the G0 rules handle them)."""
    errors = []
    if data.get("business_type") not in BUSINESS_TYPES:
        errors.append("Business type must be one of: " + ", ".join(BUSINESS_TYPES))
    if data.get("season") not in SEASONS:
        errors.append("Season must be one of: " + ", ".join(SEASONS))
    for key, q in NUMERIC_FIELDS.items():
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{q.label}: must be a number.")
        elif value < q.min:
            errors.append(f"{q.label}: cannot be negative.")
        elif value > q.max:
            errors.append(f"{q.label}: must not exceed {q.max:,.0f}.")
    for key in SYMPTOMS:
        value = data.get(key)
        if QUESTION_BY_KEY[key].kind == "yesno":
            if value is not None and value not in (True, False, NOT_SURE):
                errors.append(f"Symptom '{key}' must be Yes, No or Not sure.")
        elif not isinstance(value, bool):
            errors.append(f"'{key}' must be ticked or not ticked.")
    return errors
