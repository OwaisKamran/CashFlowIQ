"""Diagnosis report shared by the Consultation and Quick Diagnosis pages."""
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from engine.explanation import figure_meaning, how_table, how_text, plain_summary, why_decision
from knowledge_base.formulas import FORMULAS
from knowledge_base.questions import BUSINESS_TYPE_LABELS, SEASON_LABELS
from knowledge_base.rule_model import NOT_SURE
from knowledge_base.rules import RULES
from ui.components import (
    PRIORITY, SEVERITY, STATE, STATUS, days, e, icon, pill, ratio, rs, score_bar, score_ring, section,
)
from ui.styles import BORDER, INK, MUTED, NAVY, NAVY_SOFT, RUNWAY_COLOR

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
FIG = {f[0]: f for f in FIGURES}


def _figure(result, th, metric):
    """(shown value, state, meaning) for one key figure."""
    _metric, _label, fmt, _bench, judge = FIG[metric]
    value = result.metrics.get(metric)
    debt_free = result.wm.get("cr_band") == "no_debt"           # set by rule R95
    if value is None and debt_free and metric in DEBT_RATIOS:
        return "No debt", "good", "You owe nothing in the short term, so there is nothing to cover."
    if debt_free and metric == "working_capital":
        return fmt(value), "good", f"All {fmt(value)} of your short-term assets are free - you owe nothing."
    state = "na" if value is None else judge(value, result.wm, th)
    return fmt(value), state, figure_meaning(metric, value, th)


def _figures_table(result, th) -> str:
    cards = []
    for metric, label, _fmt, bench, _judge in FIGURES:
        shown, state, meaning = _figure(result, th, metric)
        colour, word, soft = STATE[state]
        cards.append(
            f"<div class='cf-kf' title='Formula: {e(FORMULAS[metric][1])}'>"
            f"<div class='top'><span class='l'>{e(label)}</span>{pill(word, colour, soft, True)}</div>"
            f"<div class='v'>{e(shown)}</div><div class='b'>{e(bench(th))}</div>"
            f"<div class='m'>{e(meaning)}</div></div>")
    return f"<div class='cf-kfs'>{''.join(cards)}</div>"


def _kpi_tiles(result, th) -> str:
    tiles = []
    for metric in KPIS:
        _m, label, _fmt, bench, _judge = FIG[metric]
        shown, state, _meaning = _figure(result, th, metric)
        colour, word, soft = STATE[state]
        tiles.append(f"<div class='cf-kpi' title='Formula: {e(FORMULAS[metric][1])}'>"
                     f"<div class='top'><span class='l'>{e(label)}</span>{pill(word, colour, soft, True)}</div>"
                     f"<div class='v'>{e(shown)}</div><div class='b'>{e(bench(th))}</div></div>")
    return f"<div class='cf-kpis'>{''.join(tiles)}</div>"


def _runway_card(result, th) -> str:
    value = result.metrics.get("runway_days")
    marks = [th["crisis_runway_days"], th["short_runway_days"], th["safe_runway_days"]]
    top = max(marks[-1] * 4 / 3, (value or 0) * 1.1)
    colour = RUNWAY_COLOR.get(result.wm.get("runway_band"), MUTED) if value is not None else MUTED
    fill = 0 if value is None else min(value / top * 100, 100)
    marks_html = "".join(f"<div class='mk' style='left:{m / top * 100:.1f}%'></div>"
                         f"<div class='ml' style='left:{m / top * 100:.1f}%'>{m:.0f} days</div>"
                         for m in marks)
    return (f"<div class='cf-card cf-runway'><div class='cf-card-title'>{icon('hourglass_bottom')}"
            f"Cash runway</div><div class='v' style='color:{colour}'>{e(days(value))}</div>"
            f"<div class='cf-muted'>safe: {th['safe_runway_days']:.0f} days or more</div>"
            f"<div class='bar'><div class='fill' style='width:{fill:.1f}%;background:{colour}'></div>"
            f"{marks_html}</div>"
            f"<div class='m'>{e(figure_meaning('runway_days', value, th))}</div></div>")


def _ratio_chart(result, th):
    rows = []
    for metric, label, limit, higher_is_better in CHART:
        value = result.metrics.get(metric)
        if value is None:
            continue
        _shown, state, _meaning = _figure(result, th, metric)
        rows.append({"Figure": label, "Value": round(value, 2), "Safe level": th[limit],
                     "Colour": STATE[state][0], "Status": STATE[state][1],
                     "Safe range": f"{'at least' if higher_is_better else 'at most'} {th[limit]:.2f}"})
    if not rows:
        return
    df = pd.DataFrame(rows)
    tips = ["Figure", "Value", "Safe range", "Status"]
    base = alt.Chart(df).encode(y=alt.Y("Figure:N", sort=None, title=None, axis=alt.Axis(
        labelFontSize=13, labelColor=INK, ticks=False, domain=False, labelPadding=10, labelLimit=240)))
    bars = base.mark_bar(cornerRadiusEnd=4, size=18).encode(
        x=alt.X("Value:Q", title=None, axis=alt.Axis(grid=False, labelColor=MUTED, domain=False,
                                                     tickColor=BORDER, labelFontSize=12, tickCount=5)),
        color=alt.Color("Colour:N", scale=None), tooltip=tips)
    safe = base.mark_tick(color=NAVY, thickness=3, size=28).encode(x="Safe level:Q", tooltip=tips)
    text = base.mark_text(align="left", dx=8, color=INK, fontSize=12).encode(
        x="Value:Q", text=alt.Text("Value:Q", format=".2f"))
    chart = (bars + safe + text).properties(height=48 * len(rows), background="#FFFFFF").configure_view(
        strokeWidth=0, fill="#FFFFFF").configure(font="Inter")
    with st.container(key="cfcard_chart"):
        st.markdown(f"<div class='cf-card-title'>{icon('bar_chart')}Your ratios vs safe levels</div>"
                    "<div class='cf-muted'>Bar = your figure (green safe, amber borderline, red warning); "
                    "navy line = the safe level.</div>", unsafe_allow_html=True)
        st.altair_chart(chart, width="stretch")

