"""Inference-engine behaviour: termination, conflict resolution, CF, safety rules."""
import pytest

from engine.certainty import combine, conclusion_cf
from engine.diagnosis import diagnose
from engine.inference_engine import InferenceEngine
from engine.working_memory import WorkingMemory
from knowledge_base import load_thresholds
from knowledge_base.formulas import safe_div
from knowledge_base.questions import default_inputs, validate_inputs
from knowledge_base.rule_model import NOT_SURE, Rule, Condition, Assert, RaiseProblem, known
from knowledge_base.rules import RULES
from sample_cases import SAMPLE_CASES


def healthy_inputs():
    return dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"])


# termination & refraction
@pytest.mark.parametrize("name", list(SAMPLE_CASES))
def test_engine_terminates_and_each_rule_fires_once(name):
    result = diagnose(SAMPLE_CASES[name]["inputs"])
    fired = [s.rule_id for s in result.trace]
    assert len(fired) == len(set(fired))            # refraction
    assert result.cycles <= len(RULES)              # bounded


def test_status_rules_fire_after_all_diagnosis():
    result = diagnose(SAMPLE_CASES["Hamza Textiles Wholesale (Watch)"]["inputs"])
    order = [s.rule_id for s in result.trace]
    score_step = order.index("R70")
    diagnosis_ids = {r.id for r in RULES if r.priority > 6}
    assert all(rid not in diagnosis_ids for rid in order[score_step:])


# conflict resolution
def test_conflict_resolution_priority_then_specificity():
    rules = [
        Rule("X1", "g", "low priority", (known("a"),), (Assert("winner", "X1"),), 1.0, 10),
        Rule("X2", "g", "high priority", (known("a"),), (Assert("winner", "X2"),), 1.0, 50),
        Rule("X3", "g", "high priority, more specific", (known("a"), known("b")),
             (Assert("winner", "X3"),), 1.0, 50),
    ]
    engine = InferenceEngine(rules, {})
    engine.run(WorkingMemory({"a": 1, "b": 2}))
    assert [s.rule_id for s in engine.trace] == ["X3", "X2", "X1"]


def test_forward_chaining_derived_fact_triggers_next_rule():
    rules = [
        Rule("A1", "g", "chain step 2", (Condition("x", "==", "yes"),),
             (Assert("y", "done"),), 1.0, 10),
        Rule("A2", "g", "chain step 1", (known("start"),), (Assert("x", "yes"),), 1.0, 1),
    ]
    engine = InferenceEngine(rules, {})
    wm = WorkingMemory({"start": True})
    engine.run(wm)
    assert wm.get("y") == "done"
    assert [s.rule_id for s in engine.trace] == ["A2", "A1"]


# certainty factors
def test_mycin_combination():
    assert combine(0.6, 0.5) == pytest.approx(0.8)
    assert combine(0.8, 0.8) == pytest.approx(0.96)
    assert combine(-0.5, -0.5) == pytest.approx(-0.75)
    assert combine(0.6, -0.4) == pytest.approx(0.2 / 0.6, rel=1e-3)
    assert conclusion_cf(0.8, [1.0, 0.75]) == pytest.approx(0.6)


def test_two_rules_combine_on_same_problem():
    result = diagnose(SAMPLE_CASES["Hamza Textiles Wholesale (Watch)"]["inputs"])
    credit = result.problem_by_key["weak_credit_control"]
    assert {e[0] for e in credit["evidence"]} == {"R28", "R59"}
    assert credit["cf"] == pytest.approx(combine(0.6, 0.5))


def test_symptom_rule_works_without_partner_rule():
    """R59 raises 'weak credit control' from the catalog even when R28 doesn't fire."""
    data = healthy_inputs()
    data["late_customers"] = True             # collections are fast -> R28 won't fire
    result = diagnose(data)
    credit = result.problem_by_key["weak_credit_control"]
    assert [e[0] for e in credit["evidence"]] == ["R59"]
    assert credit["cf"] == pytest.approx(0.5)
    assert credit["decisions"]                # decisions come from the catalog


# status safety rules
def test_critical_problem_caps_status_at_risky():
    """A Likely Critical problem caps the status at Risky (R76)."""
    data = healthy_inputs()
    data["monthly_installment"] = 300_000     # DSR > 0.5 -> 'Unsustainable debt' (Critical)
    data["bank_balance"] = 3_000_000          # keep runway comfortable
    result = diagnose(data)
    assert any(p["severity"] == "Critical" for p in result.problems)
    assert result.health_score >= load_thresholds()["watch_score"]
    assert result.status == "Risky"
    assert "R76" in [s.rule_id for s in result.trace]


def test_healthy_requires_no_high_problem():
    """Score >= 75 but a High problem exists -> Watch, not Healthy (R78)."""
    data = healthy_inputs()
    data["overdue_tax"] = True                # 'Tax arrears' is High
    result = diagnose(data)
    assert result.health_score >= load_thresholds()["healthy_score"]
    assert result.status == "Watch"
    assert "R78" in [s.rule_id for s in result.trace]


def _with_critical(cf, inputs=None):
    """Diagnose with an extra expert rule raising a Critical problem at this CF."""
    extra = Rule("X1", "Test", "Expert-added Critical rule", (known("liquid_cash"),),
                 (RaiseProblem("unsustainable_debt"),), cf, 70)
    return diagnose(inputs or healthy_inputs(), rules=RULES + [extra])


