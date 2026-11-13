"""
formulas.py - Named formulas used by COMPUTE rules.

A COMPUTE rule says e.g.  Compute("current_ratio", "current_ratio").
The engine looks the formula up in FORMULAS and calls it with
(working memory, thresholds).

DIVISION-BY-ZERO SAFETY
  Every division goes through safe_div(). If the denominator is 0 (e.g. no
  current liabilities, no sales, no fixed costs) the result is None, which
  means "not computable". The engine stores None, and ANY condition that
  tests a None fact is simply FALSE - so dependent rules safely skip.
"""
from knowledge_base.problems import PROBLEMS


def safe_div(numerator, denominator):
    """Return numerator / denominator, or None if it cannot be computed."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _sum(wm, *names):
    """Add several facts; None if any of them is missing."""
    values = [wm.get(n) for n in names]
    if any(v is None for v in values):
        return None
    return sum(values)


# ---------------- Ratio analysis ----------------
def liquid_cash(wm, th):
    return _sum(wm, "cash_in_hand", "bank_balance")


def current_assets(wm):
    return _sum(wm, "liquid_cash", "accounts_receivable", "inventory_value")


def current_liabilities(wm):
    return _sum(wm, "accounts_payable", "short_term_loans", "other_current_liabilities")


def current_ratio(wm, th):
    return safe_div(current_assets(wm), current_liabilities(wm))


def quick_ratio(wm, th):
    # Quick assets exclude inventory (stock cannot always be sold quickly)
    return safe_div(_sum(wm, "liquid_cash", "accounts_receivable"), current_liabilities(wm))


def cash_ratio(wm, th):
    return safe_div(wm.get("liquid_cash"), current_liabilities(wm))


def working_capital(wm, th):
    ca, cl = current_assets(wm), current_liabilities(wm)
    return None if ca is None or cl is None else ca - cl


# ---------------- Cash runway & cash flow ----------------
def monthly_gross_profit(wm, th):
    sales, margin = wm.get("monthly_sales"), wm.get("gross_margin_pct")
    return None if sales is None or margin is None else sales * margin / 100


def runway_days(wm, th):
    # cash / (monthly fixed expenses + installment) * 30
    monthly_outflow = _sum(wm, "monthly_fixed_expenses", "monthly_installment")
    months = safe_div(wm.get("liquid_cash"), monthly_outflow)
    return None if months is None else months * 30


def net_monthly_cash_flow(wm, th):
    gp = wm.get("monthly_gross_profit")
    outflow = _sum(wm, "monthly_fixed_expenses", "monthly_installment")
    return None if gp is None or outflow is None else gp - outflow


# ---------------- Receivables ----------------
def receivables_to_sales(wm, th):
    # How many months of sales are sitting with customers
    return safe_div(wm.get("accounts_receivable"), wm.get("monthly_sales"))


def credit_gap_days(wm, th):
    c, p = wm.get("collection_days"), wm.get("payment_days")
    return None if c is None or p is None else c - p


# ---------------- Inventory ----------------
def inventory_to_sales(wm, th):
    return safe_div(wm.get("inventory_value"), wm.get("monthly_sales"))


# ---------------- Payables ----------------
def cash_conversion_cycle(wm, th):
    # CCC = days to sell stock + days to collect - days to pay suppliers
    s, c, p = wm.get("stock_days"), wm.get("collection_days"), wm.get("payment_days")
    if None in (s, c, p):
        return None
    return s + c - p


# ---------------- Debt ----------------
def debt_service_ratio(wm, th):
    # Share of monthly gross profit consumed by the loan installment
    installment = wm.get("monthly_installment")
    if installment == 0:
        return 0.0          # no loan -> nothing to service (even if GP is 0)
    return safe_div(installment, wm.get("monthly_gross_profit"))


# ---------------- Final status ----------------
def health_score(wm, th):
    """
    100 - sum(severity weight x CF of each problem) + bonus for strengths,
    clamped to 0..100. Weights and bonus come from thresholds.json.
    """
    weights = {
        "Critical": th["weight_critical"], "High": th["weight_high"],
        "Medium": th["weight_medium"], "Low": th["weight_low"],
    }
    penalty = sum(weights[PROBLEMS[key]["severity"]] * rec.cf
                  for key, rec in wm.problems.items())
    bonus = min(len(wm.strengths) * th["strength_bonus"], th["max_strength_bonus"])
    return round(max(0.0, min(100.0, 100 - penalty + bonus)), 1)


def critical_problem_count(wm, th):
    """Critical problems that are Likely or stronger: combined CF >= cap_min_cf.
    A merely Possible Critical problem (e.g. from a 'Not sure' answer) does not cap."""
    return sum(1 for key, rec in wm.problems.items()
               if PROBLEMS[key]["severity"] == "Critical" and rec.cf >= th["cap_min_cf"])


def serious_problem_count(wm, th):
    """All Critical and High problems at ANY CF - each one blocks a Healthy status."""
    return sum(1 for key in wm.problems if PROBLEMS[key]["severity"] in ("Critical", "High"))


# Registry: formula name -> (function, human-readable formula for explanations)
FORMULAS = {
    "liquid_cash": (liquid_cash, "cash_in_hand + bank_balance"),
    "current_ratio": (current_ratio, "(liquid_cash + receivables + inventory) / (payables + short-term loans + other liabilities)"),
    "quick_ratio": (quick_ratio, "(liquid_cash + receivables) / current liabilities"),
    "cash_ratio": (cash_ratio, "liquid_cash / current liabilities"),
    "working_capital": (working_capital, "current assets - current liabilities"),
    "monthly_gross_profit": (monthly_gross_profit, "monthly_sales x gross_margin_pct / 100"),
    "runway_days": (runway_days, "liquid_cash / (fixed expenses + installment) x 30"),
    "net_monthly_cash_flow": (net_monthly_cash_flow, "gross profit - fixed expenses - installment"),
    "receivables_to_sales": (receivables_to_sales, "accounts_receivable / monthly_sales"),
    "credit_gap_days": (credit_gap_days, "collection_days - payment_days"),
    "inventory_to_sales": (inventory_to_sales, "inventory_value / monthly_sales"),
    "cash_conversion_cycle": (cash_conversion_cycle, "stock_days + collection_days - payment_days"),
    "debt_service_ratio": (debt_service_ratio, "monthly_installment / monthly_gross_profit"),
    "health_score": (health_score, "100 - sum(severity weight x CF) + strength bonus"),
    "critical_problem_count": (critical_problem_count, "number of Critical problems with CF >= cap_min_cf"),
    "serious_problem_count": (serious_problem_count, "number of Critical + High problems (any CF)"),
}
