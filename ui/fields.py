"""
fields.py - Renders one Question as a Streamlit input, shared by both pages.

* Amounts are typed as text so they can show thousand separators
  ("1,250,000"); they are parsed with questions.parse_amount().
* Each field has a tooltip with a hint, an example value inside the empty box,
  a plain-words error underneath, and a small "Why?" popover generated from
  the rule base.
* Values are mirrored into a plain dict (`store`) because Streamlit forgets
  widget values when a widget is not on screen (e.g. on another wizard step).
"""
import streamlit as st

from engine.consultation import why_asking
from knowledge_base.questions import (
    BUSINESS_TYPE_LABELS, SEASON_LABELS, YES_NO_ANSWERS, parse_amount,
)
from knowledge_base.rules import RULES
from ui.components import e

CHOICE_LABELS = {"business_type": BUSINESS_TYPE_LABELS, "season": SEASON_LABELS}


def widget_key(prefix, q):
    return f"{prefix}{q.key}"


def to_widget(q, value):
    """Stored (parsed) value -> what the widget holds."""
    if q.kind == "amount":
        return "" if value is None else f"{value:,.0f}"
    if q.kind == "yesno":                                  # None = nothing selected yet
        return next((label for label, v in YES_NO_ANSWERS.items() if v == value and
                     type(v) is type(value)), None)
    if q.kind == "checkbox":
        return bool(value)
    if q.kind == "choice":
        return value if value in q.options else q.default
    if q.kind == "text":
        return value or ""
    return None if value is None else float(value)       # days / percent


def read(q, prefix):
    """Widget value -> (parsed value, parse error or None)."""
    raw = st.session_state.get(widget_key(prefix, q))
    if q.kind == "amount":
        return parse_amount(raw)
    if q.kind == "yesno":
        return YES_NO_ANSWERS.get(raw), None               # None = not answered
    if q.kind == "checkbox":
        return bool(raw), None
    if q.kind == "text":
        return (raw or "").strip(), None
    return raw, None


def ensure_widget(q, prefix, store):
    key = widget_key(prefix, q)
    if key not in st.session_state:
        st.session_state[key] = to_widget(q, store.get(q.key, q.default if q.kind == "checkbox" else None))


def _format_amount(key):
    """on_change: show the typed amount with thousand separators."""
    value, error = parse_amount(st.session_state.get(key))
    if value is not None and error is None:
        st.session_state[key] = f"{value:,.0f}"


def why_text(q) -> str:
    why = why_asking(q, RULES)
    if q.key == "business_name":
        return "Used only as the title of your report - it does not affect the diagnosis."
    lines = [f"{why['ask_reason']} This answer is used by these rules:"]
    lines += [f"- **{rid}** {desc}" for rid, _group, desc in why["direct"]]
    if why["indirect"]:
        lines.append(f"\nIt also feeds {len(why['indirect'])} more rules through calculated "
                     "figures such as ratios.")
    return "\n".join(lines)


def render(q, prefix, store, error=None, why=True):
    """Draw the input for one question and copy its value into `store`."""
    ensure_widget(q, prefix, store)
    key = widget_key(prefix, q)
    hint = q.help
    with st.container():
        if q.kind == "text":
            st.text_input(q.text, key=key, placeholder=q.example, help=hint, max_chars=80)
        elif q.kind == "amount":
            st.text_input(q.text, key=key, placeholder=q.example, help=hint,
                          on_change=_format_amount, args=(key,))
        elif q.kind in ("days", "percent"):
            st.number_input(q.text, key=key, min_value=float(q.min), max_value=float(q.max),
                            step=1.0, format="%.0f" if q.kind == "days" else "%.1f",
                            placeholder=q.example, help=hint)
        elif q.kind == "choice":
            labels = CHOICE_LABELS.get(q.key, {})
            if len(q.options) <= 3:
                st.radio(q.text, q.options, key=key, horizontal=True, help=hint,
                         format_func=lambda o: labels.get(o, o))
            else:
                st.selectbox(q.text, q.options, key=key, help=hint,
                             format_func=lambda o: labels.get(o, o))
        elif q.kind == "yesno":
            st.radio(q.text, list(YES_NO_ANSWERS), index=None, key=key, horizontal=True,
                     help=hint or None)
        elif q.kind == "checkbox":
            st.checkbox(q.text, key=key, help=hint or None)
        if error:                                     # error directly under the field
            st.markdown(f"<div class='cf-field-error'>{e(error)}</div>", unsafe_allow_html=True)
        if why:                                       # small, unobtrusive "Why?" link
            with st.popover("Why are you asking?", width="content"):
                st.markdown(why_text(q))

    value, parse_error = read(q, prefix)
    if parse_error is None:
        store[q.key] = value
    return parse_error


def skipped_line(q):
    st.markdown(f"<div class='cf-skip'>{e(q.text)} — {e(q.skip_text)}</div>",
                unsafe_allow_html=True)


def show_answer(q, value) -> str:
    """Formatted answer for the review table."""
    if q.kind == "choice":
        return CHOICE_LABELS.get(q.key, {}).get(value, str(value))
    if q.kind == "yesno":
        return to_widget(q, value) or "-"
    if q.kind == "checkbox":
        return "Yes" if value else "No"
    if value is None or value == "":
        return "-"
    if q.kind == "amount":
        return f"Rs {value:,.0f}"
    if q.kind == "days":
        return f"{value:,.0f} days"
    if q.kind == "percent":
        return f"{value:g}%"
    return str(value)
