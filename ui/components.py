"""Shared styling, formatting and small HTML helpers for the UI."""
from html import escape

import streamlit as st

from knowledge_base import load_threshold_table, load_thresholds

NAVY = "#1F3A5F"
INK = "#1F2937"
MUTED = "#6B7280"
LINE = "#E5E7EB"

STATUS_COLOR = {
    "Healthy": "#2E7D32", "Watch": "#B7791F", "Risky": "#C2410C", "Crisis": "#B91C1C",
    "Insufficient data": "#6B7280", "Unknown": "#6B7280",
}
SEVERITY_COLOR = {"Critical": "#B91C1C", "High": "#C2410C", "Medium": "#B7791F", "Low": "#6B7280"}
STATE_COLOR = {"good": "#2E7D32", "bad": "#B91C1C", "neutral": "#B7791F", "na": "#9CA3AF"}

CSS = f"""
<style>
  [data-testid="stMainBlockContainer"] {{ max-width: 1080px; padding-top: 2.5rem; }}
  h1 {{ font-size: 1.75rem !important; font-weight: 650 !important; color: {INK}; }}
  h2 {{ font-size: 1.3rem !important; font-weight: 600 !important; color: {INK}; }}
  h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; color: {INK}; }}
  .cf-eyebrow {{ font-size: .75rem; letter-spacing: .08em; text-transform: uppercase;
                color: {MUTED}; font-weight: 600; margin-bottom: .25rem; }}
  .cf-muted {{ color: {MUTED}; font-size: .9rem; }}
  .cf-section {{ font-size: .8rem; letter-spacing: .06em; text-transform: uppercase;
                color: {NAVY}; font-weight: 700; margin: 1.6rem 0 .5rem;
                padding-bottom: .35rem; border-bottom: 1px solid {LINE}; }}
  .cf-status {{ border-left: 4px solid; padding: .9rem 1.1rem; margin: .5rem 0 1rem;
               background: #FAFAFA; }}
  .cf-status .label {{ font-size: 1.35rem; font-weight: 700; }}
  .cf-status .summary {{ color: {INK}; margin-top: .2rem; }}
  .cf-table {{ width: 100%; border-collapse: collapse; font-size: .92rem; border: none !important; }}
  .cf-table th, .cf-table td {{ border-left: none !important; border-right: none !important;
                               border-top: none !important; background: transparent !important; }}
  .cf-table td.assess {{ white-space: nowrap; }}
  .cf-why {{ border-left: 3px solid {NAVY}; background: #F5F6F8; padding: .7rem 1rem;
            margin-top: .6rem; font-size: .9rem; }}
  .cf-why ul {{ margin: .4rem 0 .2rem 1.1rem; padding: 0; }}
  .cf-why li {{ margin: .15rem 0; }}
  .cf-table th {{ text-align: left; font-weight: 600; color: {MUTED}; font-size: .78rem;
                 text-transform: uppercase; letter-spacing: .04em;
                 border-bottom: 1px solid {LINE}; padding: .45rem .5rem; }}
  .cf-table td {{ border-bottom: 1px solid {LINE}; padding: .5rem; vertical-align: top; }}
  .cf-table .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .cf-dot {{ display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
            margin-right: .4rem; vertical-align: middle; }}
  .cf-item {{ display: flex; gap: 1rem; padding: .75rem 0; border-bottom: 1px solid {LINE};
             flex-wrap: wrap; }}
  .cf-item .sev {{ width: 5.5rem; flex: none; font-size: .75rem; font-weight: 700;
                  letter-spacing: .05em; text-transform: uppercase; padding-top: .15rem; }}
  .cf-item .main {{ flex: 1 1 18rem; min-width: 0; }}
  .cf-item .title {{ font-weight: 600; color: {INK}; }}
  .cf-item .desc {{ color: {MUTED}; font-size: .9rem; margin-top: .1rem; }}
  .cf-item .meta {{ color: {MUTED}; font-size: .8rem; margin-top: .25rem; }}
  .cf-item .conf {{ width: 7rem; flex: none; text-align: right; font-variant-numeric: tabular-nums; }}
  .cf-bar {{ height: 4px; background: {LINE}; margin-top: .35rem; }}
  .cf-bar > div {{ height: 4px; background: {NAVY}; }}
  ol.cf-actions {{ padding-left: 1.4rem; margin: .25rem 0; }}
  ol.cf-actions li {{ padding: .55rem 0 .55rem .3rem; border-bottom: 1px solid {LINE}; }}
  ol.cf-actions .title {{ font-weight: 600; color: {INK}; }}
  ol.cf-actions .meta {{ color: {MUTED}; font-size: .85rem; margin-top: .15rem; }}
  .cf-score {{ margin-top: .4rem; }}
  .cf-score .track {{ position: relative; height: 8px; background: {LINE}; margin: .3rem 9px 0; }}
  .cf-score .fill {{ height: 8px; background: {NAVY}; }}
  .cf-score .tick {{ position: absolute; top: -3px; width: 1px; height: 14px; background: #9CA3AF; }}
  .cf-score .marker {{ position: absolute; top: -5px; width: 18px; height: 18px; border-radius: 50%;
                      background: #fff; border: 4px solid; transform: translateX(-50%);
                      box-sizing: border-box; }}
  .cf-score .bands {{ display: flex; font-size: .72rem; color: {MUTED}; margin: .45rem 9px 0; }}
  .cf-score .bands span {{ text-align: center; }}
  .cf-note {{ border-left: 3px solid #B7791F; padding: .5rem .8rem; margin: .5rem 0;
             background: #FFFBEB; font-size: .9rem; }}
  .cf-figures {{ display: flex; flex-wrap: wrap; gap: 2.2rem; margin: .4rem 0 1rem; }}
  .cf-figures .v {{ font-size: 1.6rem; font-weight: 650; color: {INK}; font-variant-numeric: tabular-nums; }}
  .cf-figures .l {{ font-size: .8rem; color: {MUTED}; }}
  .cf-field-error {{ color: #B91C1C; font-size: .85rem; margin: -.3rem 0 .2rem; }}
  /* the "Why are you asking?" popover button: a small text link, not a box */
  [data-testid="stPopover"] {{ margin-top: -.55rem; margin-bottom: .35rem; }}
  [data-testid="stPopover"] button {{ border: none !important; background: transparent !important;
      box-shadow: none !important; padding: 0 !important; min-height: 0 !important;
      color: {NAVY} !important; }}
  [data-testid="stPopover"] button p {{ font-size: .8rem !important; }}
  .cf-skip {{ color: {MUTED}; font-size: .85rem; font-style: italic; margin: .2rem 0 .8rem;
             padding-left: .7rem; border-left: 2px solid {LINE}; }}
  .cf-stepper {{ margin: .2rem 0 1.4rem; }}
  .cf-stepper .now {{ font-size: .95rem; color: {INK}; margin-bottom: .45rem; }}
  .cf-stepper .now b {{ color: {NAVY}; }}
  .cf-stepper .track {{ display: flex; gap: 4px; }}
  .cf-stepper .seg {{ flex: 1; }}
  .cf-stepper .bar {{ height: 5px; background: {LINE}; }}
  .cf-stepper .seg.done .bar, .cf-stepper .seg.current .bar {{ background: {NAVY}; }}
  .cf-stepper .seg.skipped .bar {{ background: repeating-linear-gradient(90deg, {LINE} 0 4px,
                                    transparent 4px 7px); }}
  .cf-stepper .name {{ font-size: .72rem; color: {MUTED}; margin-top: .3rem; }}
  .cf-stepper .seg.current .name {{ color: {NAVY}; font-weight: 700; }}
  .cf-stepper .seg.skipped .name {{ text-decoration: line-through; }}
  .cf-tip {{ background: #F5F6F8; padding: .9rem 1rem; font-size: .88rem; color: {INK}; }}
  .cf-tip b {{ color: {NAVY}; }}
  .cf-summary p {{ font-size: 1.05rem; line-height: 1.55; margin: 0 0 .35rem; color: {INK}; }}
  @media (max-width: 640px) {{
    .cf-stepper .name {{ display: none; }}
    .cf-table .hide-sm {{ display: none; }}
    .cf-item {{ gap: .2rem 1rem; }}
    .cf-item .sev {{ width: auto; order: -2; }}
    .cf-item .conf {{ width: auto; text-align: left; order: -1; margin-left: auto;
                     display: flex; gap: .3rem; align-items: baseline; }}
    .cf-item .conf .cf-bar {{ display: none; }}
    .cf-item .main {{ flex-basis: 100%; }}
    .cf-figures {{ gap: 1.2rem; }}
  }}
</style>
"""


