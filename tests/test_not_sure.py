"""Yes / No / Not sure answers: no default, uncertain evidence, MYCIN combination."""
import pytest

from engine.certainty import combine
from engine.consultation import resolve, validate_step
from engine.diagnosis import diagnose
from engine.explanation import how_table, plain_summary
from engine.inference_engine import evaluate_condition
from engine.working_memory import WorkingMemory
from knowledge_base import load_thresholds, validate_thresholds
from knowledge_base.questions import NO_ANSWER_ERROR, QUESTIONS, questions_in_step
from knowledge_base.rule_model import NOT_SURE, Condition
from knowledge_base.rules import RULES
from sample_cases import SAMPLE_CASES

TH = load_thresholds()
HEALTHY = SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"]
WATCH = SAMPLE_CASES["Hamza Textiles Wholesale (Watch)"]["inputs"]
YES_NO = [q.key for q in QUESTIONS if q.kind == "yesno"]
RULE = {r.id: r for r in RULES}


def _step(result, rule_id):
    return next(s for s in result.trace if s.rule_id == rule_id)


# ---------------------------------------------------------------- no default
def test_unanswered_question_blocks_next():
    answers = {k: v for k, v in HEALTHY.items() if k not in YES_NO}
    errors, _ = validate_step(6, answers, TH)
    shown = resolve(answers, TH).shown
    expected = {q.key for q in questions_in_step(6) if q.key in shown}
    assert set(errors) == expected and expected                 # every shown question
    assert set(errors.values()) == {NO_ANSWER_ERROR}


def test_not_sure_is_a_valid_answer():
    answers = dict(HEALTHY, **{k: NOT_SURE for k in YES_NO})
    assert validate_step(6, answers, TH) == ({}, None)


def test_skipped_questions_still_default_to_no():
    answers = {k: v for k, v in HEALTHY.items() if k not in YES_NO}
    answers.update(business_type="services", inventory_value=None, owes_nothing=False)
    res = resolve(answers, TH)
    assert "stock_piling" not in res.shown and res.facts["stock_piling"] is False


def test_sample_cases_answer_every_question():
    for case in SAMPLE_CASES.values():
        assert all(case["inputs"][k] in (True, False) for k in YES_NO)


# ---------------------------------------------------------------- engine
def test_not_sure_fires_the_yes_rule_at_half_cf():
    result = diagnose(dict(HEALTHY, overdue_tax=NOT_SURE), TH)
    problem = result.problem_by_key["tax_arrears"]
    assert problem["cf"] == pytest.approx(RULE["R69"].cf * TH["not_sure_cf"])   # 0.90 x 0.5
    assert problem["unsure"] is True
    step = _step(result, "R69")
    assert step.cf == pytest.approx(0.45) and step.unsure == ["overdue_tax"]
    row = next(r for r in how_table(result.trace) if r["Rule"] == "R69")
    assert "Not sure (CF 0.50)" in row["Because (matched facts)"] and row["CF"] == 0.45


def test_not_sure_cf_comes_from_thresholds():
    th = dict(TH, not_sure_cf=0.3)
    result = diagnose(dict(HEALTHY, overdue_tax=NOT_SURE), th)
    assert result.problem_by_key["tax_arrears"]["cf"] == pytest.approx(0.27)


def test_not_sure_combines_with_a_numeric_rule():
    # Hamza: collections of 85 days -> R28 (CF 0.60) raises weak credit control;
    # "Not sure" about late customers -> R59 at 0.50 x 0.5 = 0.25; MYCIN combines them.
    result = diagnose(dict(WATCH, late_customers=NOT_SURE), TH)
    problem = result.problem_by_key["weak_credit_control"]
    cf_by_rule = {rule_id: cf for rule_id, cf, _ in problem["evidence"]}
    assert cf_by_rule == pytest.approx({"R28": 0.60, "R59": 0.25})
    assert problem["cf"] == pytest.approx(combine(0.60, 0.25))          # 0.70, order-independent
    assert problem["unsure"] is False            # backed by real figures, not only "Not sure"


def test_no_fires_no_symptom_rule():
    result = diagnose(dict(HEALTHY, **{k: False for k in YES_NO}), TH)
    symptom_rules = {r.id for r in RULES if any(c.fact in YES_NO for c in r.conditions)}
    assert symptom_rules and not symptom_rules & {s.rule_id for s in result.trace}
    assert result.status == "Healthy"


def test_not_sure_is_not_a_no():
    wm = WorkingMemory({"x": NOT_SURE})
    assert evaluate_condition(Condition("x", "yes", True), wm, TH)
    assert not evaluate_condition(Condition("x", "not_yes"), wm, TH)


def test_problem_from_not_sure_only_is_flagged_in_summary():
    result = diagnose(dict(HEALTHY, overdue_tax=NOT_SURE), TH)
    text = " ".join(plain_summary(result))
    assert "You weren't sure whether" in text and "worth checking" in text


def test_not_sure_cf_must_be_between_0_and_1():
    assert validate_thresholds(dict(TH, not_sure_cf=1.5), TH)
    assert validate_thresholds(dict(TH, not_sure_cf=0), TH)
    assert validate_thresholds(TH, TH) == []
