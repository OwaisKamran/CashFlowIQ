"""Knowledge Base page: all rules, the problem catalog and rule counts."""
from collections import Counter

import pandas as pd
import streamlit as st

from engine.explanation import problem_catalog_rows
from knowledge_base.problems import PROBLEMS
from knowledge_base.rule_model import RaiseProblem
from knowledge_base.rules import RULES, RULE_GROUPS
from ui.components import e

KIND_LABELS = {
    "DATA CHECK": "Data check (sufficiency / sanity)",
    "COMPUTE": "Compute (derive a ratio)",
    "DECISION": "Decision (diagnose / recommend)",
    "CLASSIFY": "Classify (band / strength)",
    "STATUS": "Status (final verdict)",
}


def then_text(rule) -> str:
    """THEN column, showing problem titles instead of catalog keys."""
    parts = []
    for action in rule.actions:
        if isinstance(action, RaiseProblem):
            entry = PROBLEMS[action.key]
            parts.append(f"PROBLEM: {entry['title']} [{entry['severity']}]")
        else:
            parts.append(action.describe())
    return "  ;  ".join(parts)


st.caption("This page is for experts and the knowledge engineer, not for business owners.")
st.markdown("<div class='cf-eyebrow'>Knowledge base</div>", unsafe_allow_html=True)
st.title("Rules and knowledge")
st.markdown("<p class='cf-muted'>All expert knowledge is stored as data in "
            "<code>knowledge_base/rules.py</code>, separate from the inference engine. "
            "Numeric limits come from <code>thresholds.json</code>.</p>", unsafe_allow_html=True)

kinds = Counter(r.kind for r in RULES)
figures = [
    ("Total rules", len(RULES)),
    ("Compute rules", kinds["COMPUTE"]),
    ("Decision rules", kinds["DECISION"]),
    ("Classify & status", kinds["CLASSIFY"] + kinds["STATUS"]),
    ("Data-check rules", kinds["DATA CHECK"]),
]
st.markdown("<div class='cf-figures'>" + "".join(
    f"<div><div class='v'>{v}</div><div class='l'>{e(label)}</div></div>" for label, v in figures)
    + "</div>", unsafe_allow_html=True)

tab_rules, tab_problems, tab_groups = st.tabs(["Rules", "Problem catalog", "Rules per group"])

with tab_rules:
    f1, f2, f3 = st.columns(3)
    groups = f1.multiselect("Group", RULE_GROUPS, placeholder="All groups")
    types = f2.multiselect("Type", list(KIND_LABELS), placeholder="All types",
                           format_func=lambda k: KIND_LABELS[k])
    search = f3.text_input("Search", placeholder="e.g. runway, supplier, R17")

    df = pd.DataFrame([{"ID": r.id, "Group": r.group, "Type": r.kind, "IF": r.if_text(),
                        "THEN": then_text(r), "CF": r.cf, "Priority": r.priority,
                        "Description": r.description} for r in RULES])
    if groups:
        df = df[df["Group"].isin(groups)]
    if types:
        df = df[df["Type"].isin(types)]
    if search:
        mask = df.apply(lambda row: search.lower() in " ".join(map(str, row.values)).lower(), axis=1)
        df = df[mask]

    st.caption(f"Showing {len(df)} of {len(RULES)} rules")
    st.dataframe(df, hide_index=True, width="stretch", height=520,
                 column_config={
                     "IF": st.column_config.TextColumn(width="large"),
                     "THEN": st.column_config.TextColumn(width="large"),
                     "CF": st.column_config.NumberColumn(format="%.2f"),
                 })

    st.markdown("##### Inspect a rule")
    by_id = {r.id: r for r in RULES}
    pick = st.selectbox("Rule", list(by_id), format_func=lambda i: f"{i} - {by_id[i].description}",
                        label_visibility="collapsed")
    rule = by_id[pick]
    lines = [f"RULE {rule.id}   [{rule.group}]   CF = {rule.cf:.2f}   priority = {rule.priority}",
             f"# {rule.description}", "IF"]
    lines += [f"    {'AND ' if i else ''}{c.describe()}" for i, c in enumerate(rule.conditions)]
    lines += ["THEN"] + [f"    {part}" for part in then_text(rule).split("  ;  ")]
    st.code("\n".join(lines), language=None)

with tab_problems:
    st.caption(f"{len(PROBLEMS)} problems. Every diagnosis rule refers to this catalog for the "
               "problem's severity, description and recommended decisions.")
    st.dataframe(pd.DataFrame(problem_catalog_rows()), hide_index=True, width="stretch",
                 height=520)

with tab_groups:
    counts = pd.DataFrame({"Group": RULE_GROUPS,
                           "Rules": [sum(r.group == g for r in RULES) for g in RULE_GROUPS]})
    st.dataframe(counts, hide_index=True, width="stretch",
                 column_config={"Rules": st.column_config.ProgressColumn(
                     "Rules", format="%d", min_value=0, max_value=int(counts["Rules"].max()))})
