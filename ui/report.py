"""Diagnosis report shared by the Consultation and Quick Diagnosis pages."""
from datetime import date

import pandas as pd
import streamlit as st

from engine.explanation import figure_meaning, how_table, how_text, plain_summary, why_decision
from knowledge_base.formulas import FORMULAS
from knowledge_base.questions import BUSINESS_TYPE_LABELS, SEASON_LABELS
from knowledge_base.rule_model import NOT_SURE
from knowledge_base.rules import RULES
from ui.components import (
    MUTED, SEVERITY_COLOR, STATE_COLOR, STATUS_COLOR, days, dot, e, ratio, rs, score_bar, section,
)

TOP_ACTIONS = 3
DEBT_RATIOS = {"current_ratio", "quick_ratio", "cash_ratio"}   # divide by short-term debt

# metric -> (label, formatter, benchmark text(th), state(value, wm, th))
FIGURES = [
    ("current_ratio", "Current ratio", ratio, lambda th: f"safe: {th['current_ratio_safe']:.2f} or more",
     lambda v, wm, th: {"strong": "good", "borderline": "neutral", "weak": "bad"}.get(wm.get("cr_band"), "na")),
    ("quick_ratio", "Quick ratio", ratio, lambda th: f"safe: {th['quick_ratio_safe']:.2f} or more",
     lambda v, wm, th: "good" if v >= th["quick_ratio_safe"] else
     "bad" if v < th["quick_ratio_critical"] else "neutral"),
    ("cash_ratio", "Cash ratio", ratio, lambda th: f"safe: {th['cash_ratio_low']:.2f} or more",
     lambda v, wm, th: "good" if v >= th["cash_ratio_low"] else "bad"),
    ("runway_days", "Cash runway", days, lambda th: f"safe: {th['safe_runway_days']:.0f} days or more",
     lambda v, wm, th: {"comfortable": "good", "moderate": "neutral"}.get(wm.get("runway_band"), "bad")),
    ("net_monthly_cash_flow", "Monthly cash left over", rs, lambda th: "safe: above Rs 0",
     lambda v, wm, th: "good" if v >= 0 else "bad"),
    ("working_capital", "Working capital", rs, lambda th: "safe: above Rs 0",
     lambda v, wm, th: "good" if v >= 0 else "bad"),
    ("cash_conversion_cycle", "Cash cycle", days, lambda th: f"safe: {th['long_ccc_days']:.0f} days or less",
     lambda v, wm, th: "good" if v <= th["long_ccc_days"] else "bad"),
    ("debt_service_ratio", "Debt burden", ratio, lambda th: f"safe: {th['dsr_moderate']:.2f} or less",
     lambda v, wm, th: {"normal": "good", "moderate": "neutral", "heavy": "bad"}.get(wm.get("debt_band"), "na")),
    ("receivables_to_sales", "Receivables / monthly sales", ratio,
     lambda th: f"safe: {th['max_receivables_to_sales']:.2f} or less",
     lambda v, wm, th: "good" if v <= th["max_receivables_to_sales"] else "bad"),
    ("inventory_to_sales", "Stock / monthly sales", ratio,
     lambda th: f"safe: {th['max_inventory_to_sales']:.2f} or less",
     lambda v, wm, th: "good" if v <= th["max_inventory_to_sales"] else "bad"),
]