KPIS = ["current_ratio", "quick_ratio", "cash_conversion_cycle", "debt_service_ratio"]
# chart rows: (metric, label, threshold name, higher is better)
CHART = [("current_ratio", "Current ratio", "current_ratio_safe", True),
         ("quick_ratio", "Quick ratio", "quick_ratio_safe", True),
         ("cash_ratio", "Cash ratio", "cash_ratio_low", True),
         ("debt_service_ratio", "Debt burden", "dsr_moderate", False),
         ("receivables_to_sales", "Receivables / monthly sales", "max_receivables_to_sales", False),
         ("inventory_to_sales", "Stock / monthly sales", "max_inventory_to_sales", False)]


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
        colour, soft = PRIORITY[d["severity"]]
        if tech:
            meta = (pill(f"{d['severity']} priority", colour, soft) +
                    f"<span class='tech'>CF {d['cf']:.2f} · rules {', '.join(d['rule_ids'])}</span>")
        else:
            meta = pill(URGENCY[d["severity"]], colour, soft)
        items.append(
            f"<li><div class='title'>{e(d['text'])}</div>"
            f"<div class='meta'>{e(d['reason'])}</div>"
            f"<div class='meta'>{meta}</div></li>")
    return (f"<ol class='cf-actions' start='{start}' style='counter-reset: act {start - 1}'>"
            f"{''.join(items)}</ol>")


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

    # 1. status card with the score ring, and the cash runway card
    colour, _soft = STATUS.get(result.status, STATUS["Unknown"])
    paragraphs = "".join(f"<p>{e(s)}</p>" for s in plain_summary(result))
    ring = scale = ""
    if result.health_score is not None:
        ring = score_ring(result.health_score, result.status)
        scale = (score_bar(result.health_score, th, result.status)[:-6] +
                 "<div class='cap'>Higher is healthier: 75 or more is healthy, below 35 is a crisis. "
                 "Each problem found lowers the score.</div></div>")
    status_card = (f"<div class='cf-status' style='border-left-color:{colour}'><div class='row'>{ring}"
                   f"<div class='text'><div class='cf-eyebrow'>Overall status</div>"
                   f"<div class='label' style='color:{colour}'>{e(result.status)}</div>"
                   f"<div class='cf-summary'>{paragraphs}</div></div></div>{scale}</div>")
    if result.sufficient:
        left, right = st.columns([1.65, 1], gap="medium")
        left.markdown(status_card, unsafe_allow_html=True)
        right.markdown(_runway_card(result, th), unsafe_allow_html=True)
    else:
        st.markdown(status_card, unsafe_allow_html=True)

    for w in result.warnings:
        st.markdown(f"<div class='cf-note'><b>Please check your answers.</b> {e(w['text'])}</div>",
                    unsafe_allow_html=True)

    if not result.sufficient:
        section("Missing information", "error")
        st.markdown("".join(f"<div class='cf-item'><div class='main'>{e(m['label'])}"
                            + (f"<div class='meta'>detected by rule {m['rule_id']}</div>" if tech else "")
                            + "</div></div>" for m in result.missing), unsafe_allow_html=True)
        _render_how(result, key)
        return

    # 2. key figures: KPI tiles, ratio chart, every figure with its meaning
    section("Key figures", "monitoring")
    st.markdown(_kpi_tiles(result, th), unsafe_allow_html=True)
    st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)
    _ratio_chart(result, th)
    with st.expander("What each figure means"):
        st.markdown(_figures_table(result, th), unsafe_allow_html=True)

    # 3. what to do
    section("What you should do", "checklist")
    if result.decisions:
        st.markdown(_actions_html(result.decisions[:TOP_ACTIONS], tech=tech), unsafe_allow_html=True)
        rest = result.decisions[TOP_ACTIONS:]
        if rest:
            with st.expander(f"Show all actions ({len(result.decisions)})"):
                st.markdown(_actions_html(rest, start=TOP_ACTIONS + 1, tech=tech),
                            unsafe_allow_html=True)
    else:
        st.markdown("<p class='cf-muted'>No action needed.</p>", unsafe_allow_html=True)

    # 4. problems found
    section(f"Problems found ({len(result.problems)})", "troubleshoot")
    if not result.problems:
        st.markdown("<p class='cf-muted'>No problems found.</p>", unsafe_allow_html=True)
    items = []
    for p in result.problems:
        sev_colour, sev_soft = SEVERITY[p["severity"]]
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
            conf = pill(word, NAVY, NAVY_SOFT)
            sev = SERIOUSNESS[p["severity"]]
        items.append(
            f"<div class='cf-item' style='border-left-color:{sev_colour}'>"
            f"<div class='sev'>{pill(sev, sev_colour, sev_soft)}</div>"
            f"<div class='main'><div class='title'>{e(p['title'])}</div>"
            f"<div class='desc'>{e(p['description'])}</div>{meta}</div>"
            f"<div class='conf'>{conf}</div></div>")
    st.markdown("".join(items), unsafe_allow_html=True)
    if result.strengths:
        good, good_soft = STATUS["Healthy"]
        st.markdown("<div class='cf-goods'><b class='cf-muted'>Good signs:</b> " +
                    " ".join(pill(s["text"], good, good_soft, True) for s in result.strengths)
                    + "</div>", unsafe_allow_html=True)

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
