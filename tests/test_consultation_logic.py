"""Wizard logic: step validation, skipping, navigation, WHY, plain summary."""
from engine.consultation import (
    REVIEW_STEP, first_invalid_step, next_step, previous_step, resolve, step_is_skipped,
    validate_step, why_asking,
)
from engine.diagnosis import diagnose
from engine.explanation import figure_meaning, plain_summary
from knowledge_base import load_thresholds
from knowledge_base.problems import CONCERNS, PROBLEMS
from knowledge_base.questions import QUESTION_BY_KEY, QUESTIONS, STEPS, parse_amount
from knowledge_base.rules import RULES
from sample_cases import SAMPLE_CASES

TH = load_thresholds()
HAMZA = SAMPLE_CASES["Hamza Textiles Wholesale (Watch)"]["inputs"]


def services_answers():
    data = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"])
    data.update(business_type="services", accounts_receivable=None, accounts_payable=None,
                short_term_loans=None, other_current_liabilities=100_000)
    return data


# required business name / step validation
def test_business_name_is_required():
    errors, _ = validate_step(1, {"business_name": "", "business_type": "retail"}, TH)
    assert errors == {"business_name": "Please enter your business name."}
    errors, _ = validate_step(1, {"business_name": "   "}, TH)
    assert "business_name" in errors
    assert validate_step(1, {"business_name": "Al-Noor"}, TH) == ({}, None)


def test_cash_step_lists_each_missing_field():
    errors, _ = validate_step(2, {"cash_in_hand": 0}, TH)
    assert set(errors) == {"bank_balance", "monthly_sales", "gross_margin_pct",
                           "monthly_fixed_expenses"}                 # 0 cash is a valid answer
    errors, _ = validate_step(2, dict(HAMZA, monthly_sales=0), TH)
    assert errors == {"monthly_sales": "Monthly sales must be more than 0."}


def test_days_required_only_when_question_is_shown():
    errors, _ = validate_step(3, {"accounts_receivable": 500_000}, TH)
    assert errors == {"collection_days": "Please enter the number of days."}
    assert validate_step(3, {"accounts_receivable": None}, TH) == ({}, None)


def test_suppliers_step_needs_at_least_one_liability():
    _, step_error = validate_step(5, {}, TH)
    assert "at least one amount you owe" in step_error
    assert validate_step(5, {"other_current_liabilities": 50_000}, TH) == ({}, None)


def test_owes_nothing_tick_allows_next_and_skips_debt_questions():
    assert validate_step(5, {"owes_nothing": True}, TH) == ({}, None)
    data = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"], owes_nothing=True)
    res = resolve(data, TH)
    skipped = {q.key for q in res.skipped}
    assert {"accounts_payable", "short_term_loans", "other_current_liabilities",
            "payment_days", "monthly_installment", "rf_maxed", "delaying_suppliers"} <= skipped
    assert all(res.facts[k] == 0 for k in ("accounts_payable", "short_term_loans",
                                           "other_current_liabilities"))   # treated as 0
    result = diagnose(res.facts)
    assert result.status == "Healthy"
    assert "?" not in " ".join(plain_summary(result))


def test_samples_pass_every_step():
    for case in SAMPLE_CASES.values():
        assert first_invalid_step(case["inputs"], TH) is None


# skipping and navigation
def test_stock_step_skipped_for_services():
    answers = services_answers()
    assert step_is_skipped(4, answers, TH)
    assert next_step(3, answers, TH) == (5, [4])
    assert previous_step(5, answers, TH) == 3


def test_skipped_questions_get_defaults():
    res = resolve(services_answers(), TH)
    skipped = {q.key for q in res.skipped}
    assert {"collection_days", "inventory_value", "stock_days", "payment_days",
            "monthly_installment", "rf_maxed", "late_customers", "stock_piling"} <= skipped
    assert res.facts["payment_days"] == 0 and res.facts["rf_maxed"] is False
    assert diagnose(res.facts).sufficient
    assert all(q.skip_text for q in QUESTIONS if q.ask_if)      # every skip is explained


def test_last_step_leads_to_review():
    assert next_step(6, HAMZA, TH) == (REVIEW_STEP, [])
    assert previous_step(1, HAMZA, TH) == 0                    # back to the welcome screen


def test_wizard_answers_reach_expected_status():
    for name, case in SAMPLE_CASES.items():
        assert diagnose(resolve(case["inputs"], TH).facts).status == case["expected_status"], name


def test_parse_amount_accepts_separators():
    assert parse_amount("1,250,000") == (1_250_000.0, None)
    assert parse_amount("Rs 85,000") == (85_000.0, None)
    assert parse_amount("") == (None, None)
    assert parse_amount("abc")[1] and parse_amount("-5")[1]


def test_parse_amount_rounds_decimals_to_whole_rupees():
    assert parse_amount("1500.50") == (1501.0, None)            # half rounds up
    assert parse_amount("1,500.75") == (1501.0, None)
    assert parse_amount("25000.4") == (25_000.0, None)
    assert parse_amount("Rs 2,499.49") == (2499.0, None)
    assert parse_amount("0.5") == (1.0, None)
    assert parse_amount(1500.5) == (1501.0, None)               # numbers are rounded the same way
    assert parse_amount("1.2.3")[0] is None and parse_amount("1.2.3")[1]
    assert parse_amount("nan")[1] and parse_amount("inf")[1]


# WHY and plain language
def test_why_is_generated_from_rule_base():
    why = why_asking(QUESTION_BY_KEY["collection_days"], RULES)
    assert {"R25", "R26", "R27"} <= {rid for rid, _g, _d in why["direct"]}
    assert why["indirect"] and "accounts_receivable" in why["ask_reason"]


def test_every_problem_has_a_plain_concern():
    assert set(CONCERNS) == set(PROBLEMS)


def test_plain_summary_uses_facts():
    result = diagnose(HAMZA)
    text = " ".join(plain_summary(result))
    assert text.startswith("Hamza Textiles Wholesale is on WATCH")
    assert "106 days" in text                                   # runway from working memory
    assert "The main concern is that" in text and "?" not in text


def test_plain_summary_for_crisis_and_insufficient():
    crisis = " ".join(plain_summary(diagnose(SAMPLE_CASES["Lahore Spice Kitchen (Crisis)"]["inputs"])))
    assert "CRISIS" in crisis and "losing about Rs 130,000 a month" in crisis
    assert crisis.count("4 days") == 1                          # no repeated runway concern
    assert "Besides the cash shortage" in crisis
    empty = plain_summary(diagnose({"business_name": "Test"}))
    assert "could not diagnose Test" in empty[0]


def test_figure_meaning_is_plain():
    assert "owe more" in figure_meaning("current_ratio", 0.8, TH)
    assert "lose about Rs 130,000" in figure_meaning("net_monthly_cash_flow", -130_000, TH)
    assert figure_meaning("quick_ratio", None, TH).startswith("Could not")
    assert len(STEPS) == 6