def _figures_table(result, th) -> str:
    rows = []
    debt_free = result.wm.get("cr_band") == "no_debt"           # set by rule R95
    for metric, label, fmt, bench, judge in FIGURES:
        value = result.metrics.get(metric)
        if value is None and debt_free and metric in DEBT_RATIOS:
            shown, state = "No debt", "good"
            meaning = "You owe nothing in the short term, so there is nothing to cover."
        elif debt_free and metric == "working_capital":
            shown, state = fmt(value), "good"
            meaning = f"All {fmt(value)} of your short-term assets are free - you owe nothing."
        else:
            shown = fmt(value)
            state = "na" if value is None else judge(value, result.wm, th)
            meaning = figure_meaning(metric, value, th)
        rows.append(
            f"<tr><td title='Formula: {e(FORMULAS[metric][1])}'>{e(label)}"
            f"<div class='cf-muted' style='font-size:.75rem'>{e(bench(th))}</div></td>"
            f"<td class='num'>{e(shown)}</td>"
            f"<td>{dot(STATE_COLOR[state])}{e(meaning)}</td></tr>")
    return ("<table class='cf-table'><thead><tr><th>Figure</th><th class='num'>Value</th>"
            "<th>What it means for you</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


# plain words for owners; CF and rule IDs only in the technical view
URGENCY = {"Critical": "Do this now", "High": "Do this soon", "Medium": "Worth doing",
           "Low": "When convenient"}
SERIOUSNESS = {"Critical": "Critical", "High": "Serious", "Medium": "Moderate", "Low": "Minor"}
UNSURE_LINE = "You weren't sure about this — worth checking."


def likelihood(cf: float) -> str:
    """Certainty factor in plain words."""
    return "Very likely" if cf >= 0.85 else "Likely" if cf >= 0.65 else "Possible"


def _actions_html(decisions, start=1, tech=False) -> str:
    items = []
    for d in decisions:
        colour = SEVERITY_COLOR[d["severity"]]
        if tech:
            meta = (f"<span style='color:{colour};font-weight:600'>{d['severity']}</span> "
                    f"priority · CF {d['cf']:.2f} · rules {', '.join(d['rule_ids'])}")
        else:
            meta = f"<span style='color:{colour};font-weight:600'>{URGENCY[d['severity']]}</span>"
        items.append(
            f"<li><div class='title'>{e(d['text'])}</div>"
            f"<div class='meta'>{e(d['reason'])}</div>"
            f"<div class='meta'>{meta}</div></li>")
    return f"<ol class='cf-actions' start='{start}'>{''.join(items)}</ol>"


def render_report(result, th, key="report"):
    inputs = result.inputs
    name = inputs.get("business_name") or "Your business"
    st.markdown("<div class='cf-eyebrow' style='margin-top:1rem'>Cash flow diagnosis report</div>",
                unsafe_allow_html=True)
    st.markdown(f"## {name}")
    btype = BUSINESS_TYPE_LABELS.get(inputs.get("business_type"), "")
    season = SEASON_LABELS.get(inputs.get("season"), "")
    st.markdown(f"<div class='cf-muted'>{e(btype)} · {e(season)} season · "
                f"{date.today():%d %b %Y}</div>", unsafe_allow_html=True)
    tech = st.toggle("Show technical details (rule IDs and certainty factors)",
                     key=f"{key}_tech", value=False)

    # 1. status + plain summary
    colour = STATUS_COLOR.get(result.status, MUTED)
    paragraphs = "".join(f"<p>{e(s)}</p>" for s in plain_summary(result))
    left, right = st.columns([3, 2], gap="large", vertical_alignment="center")
    left.markdown(f"<div class='cf-status' style='border-color:{colour}'>"
                  f"<div class='cf-eyebrow'>Overall status</div>"
                  f"<div class='label' style='color:{colour}'>{e(result.status)}</div>"
                  f"<div class='cf-summary' style='margin-top:.4rem'>{paragraphs}</div></div>",
                  unsafe_allow_html=True)
    if result.health_score is not None:
        right.markdown(score_bar(result.health_score, th, result.status) +
                       "<div class='cf-muted' style='font-size:.8rem;margin-top:.7rem'>"
                       "Higher is healthier: 75 or more is healthy, below 35 is a crisis. "
                       "Each problem found lowers the score.</div>", unsafe_allow_html=True)

    for w in result.warnings:
        st.markdown(f"<div class='cf-note'><b>Please check your answers.</b> {e(w['text'])}</div>",
                    unsafe_allow_html=True)

    if not result.sufficient:
        section("Missing information")
        st.markdown("".join(f"<div class='cf-item'><div class='main'>{e(m['label'])}"
                            + (f"<div class='meta'>detected by rule {m['rule_id']}</div>" if tech else "")
                            + "</div></div>" for m in result.missing), unsafe_allow_html=True)
    else:
        # 2. what to do
        section("What you should do")
        if result.decisions:
            st.markdown(_actions_html(result.decisions[:TOP_ACTIONS], tech=tech),
                        unsafe_allow_html=True)
            rest = result.decisions[TOP_ACTIONS:]
            if rest:
                with st.expander(f"Show all actions ({len(result.decisions)})"):
                    st.markdown(_actions_html(rest, start=TOP_ACTIONS + 1, tech=tech),
                                unsafe_allow_html=True)
        else:
            st.markdown("<p class='cf-muted'>No action needed.</p>", unsafe_allow_html=True)

        # 3. what we found
        section(f"What we found ({len(result.problems)} problem"
                f"{'' if len(result.problems) == 1 else 's'})")
        if not result.problems:
            st.markdown("<p class='cf-muted'>No problems found.</p>", unsafe_allow_html=True)
        items = []
        for p in result.problems:
            sev_colour = SEVERITY_COLOR[p["severity"]]
            # "Not sure"-only problems are always Possible
            unsure = (f"<div class='meta'>{e(UNSURE_LINE)}</div>" if p.get("unsure") else "")
            if tech:
                rules = " + ".join(ev[0] for ev in p["evidence"])
                note = " (certainty factors combined)" if len(p["evidence"]) > 1 else ""
                meta = f"{unsure}<div class='meta'>Found by rule {rules}{note}</div>"
                conf = (f"CF {p['cf']:.2f}<div class='cf-bar'>"
                        f"<div style='width:{p['cf'] * 100:.0f}%'></div></div>")
                sev = p["severity"]
            else:
                meta = unsure
                word = "Possible" if p.get("unsure") else likelihood(p["cf"])
                conf = f"<span class='cf-muted'>{word}</span>"
                sev = SERIOUSNESS[p["severity"]]
            items.append(
                f"<div class='cf-item'><div class='sev' style='color:{sev_colour}'>{sev}</div>"
                f"<div class='main'><div class='title'>{e(p['title'])}</div>"
                f"<div class='desc'>{e(p['description'])}</div>{meta}</div>"
                f"<div class='conf'>{conf}</div></div>")
        st.markdown("".join(items), unsafe_allow_html=True)
        if result.strengths:
            st.markdown("<div class='cf-muted' style='margin-top:.8rem'><b>Good signs:</b> " +
                        "; ".join(e(s["text"]) for s in result.strengths) + ".</div>",
                        unsafe_allow_html=True)

        # 4. key figures
        section("Key figures")
        st.markdown(_figures_table(result, th), unsafe_allow_html=True)

    _render_how(result, key)


def _render_how(result, key):
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("How the system reached this"):
        st.markdown(
            f"The forward-chaining inference engine ran **{result.cycles} cycles** and fired "
            f"**{result.rules_fired} of {len(RULES)} rules**. In each cycle it *matches* every rule "
            "against the facts, *resolves* conflicts (priority, then specificity, then rule "
            "order) and *fires* one rule. The table lists every rule that fired, in order.")
        st.dataframe(pd.DataFrame(how_table(result.trace)), hide_index=True, width="stretch",
                     column_config={"CF": st.column_config.NumberColumn(format="%.2f")})
        st.download_button("Download trace (.txt)", how_text(result.trace),
                           file_name="cashflow_iq_trace.txt", key=f"{key}_download")

        if result.decisions:
            st.markdown("##### Why was an action recommended?")
            labels = [f"{d['rank']}. {d['text']}" for d in result.decisions]
            pick = st.selectbox("Action", labels, label_visibility="collapsed",
                                key=f"{key}_why_pick")
            st.markdown(why_decision(result.decisions[labels.index(pick)], result))

        st.markdown("##### Working memory (all facts)")
        rows = [{"Fact": f.name, "Value": _show(f.value), "CF": round(f.cf, 2),
                 "Source": "your answer" if f.source == "user" else f"rule {f.source}"}
                for f in result.wm.facts.values()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _show(value):
    if value == NOT_SURE:
        return "Not sure"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return "N/A" if value is None else str(value)
