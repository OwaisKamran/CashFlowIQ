"""UI tests using Streamlit's headless AppTest (no browser needed)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from knowledge_base.questions import QUESTION_BY_KEY, questions_in_step
from sample_cases import SAMPLE_CASES

APP = str(Path(__file__).resolve().parents[1] / "app.py")
QUICK = "views/quick_diagnosis.py"
LAHORE = SAMPLE_CASES["Lahore Spice Kitchen (Crisis)"]["inputs"]


def _app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    return at


def _widget(at, q, prefix):
    """Find the widget for a question, or None if it is not on screen."""
    key = f"{prefix}{q.key}"
    finder = {"text": at.text_input, "amount": at.text_input, "days": at.number_input,
              "percent": at.number_input, "yesno": at.radio, "checkbox": at.checkbox,
              "choice": at.selectbox if len(q.options) > 3 else at.radio}[q.kind]
    try:
        return finder(key=key)
    except KeyError:
        return None


def _set(widget, q, value):
    if q.kind == "amount":
        widget.set_value("" if value is None else f"{value:,.0f}")
    elif q.kind == "yesno":
        widget.set_value("Yes" if value else "No")
    elif q.kind == "checkbox":
        widget.set_value(bool(value))
    else:
        widget.set_value(value)


def _fill(at, questions, source, prefix):
    """Fill the questions that are on screen (repeat: answers can reveal new ones)."""
    for _ in range(3):
        for q in questions:
            w = _widget(at, q, prefix)
            if w is not None and q.key in source:
                _set(w, q, source[q.key])
        at.run()
        assert not at.exception


def _click(at, key):
    at.button(key=key).click().run()
    assert not at.exception


def _errors(at):
    return [m.value for m in at.markdown if "cf-field-error" in m.value]


# ---------------------------------------------------------------------------
# Consultation wizard
# ---------------------------------------------------------------------------
def _start(at):
    _click(at, "start_consult")
    assert at.session_state.consult_step == 1


def _complete_wizard(at, source):
    visited = []
    while at.session_state.consult_step <= 6:
        step = at.session_state.consult_step
        visited.append(step)
        _fill(at, questions_in_step(step), source, "w_")
        _click(at, "wiz_next")
        assert at.session_state.consult_step != step, f"stuck on step {step}: {_errors(at)}"
    return visited


def test_welcome_is_the_default_page():
    at = _app()
    assert any(b.key == "start_consult" for b in at.button)
    assert any("3 minutes" in m.value for m in at.markdown)


def test_full_wizard_run_gives_plain_report():
    at = _app()
    _start(at)
    visited = _complete_wizard(at, LAHORE)
    assert visited == [1, 2, 3, 4, 5, 6]
    assert at.session_state.consult_step == 7                   # review
    assert any("Review your answers" in m.value for m in at.markdown)
    _click(at, "get_diagnosis")
    result = at.session_state.consult_result
    assert result.status == "Crisis"
    page = " ".join(m.value for m in at.markdown)
    assert "Lahore Spice Kitchen is in CRISIS" in page
    assert "What you should do" in page and "Key figures" in page
    assert any(b.key == "new_consult" for b in at.button)
    assert any(b.key == "edit_answers" for b in at.button)


def _crisis_report(at):
    _start(at)
    at.session_state.wiz["answers"].update(LAHORE)
    at.session_state.wiz["step"] = 8                              # straight to the report
    at.run()
    assert not at.exception


def test_report_uses_plain_words_by_default():
    at = _app()
    _crisis_report(at)
    report = " ".join(m.value for m in at.markdown if "cf-actions" in m.value or "cf-item" in m.value)
    assert "Do this now" in report and "Very likely" in report
    assert "rule R" not in report and "rules R" not in report and "CF " not in report


def test_technical_details_toggle_shows_rules_and_cf():
    at = _app()
    _crisis_report(at)
    at.toggle(key="consult_tech").set_value(True).run()
    report = " ".join(m.value for m in at.markdown if "cf-actions" in m.value or "cf-item" in m.value)
    assert "rules R17" in report and "CF 0.95" in report and "Found by rule" in report


def test_health_score_visible_even_at_zero():
    at = _app()
    _crisis_report(at)
    assert at.session_state.consult_result.health_score == 0
    bar = next(m.value for m in at.markdown if "<div class='cf-score'>" in m.value)
    assert "class='marker' style='left:0" in bar and "out of 100" in bar


def test_empty_business_name_blocks_next():
    at = _app()
    _start(at)
    _click(at, "wiz_next")
    assert at.session_state.consult_step == 1
    assert any("Please enter your business name." in m for m in _errors(at))
    _fill(at, questions_in_step(1), {"business_name": "Test Traders"}, "w_")
    assert not any("business name" in m for m in _errors(at))   # error clears once fixed
    _click(at, "wiz_next")
    assert at.session_state.consult_step == 2


def test_cash_step_shows_error_for_each_missing_field():
    at = _app()
    _start(at)
    _fill(at, questions_in_step(1), {"business_name": "Test"}, "w_")
    _click(at, "wiz_next")
    _click(at, "wiz_next")                                       # step 2, nothing entered
    assert at.session_state.consult_step == 2
    text = " ".join(_errors(at))
    assert text.count("Please enter an amount") == 4             # cash, bank, sales, costs
    assert "profit margin" in text


def test_bad_amount_is_explained():
    at = _app()
    _start(at)
    _fill(at, questions_in_step(1), {"business_name": "Test"}, "w_")
    _click(at, "wiz_next")
    at.text_input(key="w_cash_in_hand").set_value("lots").run()
    _click(at, "wiz_next")
    assert any("Please enter a number" in m for m in _errors(at))


def test_amounts_get_thousand_separators():
    at = _app()
    _start(at)
    _fill(at, questions_in_step(1), {"business_name": "Test"}, "w_")
    _click(at, "wiz_next")
    at.text_input(key="w_bank_balance").set_value("1250000").run()
    assert at.text_input(key="w_bank_balance").value == "1,250,000"


def test_service_business_skips_stock_step():
    at = _app()
    _start(at)
    source = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"],
                  business_type="services")
    visited = _complete_wizard(at, source)
    assert 4 not in visited
    _click(at, "get_diagnosis")
    assert at.session_state.consult_result.sufficient


def test_debt_free_business_through_the_wizard():
    at = _app()
    _start(at)
    source = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"])
    for step in (1, 2, 3, 4):
        _fill(at, questions_in_step(step), source, "w_")
        _click(at, "wiz_next")
    assert at.session_state.consult_step == 5
    at.text_input(key="w_accounts_payable").set_value("").run()     # owes nothing ...
    at.text_input(key="w_short_term_loans").set_value("").run()
    at.text_input(key="w_other_current_liabilities").set_value("").run()
    _click(at, "wiz_next")
    assert at.session_state.consult_step == 5                       # ... blocked without the tick
    assert any("owe anything right now" in m for m in _errors(at))   # hint points to the tick
    at.checkbox(key="w_owes_nothing").check().run()
    assert _widget(at, QUESTION_BY_KEY["accounts_payable"], "w_") is None   # debt questions hidden
    _click(at, "wiz_next")
    assert at.session_state.consult_step == 6
    _click(at, "wiz_next")
    _click(at, "get_diagnosis")
    result = at.session_state.consult_result
    assert result.sufficient and result.status == "Healthy"
    assert any("No debt" in m.value for m in at.markdown)          # ratios explained, not N/A


def test_skip_notice_is_shown():
    at = _app()
    _start(at)
    source = dict(SAMPLE_CASES["Al-Noor General Store (Healthy)"]["inputs"],
                  business_type="services")
    for step in (1, 2, 3):
        _fill(at, questions_in_step(step), source, "w_")
        _click(at, "wiz_next")
    assert at.session_state.consult_step == 5
    assert any("service business" in m.value for m in at.markdown if "cf-skip" in m.value)


def test_hidden_follow_up_question_appears_when_needed():
    at = _app()
    _start(at)
    _fill(at, questions_in_step(1), {"business_name": "Test"}, "w_")
    _click(at, "wiz_next")
    _fill(at, questions_in_step(2), LAHORE, "w_")
    _click(at, "wiz_next")                                       # step 3
    assert _widget(at, QUESTION_BY_KEY["collection_days"], "w_") is None               # collection days hidden
    at.text_input(key="w_accounts_receivable").set_value("50,000").run()
    assert _widget(at, QUESTION_BY_KEY["collection_days"], "w_") is not None           # now asked


def test_back_keeps_answers_and_review_edit_returns_to_review():
    at = _app()
    _start(at)
    _fill(at, questions_in_step(1), {"business_name": "Back Test"}, "w_")
    _click(at, "wiz_next")
    _click(at, "wiz_back")
    assert at.session_state.consult_step == 1
    assert at.text_input(key="w_business_name").value == "Back Test"
    at.session_state.wiz["answers"].update(LAHORE)               # jump ahead to the review
    at.session_state.wiz["step"] = 7
    at.run()
    _click(at, "edit_step_2")
    assert at.session_state.consult_step == 2
    assert at.button(key="wiz_next").label == "Back to review"
    _click(at, "wiz_next")
    assert at.session_state.consult_step == 7


def test_why_popover_lists_rules():
    at = _app()
    _start(at)
    _fill(at, questions_in_step(1), {"business_name": "Test"}, "w_")
    _click(at, "wiz_next")
    text = " ".join(m.value for m in at.markdown)
    assert "R01" in text and "R82" in text                       # rules using cash in hand


# ---------------------------------------------------------------------------
# Quick Diagnosis
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(SAMPLE_CASES))
def test_quick_diagnosis_runs_each_sample(name):
    at = _app()
    at.switch_page(QUICK).run()
    at.selectbox(key="sample_choice").select(name).run()
    _click(at, "run_quick")
    expected = SAMPLE_CASES[name]["expected_status"]
    assert at.session_state.quick_result.status == expected
    assert any(expected.upper() in m.value for m in at.markdown)


def test_quick_diagnosis_requires_business_name():
    at = _app()
    at.switch_page(QUICK).run()
    at.selectbox(key="sample_choice").select("Hamza Textiles Wholesale (Watch)").run()
    at.text_input(key="q_business_name").set_value("").run()
    _click(at, "run_quick")
    assert at.session_state.quick_result is None
    assert any("Please enter your business name." in m for m in _errors(at))


def test_quick_diagnosis_blank_form_lists_missing_fields():
    at = _app()
    at.switch_page(QUICK).run()
    _click(at, "run_quick")
    assert at.session_state.quick_result is None
    text = " ".join(_errors(at))
    assert "business name" in text and "Please enter an amount" in text
    assert "at least one amount you owe" in text


# ---------------------------------------------------------------------------
@pytest.mark.parametrize("page", ["views/knowledge_base.py", "views/admin.py", "views/about.py"])
def test_other_pages_render(page):
    at = _app()
    at.switch_page(page).run()
    assert not at.exception
