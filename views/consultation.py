"""
Consultation page - a step-by-step wizard (the default page).

  Welcome -> 1 Your business -> 2 Cash -> 3 Customers -> 4 Stock -> 5 Suppliers & loans
          -> 6 Warning signs -> Review -> Diagnosis report

* "Next" is blocked until the step's required answers are filled in; errors are
  shown under the field in plain words.
* Questions (and whole steps) are skipped by their ask_if conditions, with a
  short line explaining why.
* Each question has a small "Why?" popover generated from the rule base.
"""
import streamlit as st

from engine.consultation import (
    REVIEW_STEP, because, next_step, previous_step, resolve, step_is_skipped, step_skip_reason, validate_step,
)
from engine.diagnosis import diagnose
from knowledge_base.questions import STEPS, questions_in_step
from ui import fields
from ui.components import e, stepper
from ui.report import render_report

TH = st.session_state.thresholds
PREFIX = "w_"
RESULT_STEP = REVIEW_STEP + 1


def _new_state():
    return {"step": 0, "answers": {}, "errors": {}, "step_error": None, "notice": None,
            "back_to_review": False}


st.session_state.setdefault("wiz", _new_state())
W = st.session_state.wiz


# ----------------------------------------------------------------------
# Callbacks
# ----------------------------------------------------------------------
def _read_step(step):
    """Copy the current widget values of a step into the answers; return parse errors."""
    parse_errors = {}
    for q in questions_in_step(step):
        if fields.widget_key(PREFIX, q) in st.session_state:
            value, error = fields.read(q, PREFIX)
            if error:
                parse_errors[q.key] = error
            else:
                W["answers"][q.key] = value
    return parse_errors


def go(step, notice=None):
    W["step"], W["notice"] = step, notice
    W["errors"], W["step_error"] = {}, None


def start():
    go(1)


def on_next():
    step = W["step"]
    parse_errors = _read_step(step)
    errors, step_error = validate_step(step, W["answers"], TH)
    errors.update(parse_errors)
    if errors or step_error:
        W["errors"], W["step_error"] = errors, step_error
        return
    if W["back_to_review"]:
        W["back_to_review"] = False
        go(REVIEW_STEP)
        return
    target, passed = next_step(step, W["answers"], TH)
    notice = " ".join(f"Step {s} – {STEPS[s][0]} was skipped because {because(step_skip_reason(s))}"
                      for s in passed)
    go(target, notice or None)


def on_back():
    if W["step"] in STEPS:
        _read_step(W["step"])              # keep what was typed, even if incomplete
    W["back_to_review"] = False
    go(previous_step(W["step"], W["answers"], TH))


def edit_step(step):
    W["back_to_review"] = True
    go(step)


def get_diagnosis():
    go(RESULT_STEP)


def restart():
    for k in [k for k in st.session_state if str(k).startswith(PREFIX)]:
        del st.session_state[k]
    W.clear()
    W.update(_new_state())


# ----------------------------------------------------------------------
# Screens
# ----------------------------------------------------------------------
def welcome():
    st.markdown("<div class='cf-eyebrow'>Consultation</div>", unsafe_allow_html=True)
    st.title("Cash flow check-up for your business")
    st.markdown(
        "<div class='cf-summary' style='max-width:640px'>"
        "<p>Answer a few simple questions about your cash, customers, stock and loans.</p>"
        "<p>It takes about <b>3 minutes</b>. Rough figures from a normal month are fine.</p>"
        "<p>You will get a <b>health status</b>, the <b>main problems</b> and "
        "<b>what to do next</b> - with the reasoning explained.</p></div>",
        unsafe_allow_html=True)
    st.button("Start", type="primary", key="start_consult", on_click=start)
    st.markdown("<p class='cf-muted' style='margin-top:1.5rem;font-size:.85rem'>All amounts are in "
                "Pakistani rupees (Rs). Nothing you enter is saved after you close the page.</p>",
                unsafe_allow_html=True)


def skipped_steps():
    return {s for s in STEPS if step_is_skipped(s, W["answers"], TH)}


