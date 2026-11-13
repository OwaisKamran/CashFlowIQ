"""
Knowledge Acquisition page - the domain expert tunes the knowledge
(thresholds) without touching code.

Streamlit Community Cloud's file system is NOT permanent, so edits apply to the
current browser session only. Use Download / Upload to keep a copy.
"""
import json

import pandas as pd
import streamlit as st

from knowledge_base import validate_thresholds


def apply(values: dict):
    st.session_state.thresholds = {k: float(v) for k, v in values.items()}
    st.session_state.quick_result = None     # old diagnosis used old knowledge


st.caption("This page is for experts and the knowledge engineer, not for business owners.")
st.markdown("<div class='cf-eyebrow'>Knowledge acquisition</div>", unsafe_allow_html=True)
st.title("Thresholds")
st.markdown("Knowledge acquisition is how expert knowledge enters the system. Here a domain "
            "expert can tune **every numeric threshold** the rules use, without changing code. "
            "The next diagnosis immediately reasons with the new values.")
st.markdown("<p class='cf-muted'>Streamlit Community Cloud does not keep files permanently, so "
            "changes apply to your current session only. Use <b>Download</b> to save your "
            "thresholds and <b>Upload</b> to restore them later.</p>", unsafe_allow_html=True)

defaults = st.session_state.threshold_defaults
current = st.session_state.thresholds
table = st.session_state.threshold_table

df = pd.DataFrame([{
    "Threshold": name, "Group": meta["group"], "Value": float(current[name]),
    "Default": float(defaults[name]), "Description": meta["description"],
} for name, meta in table.items()])

edited = st.data_editor(
    df, hide_index=True, width="stretch", height=520, key="threshold_editor",
    disabled=["Threshold", "Group", "Default", "Description"],
    column_config={
        "Value": st.column_config.NumberColumn(min_value=0.0, step=0.05, format="%.2f",
                                               help="Edit this column"),
        "Default": st.column_config.NumberColumn(format="%.2f"),
        "Description": st.column_config.TextColumn(width="large"),
    })

new_values = dict(zip(edited["Threshold"], edited["Value"]))
changed = {k: v for k, v in new_values.items() if v != defaults[k]}

c1, c2, c3 = st.columns(3)
if c1.button("Apply to this session", type="primary", width="stretch"):
    errors = validate_thresholds(new_values, defaults)
    if errors:
        st.error("Not applied:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        apply(new_values)
        st.success(f"Applied. {len(changed)} threshold(s) differ from the defaults.")
if c2.button("Reset to defaults", width="stretch"):
    apply(defaults)
    st.session_state.pop("threshold_editor", None)
    st.rerun()

export = {name: {**meta, "value": current[name]} for name, meta in table.items()}
c3.download_button("Download thresholds.json", json.dumps(export, indent=2),
                   file_name="thresholds.json", mime="application/json", width="stretch")

if changed:
    st.markdown("**Different from defaults:** " +
                ", ".join(f"`{k}` {defaults[k]:g} → {v:g}" for k, v in changed.items()))

st.markdown("##### Upload thresholds")
uploaded = st.file_uploader("Upload a thresholds.json file", type="json")
if uploaded is not None and st.button("Apply uploaded file"):
    try:
        raw = json.load(uploaded)
        # Accept the full format {name: {value, ...}} or a flat {name: value}
        values = {k: (v["value"] if isinstance(v, dict) else v) for k, v in raw.items()}
        errors = validate_thresholds(values, defaults)
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        errors = [f"Could not read the file: {exc}"]
    if errors:
        st.error("Upload rejected:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        apply(values)
        st.session_state.pop("threshold_editor", None)
        st.success("Uploaded thresholds applied to this session.")
        st.rerun()
