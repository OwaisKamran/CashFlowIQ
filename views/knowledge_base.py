"""Knowledge Base page: all rules, the problem catalog and rule counts."""
from collections import Counter

import streamlit as st

from engine.explanation import problem_catalog_rows
from knowledge_base.problems import PROBLEMS
from knowledge_base.rule_model import RaiseProblem
from knowledge_base.rules import RULES, RULE_GROUPS
from ui.components import SEVERITY, e, icon, page_header, pill

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


def html_table(header, rows) -> str:
    """Scrollable table with a sticky navy header row."""
    head = "".join(f"<th class='{c}'>{e(h)}</th>" for h, c in header)
    body = "".join("<tr>" + "".join(f"<td class='{c}'>{v}</td>" for v, (_h, c) in zip(r, header))
                   + "</tr>" for r in rows)
    return (f"<div class='cf-scroll'><table class='cf-table'><thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table></div>")


page_header("Knowledge Base", "Every rule, the problem catalog and rule counts.",
            f"{len(RULES)} rules · {len(RULE_GROUPS)} groups", "menu_book")
st.caption("This page is for experts and the knowledge engineer, not for business owners.")
st.markdown("## Rules and knowledge")
st.markdown("<p class='cf-muted'>All expert knowledge is stored as data in "
            "<code>knowledge_base/rules.py</code>, separate from the inference engine. "
            "Numeric limits come from <code>thresholds.json</code>.</p>", unsafe_allow_html=True)

# stat tiles
kinds = Counter(r.kind for r in RULES)
counts = {g: sum(r.group == g for r in RULES) for g in RULE_GROUPS}
stats = [("rule_settings", len(RULES), "Total rules"), ("calculate", kinds["COMPUTE"], "Compute rules"),
         ("fact_check", kinds["DECISION"], "Decision rules"), ("category", len(RULE_GROUPS), "Rule groups")]
st.markdown("<div class='cf-stats'>" + "".join(
    f"<div class='cf-stat'><div class='i'>{icon(i)}</div><div><div class='v'>{v}</div>"
    f"<div class='l'>{e(label)}</div></div></div>" for i, v, label in stats) + "</div>",
    unsafe_allow_html=True)

tab_rules, tab_problems, tab_groups = st.tabs([":material/list: Rules", ":material/report: Problem catalog",
                                               ":material/bar_chart: Rules per group"])

with tab_rules:                                       # filters + rules table
    groups = st.pills("Group", RULE_GROUPS, selection_mode="multi", key="kb_groups",
                      format_func=lambda g: f"{g} · {counts[g]}")
    f2, f3 = st.columns(2)
    types = f2.multiselect("Type", list(KIND_LABELS), placeholder="All types",
                           format_func=lambda k: KIND_LABELS[k])
    search = f3.text_input("Search", placeholder="e.g. runway, supplier, R17")

    rules = [r for r in RULES if (not groups or r.group in groups) and (not types or r.kind in types)]
    if search:
        q = search.lower()
        rules = [r for r in rules if q in " ".join(map(str, (r.id, r.group, r.kind, r.if_text(),
                                                               then_text(r), r.description))).lower()]
    st.caption(f"Showing {len(rules)} of {len(RULES)} rules")
    header = [("Rule", ""), ("Group", ""), ("Type", ""), ("IF", ""), ("THEN", ""), ("CF", "num"),
              ("Priority", "num")]
    rows = [(f"<b>{r.id}</b><span class='sub'>{e(r.description)}</span>", e(r.group), e(r.kind),
             e(r.if_text()), e(then_text(r)), f"{r.cf:.2f}", r.priority) for r in rules]
    st.markdown(html_table(header, rows), unsafe_allow_html=True)

    st.markdown("#### Inspect a rule")
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
    rows = [(f"<code>{e(r['Key'])}</code>", e(r["Problem"]), pill(r["Severity"], *SEVERITY[r["Severity"]]),
             e(r["Decisions"])) for r in problem_catalog_rows()]
    st.markdown(html_table([("Key", ""), ("Problem", ""), ("Severity", ""), ("Decisions", "")], rows),
                unsafe_allow_html=True)

with tab_groups:
    top = max(counts.values())
    bars = "".join(
        f"<div class='cf-groupbar'><span>{e(g)}</span><div class='t'><div style='width:{n / top * 100:.0f}%'>"
        f"</div></div><b class='cf-num'>{n}</b></div>" for g, n in counts.items())
    st.markdown(f"<div class='cf-card'>{bars}</div>", unsafe_allow_html=True)