# session state shared by all pages
def init_state():
    if "thresholds" not in st.session_state:
        st.session_state.thresholds = load_thresholds()
        st.session_state.threshold_defaults = load_thresholds()
        st.session_state.threshold_table = load_threshold_table()


def thresholds_modified() -> bool:
    return st.session_state.thresholds != st.session_state.threshold_defaults


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# number formatting
def rs(value) -> str:
    """Format money as Rs 1,250,000."""
    if value is None:
        return "N/A"
    return f"{'-' if value < 0 else ''}Rs {abs(value):,.0f}"


def ratio(value) -> str:
    return "N/A" if value is None else f"{value:,.2f}"


def days(value) -> str:
    return "N/A" if value is None else f"{value:,.0f} days"


# small HTML building blocks
def e(text) -> str:
    return escape(str(text))


def section(title: str):
    st.markdown(f"<div class='cf-section'>{e(title)}</div>", unsafe_allow_html=True)


def dot(colour: str) -> str:
    return f"<span class='cf-dot' style='background:{colour}'></span>"


def score_bar(score: float, th: dict, status: str = "") -> str:
    """Health score bar with a marker and the status bands."""
    crisis, watch, healthy = th["crisis_score"], th["watch_score"], th["healthy_score"]
    colour = STATUS_COLOR.get(status, NAVY)
    ticks = "".join(f"<div class='tick' style='left:{v}%'></div>" for v in (crisis, watch, healthy))
    bands = [("Crisis", crisis), ("Risky", watch - crisis), ("Watch", healthy - watch),
             ("Healthy", 100 - healthy)]
    band_html = "".join(f"<span style='width:{w}%'>{n}</span>" for n, w in bands)
    return (f"<div class='cf-score'>"
            f"<div style='display:flex;justify-content:space-between;align-items:baseline'>"
            f"<span class='cf-eyebrow'>Health score</span>"
            f"<span><b style='font-size:1.6rem;color:{colour}'>{score:.0f}</b> "
            f"<span class='cf-muted'>out of 100</span></span></div>"
            f"<div class='track'><div class='fill' style='width:{score}%;background:{colour}'></div>"
            f"{ticks}<div class='marker' style='left:{score}%;border-color:{colour}'></div></div>"
            f"<div class='bands'>{band_html}</div></div>")


