"""G0 data-sufficiency and sanity rules: no conclusions without data."""
from engine.diagnosis import diagnose
from knowledge_base.questions import QUESTIONS, default_inputs, fill_optional_blanks
from knowledge_base.rule_model import FlagMissing
from knowledge_base.rules import ESSENTIAL_FACTS, LIABILITY_FACTS, RULES
from sample_cases import SAMPLE_CASES


def missing_facts(result):
    return [m["fact"] for m in result.missing]


def test_empty_input_is_insufficient_data():
    result = diagnose(default_inputs())
    assert result.status == "Insufficient data"
    assert result.health_score is None                     # no score computed
    assert result.problems == [] and result.decisions == []
    assert set(missing_facts(result)) == set(ESSENTIAL_FACTS) | {"current_liabilities"}
    fired = [s.rule_id for s in result.trace]
    assert "R93" in fired and "R70" not in fired           # halted before scoring
    assert fired[-1] == "R93"                              # HALT is the last rule fired


def test_completely_absent_inputs_are_insufficient():
    assert diagnose({}).status == "Insufficient data"


def test_partial_input_lists_exactly_the_missing_facts():
    data = fill_optional_blanks(default_inputs())
    data.update(cash_in_hand=50_000, monthly_sales=900_000, accounts_payable=200_000)
    result = diagnose(data)
    assert result.status == "Insufficient data"
    assert missing_facts(result) == ["bank_balance", "gross_margin_pct", "monthly_fixed_expenses"]


def test_zero_sales_is_insufficient():
    data = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"], monthly_sales=0)
    result = diagnose(data)
    assert missing_facts(result) == ["monthly_sales"]
    assert "R88" in [w["rule_id"] for w in result.warnings]   # receivables but no sales


def test_no_liabilities_is_insufficient():
    data = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"])
    data.update({k: 0 for k in LIABILITY_FACTS})
    result = diagnose(data)
    assert missing_facts(result) == ["current_liabilities"]


def debt_free_inputs():
    data = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"])
    data.update({k: 0 for k in LIABILITY_FACTS}, monthly_installment=0, payment_days=0,
                owes_nothing=True)
    return data


def test_debt_free_business_gets_a_sensible_result():
    """Ticking 'I don't owe anything' = no short-term debt (a strength), not missing data."""
    result = diagnose(debt_free_inputs())
    fired = [s.rule_id for s in result.trace]
    assert result.sufficient and "R87" not in fired and "R95" in fired
    assert result.status == "Healthy" and result.health_score >= 75
    assert "No short-term debt" in [s["text"] for s in result.strengths]
    # liquidity ratios are not computable
    for metric in ("current_ratio", "quick_ratio", "cash_ratio"):
        assert result.metrics[metric] is None
    assert result.metrics["working_capital"] > 0
    assert not {"weak_current_ratio", "negative_working_capital",
                "quick_liquidity_shortfall"} & set(result.problem_by_key)
    assert result.warnings == []


def test_debt_free_with_cash_problems_still_diagnosed():
    data = debt_free_inputs()
    data.update(cash_in_hand=10_000, bank_balance=20_000, monthly_fixed_expenses=500_000,
                gross_margin_pct=10)
    result = diagnose(data)
    assert result.sufficient and result.status == "Crisis"      # no debt, but no cash either
    assert "No short-term debt" in [s["text"] for s in result.strengths]


def test_tick_is_ignored_when_debts_are_entered():
    data = dict(SAMPLE_CASES["Hamza Textiles Wholesale (Watch)"]["inputs"], owes_nothing=True)
    result = diagnose(data)
    assert "R95" not in [s.rule_id for s in result.trace]       # real debts -> normal ratios
    assert result.metrics["current_ratio"] is not None
    assert result.status == "Watch"


def test_one_liability_is_enough():
    data = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"])
    data.update(accounts_payable=0, short_term_loans=0, other_current_liabilities=50_000)
    assert diagnose(data).sufficient


def test_zero_cash_is_allowed_but_missing_cash_is_not():
    data = dict(SAMPLE_CASES["Lahore Spice Kitchen (Crisis)"]["inputs"], cash_in_hand=0, bank_balance=0)
    assert diagnose(data).status == "Crisis"                # 0 is real data
    data["cash_in_hand"] = None
    assert missing_facts(diagnose(data)) == ["cash_in_hand"]


def test_sanity_warnings_do_not_block_diagnosis():
    data = dict(SAMPLE_CASES["Hamza Textiles Wholesale (Watch)"]["inputs"], collection_days=0)
    result = diagnose(data)
    assert result.sufficient
    assert "R91" in [w["rule_id"] for w in result.warnings]


def test_sufficient_samples_have_data_sufficient_fact():
    for case in SAMPLE_CASES.values():
        result = diagnose(case["inputs"])
        assert result.sufficient and result.wm.get("data_sufficient") is True
        assert result.warnings == []


def test_required_questions_match_data_sufficiency_rules():
    flagged = {a.fact for r in RULES for a in r.actions if isinstance(a, FlagMissing)}
    assert flagged == set(ESSENTIAL_FACTS) | {"current_liabilities"}
    # required numbers = the essential facts of the G0 rules
    always_required = {q.key for q in QUESTIONS
                       if q.required and not q.ask_if and q.kind != "text"}
    assert always_required == set(ESSENTIAL_FACTS)
