"""Shared styling, formatting and small HTML helpers for the UI."""
from html import escape

import streamlit as st

from knowledge_base import load_threshold_table, load_thresholds

from ui.styles import (  # noqa: F401  (re-exported for the pages)
    BORDER, CSS, INK, MUTED, NAVY, PRIORITY, SEVERITY, SEVERITY_COLOR, STATE, STATE_COLOR,
    STATUS, STATUS_COLOR, TEAL, TRACK,
)

LINE = BORDER


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


def icon(name: str) -> str:
    """Material Symbols line icon (the font Streamlit already loads)."""
    return f"<span class='cf-ico' aria-hidden='true'>{name}</span>"


def chip(text: str, icon_name: str = "") -> str:
    return f"<span class='cf-chip'>{icon(icon_name) if icon_name else ''}{e(text)}</span>"


def page_header(title: str, subtitle: str, chip_text: str = "", chip_icon: str = ""):
    """Page title and subtitle on the left, a small context chip on the right."""
    right = chip(chip_text, chip_icon) if chip_text else ""
    st.markdown(f"<div class='cf-page'><div><div class='t'>{e(title)}</div>"
                f"<div class='s'>{e(subtitle)}</div></div>{right}</div>", unsafe_allow_html=True)


def section(title: str, icon_name: str = ""):
    st.markdown(f"<div class='cf-section'>{icon(icon_name) if icon_name else ''}{e(title)}</div>",
                unsafe_allow_html=True)


def pill(text: str, colour: str, background: str, with_dot: bool = False) -> str:
    mark = f"<span class='cf-dot' style='background:{colour}'></span>" if with_dot else ""
    return (f"<span class='cf-pill' style='color:{colour};background:{background}'>"
            f"{mark}{e(text)}</span>")


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
            f"<div class='track'><div class='fill' style='width:{score}%;background:{colour}'></div>"
            f"{ticks}<div class='marker' style='left:{score}%;border-color:{colour}'></div></div>"
            f"<div class='bands'>{band_html}</div></div>")


def score_ring(score: float, status: str) -> str:
    """Donut ring (CSS conic-gradient) coloured by status, with the score inside."""
    colour = STATUS_COLOR.get(status, NAVY)
    return (f"<div class='cf-ring' style='background:conic-gradient({colour} {score:.1f}%, "
            f"{TRACK} 0)'><div class='in'><span class='n' style='color:{colour}'>{score:.0f}</span>"
            f"<span class='o'>out of 100</span></div></div>")


def stepper(current: int, steps: dict, skipped: set, review: bool = False) -> str:
    """'Step 2 of 6 – Cash' plus a step tracker (done, current, upcoming, skipped)."""
    segs = []
    for n, (title, _intro) in steps.items():
        state = ("skipped" if n in skipped else "current" if n == current and not review
                 else "done" if n < current or review else "todo")
        mark = icon("check") if state == "done" else str(n)
        segs.append(f"<div class='seg {state}'><div class='dot'>{mark}</div>"
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
      function (b) {                                  // label only, without the icon
        var label = b.querySelector('[data-testid="stMarkdownContainer"]') || b;
        return ACTIONS.indexOf(label.innerText.trim()) >= 0;
      });
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