def stepper(current: int, steps: dict, skipped: set, review: bool = False) -> str:
    """'Step 2 of 6 – Cash' plus a segmented progress bar."""
    segs = []
    for n, (title, _intro) in steps.items():
        state = ("skipped" if n in skipped else "current" if n == current and not review
                 else "done" if n < current or review else "todo")
        segs.append(f"<div class='seg {state}'><div class='bar'></div>"
                    f"<div class='name'>{e(title)}</div></div>")
    now = ("<b>Review your answers</b>" if review else
           f"Step {current} of {len(steps)} – <b>{e(steps[current][0])}</b>")
    return (f"<div class='cf-stepper'><div class='now'>{now}</div>"
            f"<div class='track'>{''.join(segs)}</div></div>")


# Enter key: move to the next box, press Next on the last box
_ENTER_JS = """
(function () {
  if (window.__cfEnterNav) return;
  window.__cfEnterNav = true;
  var ACTIONS = ["Next", "Back to review", "Run diagnosis"];
  function boxes() {
    return Array.prototype.filter.call(
      document.querySelectorAll('[data-testid="stMain"] input'),
      function (el) {
        return (el.type === "text" || el.type === "number") &&
               el.getAttribute("role") !== "combobox" && !el.disabled &&
               el.offsetParent !== null;
      });
  }
  function actionButton() {
    return Array.prototype.find.call(
      document.querySelectorAll('[data-testid="stMain"] button'),
      function (b) { return ACTIONS.indexOf(b.innerText.trim()) >= 0; });
  }
  function labels() {
    return boxes().map(function (el) { return el.getAttribute("aria-label"); }).join("|");
  }
  function nextAfter(label) {                         // box that follows `label` right now
    var list = boxes();
    for (var k = 0; k < list.length; k++) {
      if (list[k].getAttribute("aria-label") === label) return list[k + 1] || null;
    }
    return null;
  }
  function go(el) { el.focus(); if (el.select) el.select(); }
  function when(test, then, ms) {                     // poll until test() or timeout
    var start = Date.now();
    (function tick() {
      if (test() || Date.now() - start > ms) { then(); return; }
      setTimeout(tick, 100);
    })();
  }
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" || ev.shiftKey || ev.isComposing) return;
    var box = ev.target;
    if (boxes().indexOf(box) < 0) return;
    var label = box.getAttribute("aria-label");
    var next = nextAfter(label);
    if (next) {
      go(next);                                       // 1) move on at once (same event)
      setTimeout(function () {                        // 2) after the redraw, a follow-up
        var fresh = nextAfter(label);                 //    question may have appeared
        var here = document.activeElement;
        if (fresh && fresh !== here && here === next && !next.value) go(fresh);
      }, 700);
      return;
    }
    box.blur();                                       // last box: save it, then...
    setTimeout(function () {
      var fresh = nextAfter(label);                   // ...a follow-up box appeared? go there
      if (fresh) { go(fresh); return; }
      var b = actionButton();                         // ...otherwise press Next / Run
      if (!b) return;
      var before = labels();
      b.click();
      when(function () { return labels() !== before; }, function () {
        var l = boxes();
        var first = l.filter(function (el) { return !el.value; })[0] || l[0];
        if (first) go(first);                         // new step: cursor in first empty box
      }, 3000);
    }, 600);
  });
})();
"""


def enable_enter_navigation():
    """Inject the Enter-key script into the page once."""
    import json
    loader = ("<script>var d = window.parent.document;"
              "if (!d.getElementById('cf-enter-nav')) {"
              "var s = d.createElement('script'); s.id = 'cf-enter-nav';"
              f"s.textContent = {json.dumps(_ENTER_JS)}; d.head.appendChild(s);}}</script>")
    with st.sidebar:
        st.iframe(loader, height=1)


def footer():
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("For educational purposes only — not financial advice. "
               "CashFlow IQ is a rule-based expert system built as a university project.")
