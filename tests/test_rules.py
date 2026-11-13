"""Knowledge-base integrity tests."""
import re

from knowledge_base import load_thresholds, validate_thresholds
from knowledge_base.formulas import FORMULAS
from knowledge_base.problems import PROBLEMS, SEVERITY_RANK
from knowledge_base.rule_model import T, Compute, RaiseProblem
from knowledge_base.rules import RULES, RULE_GROUPS


def test_rule_count_at_least_50():
    assert len(RULES) >= 50


def test_rule_ids_unique_and_well_formed():
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids)), "duplicate rule IDs"
    assert all(re.fullmatch(r"R\d{2,3}", i) for i in ids)


def test_rule_ids_are_sequential():
    assert [r.id for r in RULES] == [f"R{i:02d}" for i in range(1, len(RULES) + 1)]


def test_every_group_has_rules():
    for group in RULE_GROUPS:
        assert any(r.group == group for r in RULES), group


def test_certainty_factors_in_range():
    assert all(0 < r.cf <= 1 for r in RULES)


def test_all_threshold_references_exist():
    thresholds = load_thresholds()
    for rule in RULES:
        for cond in rule.conditions:
            if isinstance(cond.value, T):
                assert cond.value.name in thresholds, f"{rule.id}: {cond.value.name}"


def test_no_unused_thresholds():
    used = {c.value.name for r in RULES for c in r.conditions if isinstance(c.value, T)}
    scoring = {"weight_critical", "weight_high", "weight_medium", "weight_low",
               "strength_bonus", "max_strength_bonus"}
    assert set(load_thresholds()) - used - scoring == set()


def test_all_problem_and_formula_references_exist():
    for rule in RULES:
        for action in rule.actions:
            if isinstance(action, RaiseProblem):
                assert action.key in PROBLEMS, f"{rule.id}: {action.key}"
            if isinstance(action, Compute):
                assert action.formula in FORMULAS, f"{rule.id}: {action.formula}"


def test_default_thresholds_are_valid():
    th = load_thresholds()
    assert validate_thresholds(th, th) == []


def test_threshold_validation_catches_bad_edits():
    defaults = load_thresholds()
    bad = dict(defaults, crisis_runway_days=100, dsr_heavy=-1)
    errors = validate_thresholds(bad, defaults)
    assert any("negative" in e for e in errors)
    bad = dict(defaults, crisis_runway_days=100)        # crisis > short runway
    assert any("crisis_runway_days" in e for e in validate_thresholds(bad, defaults))
    assert validate_thresholds({"nope": 1}, defaults)


def test_every_catalog_problem_is_used_and_has_decisions():
    raised = {a.key for r in RULES for a in r.actions if isinstance(a, RaiseProblem)}
    assert raised == set(PROBLEMS)
    for key, entry in PROBLEMS.items():
        assert entry["severity"] in SEVERITY_RANK
        assert entry["decisions"], key