# number inputs: only digits, commas and one decimal point
_FILTER_JS = """
(function () {
  if (window.__cfInputFilter) return;
  window.__cfInputFilter = true;
  var RULES = [                                       // container key prefix -> allowed input
    {sel: '[class*="st-key-cfrs_"] input',   chars: /[0-9,.]/, dot: true},   // money (rounded on the server)
    {sel: '[class*="st-key-cfdays_"] input', chars: /[0-9]/,  dot: false},   // days
    {sel: '[class*="st-key-cfpct_"] input',  chars: /[0-9.]/, dot: true}     // percentages
  ];
  function ruleFor(el) {
    if (!el || el.tagName !== "INPUT") return null;
    for (var i = 0; i < RULES.length; i++) if (el.matches(RULES[i].sel)) return RULES[i];
    return null;
  }
  function clean(text, rule, current) {               // keep allowed characters, at most one "."
    var out = "", dotUsed = rule.dot && current.indexOf(".") >= 0;
    for (var i = 0; i < text.length; i++) {
      var c = text.charAt(i);
      if (!rule.chars.test(c)) continue;
      if (c === ".") { if (dotUsed) continue; dotUsed = true; }
      out += c;
    }
    return out;
  }
  function selection(el) {                            // number inputs have no selection API
    try { if (el.selectionStart !== null) return [el.selectionStart, el.selectionEnd]; } catch (e) {}
    return null;
  }
  function insert(el, rule, text) {                   // React-safe value change
    var sel = selection(el), value = el.value, next, caret;
    var kept = sel ? value.slice(0, sel[0]) + value.slice(sel[1]) : "";
    var add = clean(text, rule, kept);
    if (sel) { next = value.slice(0, sel[0]) + add + value.slice(sel[1]); caret = sel[0] + add.length; }
    else { next = add; }
    var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(el, next);
    el.dispatchEvent(new Event("input", {bubbles: true}));
    if (sel) { try { el.setSelectionRange(caret, caret); } catch (e) {} }
  }
  function blocked(el, rule, ch) {
    if (!rule.chars.test(ch)) return true;
    if (ch !== ".") return false;
    var sel = selection(el), value = el.value;
    var kept = sel ? value.slice(0, sel[0]) + value.slice(sel[1]) : value;
    return kept.indexOf(".") >= 0;
  }
  document.addEventListener("keydown", function (ev) {        // typing on a keyboard
    var rule = ruleFor(ev.target);
    if (!rule || ev.ctrlKey || ev.metaKey || ev.altKey || ev.key.length !== 1) return;
    if (blocked(ev.target, rule, ev.key)) ev.preventDefault();
  }, true);
  document.addEventListener("beforeinput", function (ev) {    // phone keyboards, autofill
    var rule = ruleFor(ev.target);
    if (!rule || !ev.data || ev.inputType === "insertFromPaste") return;
    for (var i = 0; i < ev.data.length; i++) {
      if (blocked(ev.target, rule, ev.data.charAt(i))) { ev.preventDefault(); return; }
    }
  }, true);
  document.addEventListener("paste", function (ev) {          // paste: strip what is not allowed
    var rule = ruleFor(ev.target);
    if (!rule) return;
    ev.preventDefault();
    insert(ev.target, rule, (ev.clipboardData || window.clipboardData).getData("text") || "");
  }, true);
  document.addEventListener("drop", function (ev) {           // drag-and-drop text
    if (ruleFor(ev.target)) ev.preventDefault();
  }, true);
  document.addEventListener("focusin", function (ev) {        // remember the last valid value
    if (ruleFor(ev.target)) ev.target.__cfLast = ev.target.value;
  }, true);
  document.addEventListener("input", function (ev) {          // keep within the field's max
    var el = ev.target, rule = ruleFor(el);
    if (!rule) return;
    if (el.max !== "" && el.value !== "" && Number(el.value) > Number(el.max)) {
      var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
      setter.call(el, el.__cfLast || "");
      el.dispatchEvent(new Event("input", {bubbles: true}));
      return;
    }
    el.__cfLast = el.value;
  }, true);
})();
"""


def enable_enter_navigation():
    """Inject the Enter-key and number-input filter scripts into the page once."""
    import json
    loader = "<script>var d = window.parent.document;" + "".join(
        f"if (!d.getElementById('{sid}')) {{"
        f"var s = d.createElement('script'); s.id = '{sid}';"
        f"s.textContent = {json.dumps(js)}; d.head.appendChild(s);}}"
        for sid, js in (("cf-enter-nav", _ENTER_JS), ("cf-input-filter", _FILTER_JS))) + "</script>"
    with st.sidebar:
        st.iframe(loader, height=1)


def footer():
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("For educational purposes only — not financial advice. "
               "CashFlow IQ is a rule-based expert system built as a university project.")
