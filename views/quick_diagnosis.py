"""Quick Diagnosis page: every question on one page, with sample businesses."""
import streamlit as st

from engine.consultation import resolve, validate_step
from engine.diagnosis import diagnose
from knowledge_base.questions import BUSINESS_TYPE_LABELS, QUESTIONS, STEPS, questions_in_step
from sample_cases import SAMPLE_CASES
from ui import fields
from engine.explanation import plain_summary
from ui.components import STATUS, e, page_header, pill
from ui.report import render_report

TH = st.session_state.thresholds
PREFIX = "q_"

st.session_state.setdefault("quick_answers", {})
st.session_state.setdefault("quick_errors", {})
st.session_state.setdefault("quick_step_errors", {})
st.session_state.setdefault("quick_result", None)
st.session_state.setdefault("quick_sample", None)
A = st.session_state.quick_answers


def _load_sample(choice=None):
    """Fill the form from a sample business (None = clear the form)."""
    st.session_state.quick_sample = choice
    data = {} if choice is None else SAMPLE_CASES[choice]["inputs"]
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
page_header("Quick Diagnosis", "All questions on one page. Pick a sample business to see a "
            "diagnosis instantly, or type your own figures.", f"{len(SAMPLE_CASES)} sample businesses",
            "storefront")

# sample businesses as cards
cols = st.columns(len(SAMPLE_CASES), gap="small")
for i, (name, case) in enumerate(SAMPLE_CASES.items()):
    colour, soft = STATUS[case["expected_status"]]
    with cols[i], st.container(key=f"cfsample_{i}"):
        st.markdown(f"<div class='cf-sample'><div class='strip' style='background:{colour}'></div>"
                    f"<div class='n'>{e(case['inputs']['business_name'])}</div>"
                    f"<div class='ty'>{e(BUSINESS_TYPE_LABELS[case['inputs']['business_type']])}</div>"
                    f"{pill(case['expected_status'], colour, soft, True)}</div>", unsafe_allow_html=True)
        st.button("Load", key=f"load_{i}", on_click=_load_sample, args=(name,),
                  icon=":material/download:", width="stretch")
loaded = st.session_state.quick_sample
note = st.container(horizontal=True, vertical_alignment="center")
if loaded in SAMPLE_CASES:
    case = SAMPLE_CASES[loaded]
    note.caption(f"{case['story']} Expected status: {case['expected_status']}.")
note.button("Clear form", key="clear_form", type="tertiary", on_click=_load_sample,
            icon=":material/restart_alt:")

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
    if row.button("Start a guided consultation", key="to_consult", icon=":material/assignment:"):
        st.switch_page("views/consultation.py")
    st.markdown("<p class='cf-muted' style='margin-top:1rem'>Your answers are below. Change any "
                "of them and press <b>Run diagnosis</b> again.</p>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top:1rem'>Your answers</h2>", unsafe_allow_html=True)

errors = st.session_state.quick_errors
step_errors = st.session_state.quick_step_errors
shown = resolve(A, TH).shown
labels = []
for step, (title, _intro) in STEPS.items():
    bad = step in step_errors or any(q.key in errors for q in questions_in_step(step))
    labels.append(f"{':material/error: ' if bad else ''}{step}. {title}")
for tab, (step, (title, intro)) in zip(st.tabs(labels), STEPS.items()):
    with tab, st.container(key=f"cfcard_q{step}"):
        st.markdown(f"<p class='cf-muted'>{e(intro)}</p>", unsafe_allow_html=True)
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
        if step in step_errors:
            st.markdown(f"<div class='cf-field-error'>{e(step_errors[step])}</div>",
                        unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if errors or st.session_state.quick_step_errors:
    st.markdown("<div class='cf-field-error'>Some answers are missing - see the messages in red "
                "above.</div>", unsafe_allow_html=True)
st.button("Run diagnosis", type="primary", key="run_quick", on_click=_run,
          icon=":material/play_arrow:")
if st.session_state.quick_result is not None:          # short status by the button
    _r = st.session_state.quick_result
    _c, _soft = STATUS.get(_r.status, STATUS["Unknown"])
    st.markdown(f"<div class='cf-status' style='display:block;border-color:{_c};background:{_soft}'>"
                f"<b style='color:{_c}'>{e(_r.status)}</b> - "
                f"{e(plain_summary(_r)[0])} The full report is at the top of this page.</div>",
                unsafe_allow_html=True)
