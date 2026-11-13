"""Each demo business must reach its expected status with default thresholds."""
import pytest

from engine.diagnosis import diagnose
from knowledge_base.questions import validate_inputs
from sample_cases import SAMPLE_CASES


@pytest.mark.parametrize("name", list(SAMPLE_CASES))
def test_sample_case_status(name):
    case = SAMPLE_CASES[name]
    assert validate_inputs(case["inputs"]) == []          # sample data is valid
    result = diagnose(case["inputs"])
    assert result.status == case["expected_status"], (
        f"{name}: got {result.status} (score {result.health_score})")


def test_all_four_statuses_are_demonstrated():
    statuses = {c["expected_status"] for c in SAMPLE_CASES.values()}
    assert statuses == {"Healthy", "Watch", "Risky", "Crisis"}


@pytest.mark.parametrize("name", list(SAMPLE_CASES))
def test_decisions_are_ranked_and_explained(name):
    result = diagnose(SAMPLE_CASES[name]["inputs"])
    assert result.decisions, "every case should recommend at least one decision"
    assert [d["rank"] for d in result.decisions] == list(range(1, len(result.decisions) + 1))
    assert all(d["reason"] for d in result.decisions)