def test_possible_critical_does_not_cap_at_risky_but_blocks_healthy():
    """Critical at CF 0.40: no Risky cap (R76), but no Healthy either (R78)."""
    result = _with_critical(0.40)
    fired = [s.rule_id for s in result.trace]
    assert result.problem_by_key["unsustainable_debt"]["cf"] == pytest.approx(0.40)
    assert result.health_score >= load_thresholds()["healthy_score"]
    assert result.wm.get("critical_problem_count") == 0
    assert result.wm.get("serious_problem_count") == 1
    assert result.status == "Watch" and "R76" not in fired and "R78" in fired


def test_likely_critical_still_caps_at_risky():
    """Critical at CF 0.60: the cap R76 applies."""
    result = _with_critical(0.60)
    assert result.wm.get("critical_problem_count") == 1
    assert result.status == "Risky" and "R76" in [s.rule_id for s in result.trace]


def test_cap_min_cf_is_exactly_the_boundary():
    assert _with_critical(0.50).status == "Risky"                       # >= 0.5 caps
    assert _with_critical(0.49).status == "Watch"


def test_possible_critical_never_triggers_the_cap_but_still_lowers_the_score():
    """The cap stays silent, but the score penalty (30 x 0.40) still applies."""
    hamza = SAMPLE_CASES["Hamza Textiles Wholesale (Watch)"]["inputs"]
    result = _with_critical(0.40, hamza)
    fired = [s.rule_id for s in result.trace]
    assert result.wm.get("critical_problem_count") == 0
    assert "R76" not in fired and "R75" in fired
    assert result.health_score == pytest.approx(diagnose(hamza).health_score - 30 * 0.40)


def test_cap_min_cf_comes_from_thresholds():
    extra = Rule("X1", "Test", "Expert-added Critical rule", (known("liquid_cash"),),
                 (RaiseProblem("unsustainable_debt"),), 0.40, 70)
    th = dict(load_thresholds(), cap_min_cf=0.3)
    assert diagnose(healthy_inputs(), th, rules=RULES + [extra]).status == "Risky"


def test_possible_high_from_not_sure_blocks_healthy():
    """Not sure about overdue tax: High problem at CF 0.45 still blocks Healthy."""
    result = diagnose(dict(healthy_inputs(), overdue_tax=NOT_SURE))
    assert result.problem_by_key["tax_arrears"]["cf"] == pytest.approx(0.45)
    assert result.status == "Watch"


@pytest.mark.parametrize("name", list(SAMPLE_CASES))
def test_status_safety_invariants_hold(name):
    result = diagnose(SAMPLE_CASES[name]["inputs"])
    cap = load_thresholds()["cap_min_cf"]
    if any(p["severity"] == "Critical" and p["cf"] >= cap for p in result.problems):
        assert result.status in ("Risky", "Crisis")
    if result.status == "Healthy":
        assert not {p["severity"] for p in result.problems} & {"Critical", "High"}


def test_imminent_crisis_overrides_score():
    result = diagnose(SAMPLE_CASES["Lahore Spice Kitchen (Crisis)"]["inputs"])
    assert "R73" in [s.rule_id for s in result.trace]
    assert result.status == "Crisis"


# division by zero / bad data
def test_safe_div():
    assert safe_div(10, 0) is None
    assert safe_div(None, 5) is None
    assert safe_div(10, 4) == 2.5


def test_all_zero_inputs_do_not_crash():
    data = {k: (0.0 if v is None else v) for k, v in default_inputs().items()}
    result = diagnose(data)
    assert result.status == "Insufficient data"
    assert result.health_score is None


def test_zero_costs_are_zero_safe():
    """Fixed costs and installment both 0 -> runway not computable, rules skip safely."""
    data = healthy_inputs()
    data.update(monthly_fixed_expenses=0, monthly_installment=0)
    result = diagnose(data)
    assert result.metrics["runway_days"] is None
    assert result.metrics["debt_service_ratio"] == 0
    fired = {s.rule_id for s in result.trace}
    assert not fired & {"R17", "R18", "R19", "R20"}
    assert result.status in ("Healthy", "Watch", "Risky", "Crisis")


def test_zero_gross_profit_with_loan():
    data = healthy_inputs()
    data["gross_margin_pct"] = 0
    result = diagnose(data)
    assert result.metrics["debt_service_ratio"] is None
    assert "monthly_cash_burn" in result.problem_by_key
    assert [w["rule_id"] for w in result.warnings] == ["R89"]      # sanity warning


def test_validation_rejects_bad_inputs():
    data = healthy_inputs()
    assert validate_inputs(data) == []
    data.update(cash_in_hand=-1, collection_days=400, gross_margin_pct=150, business_type="bank")
    errors = validate_inputs(data)
    assert len(errors) == 4


def test_every_case_gets_collection_and_debt_band():
    for case in SAMPLE_CASES.values():
        result = diagnose(case["inputs"])
        assert result.wm.get("collection_band") in ("normal", "slow", "very_slow")
        assert result.wm.get("debt_band") in ("normal", "moderate", "heavy")


def test_thresholds_change_conclusions():
    """Knowledge acquisition: editing a threshold changes the reasoning."""
    data = healthy_inputs()
    th = load_thresholds()
    th["safe_runway_days"] = 500              # demand > 16 months of runway
    th["short_runway_days"] = 400
    result = diagnose(data, th)
    assert result.wm.get("runway_band") == "short"