def step_screen(step):
    title, intro = STEPS[step]
    st.markdown(stepper(step, STEPS, skipped_steps()), unsafe_allow_html=True)
    if W["notice"]:
        st.markdown(f"<div class='cf-skip'>{e(W['notice'])}</div>", unsafe_allow_html=True)
    st.markdown(f"## {title}")
    st.markdown(f"<p class='cf-muted'>{e(intro)}</p>", unsafe_allow_html=True)

    main, tip = st.columns([3, 1.3], gap="large")
    with main:
        parse_errors = _read_step(step)        # so ask_if reacts to what was just typed
        if W["errors"] or W["step_error"]:     # after a failed "Next", re-check live
            W["errors"], W["step_error"] = validate_step(step, W["answers"], TH)
            W["errors"].update(parse_errors)
        shown = resolve(W["answers"], TH).shown
        for q in questions_in_step(step):
            if q.key in shown:
                fields.render(q, PREFIX, W["answers"], error=W["errors"].get(q.key))
            else:
                fields.skipped_line(q)
        if W["step_error"]:
            st.markdown(f"<div class='cf-field-error' style='margin-top:.5rem'>"
                        f"{e(W['step_error'])}</div>", unsafe_allow_html=True)
        if W["errors"] or W["step_error"]:
            st.markdown("<div class='cf-field-error'>Please fix the answers marked in red to "
                        "continue.</div>", unsafe_allow_html=True)
        row = st.container(horizontal=True, gap="small")
        row.button("Back", key="wiz_back", on_click=on_back)
        row.button("Back to review" if W["back_to_review"] else "Next", type="primary",
                   key="wiz_next", on_click=on_next)
    with tip:
        st.markdown(
            "<div class='cf-tip'><b>Tips</b><br>Rough figures are fine.<br>"
            "Type amounts like <i>250,000</i>.<br>Press <b>Enter</b> to go to the next box.<br>"
            "Leave a box blank if it does not apply - "
            "unless it says it is needed.<br>Click <b>Why are you asking?</b> under a question "
            "to see which rules use it."
            "</div>", unsafe_allow_html=True)


def review_screen():
    st.markdown(stepper(REVIEW_STEP, STEPS, skipped_steps(), review=True), unsafe_allow_html=True)
    st.markdown("## Review your answers")
    st.markdown("<p class='cf-muted'>Check everything below. Use <b>Edit</b> to change a step, "
                "then press <b>Get diagnosis</b>.</p>", unsafe_allow_html=True)
    res = resolve(W["answers"], TH)
    for step, (title, _intro) in STEPS.items():
        head = st.container(horizontal=True, vertical_alignment="center")
        head.markdown(f"**{step}. {title}**", width="content")
        head.button("Edit", key=f"edit_step_{step}", type="tertiary", on_click=edit_step,
                    args=(step,))
        if step_is_skipped(step, W["answers"], TH):
            st.markdown(f"<div class='cf-skip'>Skipped: {e(step_skip_reason(step))}</div>",
                        unsafe_allow_html=True)
            continue
        rows = "".join(
            f"<tr><td>{e(q.label)}</td><td class='num'>"
            f"{e(fields.show_answer(q, res.facts.get(q.key)))}</td></tr>"
            for q in questions_in_step(step) if q.key in res.shown)
        st.markdown(f"<table class='cf-table' style='margin-bottom:1rem'>{rows}</table>",
                    unsafe_allow_html=True)
    row = st.container(horizontal=True, gap="small")
    row.button("Back", key="review_back", on_click=on_back)
    row.button("Get diagnosis", type="primary", key="get_diagnosis", on_click=get_diagnosis)


def result_screen():
    facts = dict(resolve(W["answers"], TH).facts)
    result = diagnose(facts, TH)
    st.session_state.consult_result = result
    render_report(result, TH, key="consult")
    st.markdown("<br>", unsafe_allow_html=True)
    row = st.container(horizontal=True, gap="small")
    row.button("Start new consultation", type="primary", key="new_consult", on_click=restart)
    row.button("Edit answers", key="edit_answers", on_click=go, args=(REVIEW_STEP,))


# ----------------------------------------------------------------------
step = W["step"]
st.session_state.consult_step = step                    # used by the UI tests
if step == 0:
    welcome()
elif step in STEPS:
    step_screen(step)
elif step == REVIEW_STEP:
    review_screen()
else:
    result_screen()
