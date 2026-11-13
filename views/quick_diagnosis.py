"""Quick Diagnosis page: every question on one page, with sample businesses."""
import streamlit as st

from engine.consultation import resolve, validate_step
from engine.diagnosis import diagnose
from knowledge_base.questions import QUESTIONS, STEPS, questions_in_step
from sample_cases import SAMPLE_CASES
from ui import fields
from engine.explanation import plain_summary
from ui.components import MUTED, STATUS_COLOR, e, section
from ui.report import render_report

TH = st.session_state.thresholds
PREFIX = "q_"
BLANK = "Blank form"

st.session_state.setdefault("quick_answers", {})
st.session_state.setdefault("quick_errors", {})
st.session_state.setdefault("quick_step_errors", {})
st.session_state.setdefault("quick_result", None)
A = st.session_state.quick_answers


def _load_sample():
    choice = st.session_state.sample_choice
    data = {} if choice == BLANK else SAMPLE_CASES[choice]["inputs"]
    A.clear()
    A.update(data)
    for q in QUESTIONS:
        blank = None if q.kind == "yesno" else q.default      # no pre-selected answer
        st.session_state[fields.widget_key(PREFIX, q)] = fields.to_widget(q, data.get(q.key, blank))
    st.session_state.quick_result = None
    st.session_state.quick_errors, st.session_state.quick_step_errors = {}, {}


def _run():
    parse_errors = {}
    for q in QUESTIONS:
        if fields.widget_key(PREFIX, q) in st.session_state:
            value, error = fields.read(q, PREFIX)
            if error:
                parse_errors[q.key] = error
            else:
                A[q.key] = value
    errors, step_errors = dict(parse_errors), {}
    for step in STEPS:
        field_errors, step_error = validate_step(step, A, TH)
        errors.update(field_errors)
        if step_error:
            step_errors[step] = step_error
    st.session_state.quick_errors, st.session_state.quick_step_errors = errors, step_errors
    st.session_state.quick_result = None if (errors or step_errors) else \
        diagnose(resolve(A, TH).facts, TH)


# page
st.markdown("<div class='cf-eyebrow'>Quick diagnosis</div>", unsafe_allow_html=True)
st.title("Quick diagnosis")
st.markdown("<p class='cf-muted'>All questions on one page. Pick a sample business to see a "
            "diagnosis instantly, or type your own figures.</p>", unsafe_allow_html=True)

st.selectbox("Sample business", [BLANK] + list(SAMPLE_CASES), key="sample_choice",
             on_change=_load_sample)
if st.session_state.get("sample_choice") in SAMPLE_CASES:
    case = SAMPLE_CASES[st.session_state.sample_choice]
    st.caption(f"{case['story']} Expected status: {case['expected_status']}.")

# sync typed values so skipped questions update
for _q in QUESTIONS:
    if fields.widget_key(PREFIX, _q) in st.session_state:
        _value, _error = fields.read(_q, PREFIX)
        if _error is None:
            A[_q.key] = _value

# report first, so it is visible after Run diagnosis
if st.session_state.quick_result is not None:
    render_report(st.session_state.quick_result, TH, key="quick")
    st.markdown("<br>", unsafe_allow_html=True)
    row = st.container(horizontal=True, gap="small")
    if row.button("Start a guided consultation", key="to_consult"):
        st.switch_page("views/consultation.py")
    st.markdown("<p class='cf-muted' style='margin-top:1rem'>Your answers are below. Change any "
                "of them and press <b>Run diagnosis</b> again.</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top:1rem'>Your answers</h2>", unsafe_allow_html=True)

errors = st.session_state.quick_errors
for step, (title, intro) in STEPS.items():
    section(f"{step}. {title}")
    shown = resolve(A, TH).shown
    qs = questions_in_step(step)
    if not any(q.key in shown for q in qs):
        fields.skipped_line(qs[0])
        continue
    cols = st.columns(2, gap="large")
    for i, q in enumerate([q for q in qs if q.key in shown]):
        with cols[i % 2]:
            fields.render(q, PREFIX, A, error=errors.get(q.key))
    for q in qs:
        if q.key not in shown:
            fields.skipped_line(q)
    if step in st.session_state.quick_step_errors:
        st.markdown(f"<div class='cf-field-error'>{e(st.session_state.quick_step_errors[step])}"
                    "</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if errors or st.session_state.quick_step_errors:
    st.markdown("<div class='cf-field-error'>Some answers are missing - see the messages in red "
                "above.</div>", unsafe_allow_html=True)
st.button("Run diagnosis", type="primary", key="run_quick", on_click=_run)
if st.session_state.quick_result is not None:          # short status by the button
    _r = st.session_state.quick_result
    st.markdown(f"<div class='cf-status' style='border-color:{STATUS_COLOR.get(_r.status, MUTED)}'>"
                f"<b style='color:{STATUS_COLOR.get(_r.status, MUTED)}'>{e(_r.status)}</b> - "
                f"{e(plain_summary(_r)[0])} The full report is at the top of this page.</div>",
                unsafe_allow_html=True)
