"""Knowledge Acquisition page: edit, validate, download and upload thresholds."""
import json

import pandas as pd
import streamlit as st

from knowledge_base import validate_thresholds
from ui.components import e, icon, page_header


def apply(values: dict):
    st.session_state.thresholds = {k: float(v) for k, v in values.items()}
    st.session_state.quick_result = None     # clear results made with old thresholds


page_header("Knowledge Acquisition", "Tune the thresholds the rules use, without changing code.",
            f"{len(st.session_state.threshold_table)} thresholds", "tune")
st.caption("This page is for experts and the knowledge engineer, not for business owners.")
st.markdown("## Thresholds")
st.markdown("Knowledge acquisition is how expert knowledge enters the system. Here a domain "
            "expert can tune **every numeric threshold** the rules use, without changing code. "
            "The next diagnosis immediately reasons with the new values.")
st.markdown("<p class='cf-muted'>Streamlit Community Cloud does not keep files permanently, so "
            "changes apply to your current session only. Use <b>Download</b> to save your "
            "thresholds and <b>Upload</b> to restore them later.</p>", unsafe_allow_html=True)

defaults = st.session_state.threshold_defaults
current = st.session_state.thresholds
table = st.session_state.threshold_table

GROUP_ICONS = {"Ratio analysis": "balance", "Cash runway": "hourglass_bottom", "Receivables": "group",
               "Inventory": "inventory_2", "Payables": "local_shipping", "Debt": "account_balance",
               "Business type": "storefront", "Final status": "flag", "Certainty": "percent"}
groups = list(dict.fromkeys(meta["group"] for meta in table.values()))


def editor_key(group: str) -> str:
    return "threshold_editor_" + group.lower().replace(" ", "_")


new_values = {}
for group in groups:
    names = [n for n, meta in table.items() if meta["group"] == group]
    df = pd.DataFrame([{"Threshold": n, "Value": float(current[n]), "Default": float(defaults[n]),
                        "Description": table[n]["description"]} for n in names])
    with st.container(key=f"cfcard_thr_{editor_key(group)}"):
        st.markdown(f"<div class='cf-thr-head'><div class='cf-card-title'>{icon(GROUP_ICONS.get(group, 'tune'))}"
                    f"{e(group)}</div><span class='cf-muted'>{len(names)} thresholds</span></div>",
                    unsafe_allow_html=True)
        edited = st.data_editor(
            df, hide_index=True, width="stretch", key=editor_key(group),
            disabled=["Threshold", "Default", "Description"],
            column_config={
                "Value": st.column_config.NumberColumn(min_value=0.0, step=0.05, format="%.2f",
                                                       help="Edit this column"),
                "Default": st.column_config.NumberColumn(format="%.2f"),
                "Description": st.column_config.TextColumn(width="large"),
            })
        new_values.update(zip(edited["Threshold"], edited["Value"]))
    st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)


def clear_editors():
    for group in groups:
        st.session_state.pop(editor_key(group), None)


changed = {k: v for k, v in new_values.items() if v != defaults[k]}

c1, c2, c3 = st.columns(3)
if c1.button("Apply to this session", type="primary", width="stretch", icon=":material/check:"):
    errors = validate_thresholds(new_values, defaults)
    if errors:
        st.error("Not applied:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        apply(new_values)
        st.success(f"Applied. {len(changed)} threshold(s) differ from the defaults.")
if c2.button("Reset to defaults", width="stretch", icon=":material/restart_alt:"):
    apply(defaults)
    clear_editors()
    st.rerun()

export = {name: {**meta, "value": current[name]} for name, meta in table.items()}
c3.download_button("Download thresholds.json", json.dumps(export, indent=2),
                   file_name="thresholds.json", mime="application/json", width="stretch",
                   icon=":material/download:")

if changed:
    st.markdown("**Different from defaults:** " +
                ", ".join(f"`{k}` {defaults[k]:g} → {v:g}" for k, v in changed.items()))

st.markdown("#### Upload thresholds")
uploaded = st.file_uploader("Upload a thresholds.json file", type="json")
if uploaded is not None and st.button("Apply uploaded file", icon=":material/upload:"):
    try:
        raw = json.load(uploaded)
        # full {name: {value, ...}} or flat {name: value}
        values = {k: (v["value"] if isinstance(v, dict) else v) for k, v in raw.items()}
        errors = validate_thresholds(values, defaults)
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        errors = [f"Could not read the file: {exc}"]
    if errors:
        st.error("Upload rejected:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        apply(values)
        clear_editors()
        st.success("Uploaded thresholds applied to this session.")
        st.rerun()
