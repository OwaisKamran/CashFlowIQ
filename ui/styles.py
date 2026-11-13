"""Colour palette, type scale and CSS for the whole UI (colour only carries meaning)."""

# base palette
NAVY = "#1E3A5F"           # headings accents, current step, table headers
SIDEBAR = "#13294B"        # dark sidebar
TEAL = "#0F766E"           # accent on light backgrounds: buttons, done steps, badges
TEAL_ON_DARK = "#14B8A6"   # accent on the dark sidebar
TEAL_SOFT = "#E6F4F2"
PAGE_BG = "#F4F6FA"
CARD = "#FFFFFF"
BORDER = "#E3E8EF"
INK = "#1F2937"            # body text
MUTED = "#5B6472"          # secondary text (AA on page and cards)
MUTED_ON_TINT = "#4B5563"  # secondary text on coloured backgrounds
NAVY_SOFT = "#EEF2F7"
SIDEBAR_TEXT = "#E6ECF5"
SIDEBAR_LABEL = "#9fb3cf"  # small uppercase section labels in the sidebar
TRACK = "#E3E8EF"          # empty part of bars and the score ring

# status: (text colour, soft background)
STATUS = {
    "Healthy": ("#15803D", "#DCFCE7"),
    "Watch": ("#B45309", "#FEF3C7"),
    "Risky": ("#C2410C", "#FFEDD5"),
    "Crisis": ("#B91C1C", "#FEE2E2"),
    "Insufficient data": ("#4B5563", "#F3F4F6"),
    "Unknown": ("#4B5563", "#F3F4F6"),
}
STATUS_COLOR = {k: v[0] for k, v in STATUS.items()}

# problem severity: (text colour, soft background)
SEVERITY = {
    "Critical": ("#B91C1C", "#FEE2E2"),
    "High": ("#C2410C", "#FFEDD5"),
    "Medium": ("#B45309", "#FEF3C7"),
    "Low": ("#475569", "#F1F5F9"),
}
SEVERITY_COLOR = {k: v[0] for k, v in SEVERITY.items()}

# action priority chip: (text colour, soft background)
PRIORITY = {
    "Critical": ("#B91C1C", "#FEE2E2"),     # Do this now
    "High": ("#B45309", "#FEF3C7"),         # Do this soon
    "Medium": (TEAL, TEAL_SOFT),            # Worth doing
    "Low": ("#4B5563", "#F3F4F6"),          # When convenient
}

# key figure state: (colour, chip text, soft background)
STATE = {
    "good": ("#15803D", "Safe", "#DCFCE7"),
    "neutral": ("#B45309", "Borderline", "#FEF3C7"),
    "bad": ("#B91C1C", "Warning", "#FEE2E2"),
    "na": ("#4B5563", "Not available", "#F3F4F6"),
}
STATE_COLOR = {k: v[0] for k, v in STATE.items()}

# runway band -> colour
RUNWAY_COLOR = {"critical": "#B91C1C", "short": "#C2410C", "moderate": "#B45309",
                "comfortable": "#15803D"}

RADIUS = "12px"
SHADOW = "0 1px 2px rgba(16, 24, 40, .05), 0 1px 3px rgba(16, 24, 40, .04)"
HEAD_FONT = "'Plus Jakarta Sans', 'Inter', system-ui, sans-serif"
BODY_FONT = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"

CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap');

  /* type */
  html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], p, li, label, input,
  textarea, button, select, td, th, [data-testid="stMarkdownContainer"],
  [data-testid="stWidgetLabel"] {{ font-family: {BODY_FONT}; }}
  h1, h2, h3, h4, .cf-h {{ font-family: {HEAD_FONT} !important; letter-spacing: -.01em; }}
  h1 {{ font-size: 32px !important; font-weight: 700 !important; color: {INK}; }}
  h2 {{ font-size: 20px !important; font-weight: 700 !important; color: {INK}; }}
  h3, h4, h5 {{ font-size: 16px !important; font-weight: 600 !important; color: {INK}; }}
  [data-testid="stCaptionContainer"], .cf-muted {{ font-size: 13px; color: {MUTED}; }}
  .cf-num, .cf-kpi .v, .cf-ring .n, .cf-runway .v, .cf-table td.num {{ font-variant-numeric: tabular-nums; }}
  [data-testid="stMainBlockContainer"] {{ max-width: 1180px; padding-top: 2.2rem; }}

  .cf-ico {{ font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal;
            font-size: 1.2em; line-height: 1; vertical-align: -.22em; letter-spacing: normal;
            text-transform: none; white-space: nowrap; font-feature-settings: 'liga';
            -webkit-font-smoothing: antialiased; }}

  /* sidebar */
  [data-testid="stSidebar"] {{ background: {SIDEBAR}; }}
  [data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT}; }}
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ color: {SIDEBAR_LABEL} !important; }}
  [data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * {{
      color: {SIDEBAR_LABEL} !important; font-size: 11px !important; font-weight: 600 !important;
      text-transform: uppercase; letter-spacing: .08em; }}
  [data-testid="stSidebarNavLink"] {{ border-radius: 8px; }}
  [data-testid="stSidebarNavLink"]:hover {{ background: rgba(255, 255, 255, .06); }}
  [data-testid="stSidebarNavLink"][aria-current="page"] {{ background: rgba(20, 184, 166, .14); }}
  [data-testid="stSidebarNavLink"][aria-current="page"] * {{ color: {TEAL_ON_DARK} !important;
      font-weight: 600; }}
  [data-testid="stSidebar"] hr {{ border-color: rgba(255, 255, 255, .12); }}
  /* the 1px frame that loads the page scripts: keep it running but take it out of the layout */
  [data-testid="stSidebar"] [data-testid="stElementContainer"]:has(iframe) {{
      position: absolute !important; width: 0 !important; height: 0 !important; overflow: hidden;
      opacity: 0; pointer-events: none; margin: 0 !important; }}
  [data-testid="stSidebar"] .cf-side-name {{ font-family: {HEAD_FONT}; font-weight: 700;
      font-size: 17px; color: #FFFFFF; }}

  /* page header: title + subtitle left, context chip right */
  .cf-page {{ display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between;
             gap: .6rem 1.5rem; margin: 0 0 1.6rem; }}
  .cf-page .t {{ font-family: {HEAD_FONT}; font-size: 32px; font-weight: 700; color: {INK};
                line-height: 1.15; letter-spacing: -.015em; }}
  .cf-page .s {{ font-size: 15px; color: {MUTED}; margin-top: .35rem; }}
  .cf-chip {{ display: inline-flex; align-items: center; gap: .35rem; font-size: 13px; font-weight: 600;
             color: {NAVY}; background: {CARD}; border: 1px solid {BORDER}; border-radius: 999px;
             padding: .3rem .75rem; white-space: nowrap; }}
  .cf-chip .cf-ico {{ color: {TEAL}; }}

  /* section titles */
  .cf-section {{ font-family: {HEAD_FONT}; font-size: 20px; font-weight: 700; color: {INK};
                margin: 2rem 0 .8rem; display: flex; align-items: center; gap: .5rem; }}
  .cf-section .cf-ico {{ color: {TEAL}; font-size: 22px; }}
  .cf-eyebrow {{ font-size: 12px; letter-spacing: .07em; text-transform: uppercase;
                color: {MUTED}; font-weight: 600; margin-bottom: .25rem; }}

  /* cards: HTML cards and keyed Streamlit containers */
  .cf-card, [class*="st-key-cfcard"], [class*="st-key-cfhero"], [class*="st-key-cfsample"] {{
      background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}; box-shadow: {SHADOW}; }}
  .cf-card {{ padding: 1.1rem 1.25rem; }}
  [class*="st-key-cfcard"] {{ padding: 1.3rem 1.4rem 1.1rem; }}
  .cf-card-title {{ font-family: {HEAD_FONT}; font-size: 16px; font-weight: 600; color: {INK};
                   display: flex; align-items: center; gap: .45rem; }}
  .cf-card-title .cf-ico {{ color: {TEAL}; }}

  /* chips */
  .cf-pill {{ display: inline-flex; align-items: center; font-size: 12px; font-weight: 600;
             line-height: 1.2; padding: .22rem .6rem; border-radius: 999px; white-space: nowrap; }}
  .cf-dot {{ display: inline-block; width: .5rem; height: .5rem; border-radius: 50%;
            margin-right: .35rem; vertical-align: middle; flex: none; }}

  /* welcome hero */
  [class*="st-key-cfhero"] {{ padding: 2.2rem 2.2rem 1.8rem; }}
  .cf-hero .t {{ font-family: {HEAD_FONT}; font-size: 32px; font-weight: 700; color: {INK};
                line-height: 1.2; margin: .7rem 0 .5rem; letter-spacing: -.015em; }}
  .cf-hero .d {{ font-size: 17px; color: {INK}; max-width: 620px; line-height: 1.55; }}
  .cf-hero .n {{ font-size: 13px; color: {MUTED}; margin-top: .4rem; }}
  .cf-tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: .8rem;
              margin: 1.5rem 0 1.4rem; }}
  .cf-tile {{ background: {PAGE_BG}; border: 1px solid {BORDER}; border-radius: 10px; padding: .9rem 1rem; }}
  .cf-tile .i {{ width: 34px; height: 34px; border-radius: 9px; background: {TEAL_SOFT}; color: {TEAL};
                display: flex; align-items: center; justify-content: center; margin-bottom: .55rem; }}
  .cf-tile .i .cf-ico {{ vertical-align: 0; font-size: 20px; }}
  .cf-tile .h {{ font-family: {HEAD_FONT}; font-weight: 600; font-size: 16px; color: {INK}; }}
  .cf-tile .p {{ font-size: 13px; color: {MUTED}; margin-top: .2rem; line-height: 1.45; }}

  /* stepper */
  .cf-stepper {{ margin: 0 0 1.3rem; }}
  .cf-stepper .now {{ font-size: 13px; color: {MUTED}; margin-bottom: .75rem; }}
  .cf-stepper .now b {{ color: {NAVY}; }}
  .cf-stepper .track {{ display: flex; align-items: flex-start; }}
  .cf-stepper .seg {{ flex: 1; position: relative; text-align: center; min-width: 0; }}
  .cf-stepper .seg::before {{ content: ""; position: absolute; top: 15px; left: -50%; width: 100%;
                             height: 2px; background: {BORDER}; }}
  .cf-stepper .seg:first-child::before {{ display: none; }}
  .cf-stepper .seg.done::before, .cf-stepper .seg.current::before {{ background: {TEAL}; }}
  .cf-stepper .dot {{ position: relative; z-index: 1; width: 32px; height: 32px; margin: 0 auto;
                     border-radius: 50%; display: flex; align-items: center; justify-content: center;
                     font-size: 13px; font-weight: 700; background: {CARD}; border: 2px solid #CBD5E1;
                     color: {MUTED}; box-sizing: border-box; font-variant-numeric: tabular-nums; }}
  .cf-stepper .dot .cf-ico {{ vertical-align: 0; font-size: 18px; }}
  .cf-stepper .seg.done .dot {{ background: {TEAL}; border-color: {TEAL}; color: #FFFFFF; }}
  .cf-stepper .seg.current .dot {{ background: {NAVY}; border-color: {NAVY}; color: #FFFFFF;
                                   box-shadow: 0 0 0 4px {NAVY_SOFT}; }}
  .cf-stepper .seg.skipped .dot {{ background: {PAGE_BG}; border: 2px dashed #9CA3AF; color: #6B7280; }}
  .cf-stepper .name {{ font-size: 12px; color: {MUTED}; margin-top: .4rem; padding: 0 .2rem; }}
  .cf-stepper .seg.done .name {{ color: {TEAL}; font-weight: 600; }}
  .cf-stepper .seg.current .name {{ color: {NAVY}; font-weight: 700; }}
  .cf-stepper .seg.skipped .name {{ text-decoration: line-through; }}

  /* Rs prefix on money inputs */
  [class*="st-key-cfrs_"] [data-testid="stTextInputRootElement"] {{ display: flex; align-items: center; }}
  [class*="st-key-cfrs_"] [data-testid="stTextInputRootElement"]::before {{ content: "Rs"; flex: none;
      padding: 0 .1rem 0 .8rem; font-size: 14px; font-weight: 600; color: {MUTED}; }}

  /* segmented Yes / No / Not sure */
  [data-testid="stButtonGroup"] button {{ min-width: 5.2rem; }}

  /* status card with the score ring */
  .cf-status {{ background: {CARD}; border: 1px solid {BORDER}; border-left: 4px solid; border-radius: {RADIUS};
               box-shadow: {SHADOW}; padding: 1.2rem 1.4rem; height: 100%; box-sizing: border-box; }}
  .cf-status .row {{ display: flex; gap: 1.4rem; align-items: center; flex-wrap: wrap; }}
  .cf-status .text {{ flex: 1 1 16rem; min-width: 0; }}
  .cf-status .label {{ font-family: {HEAD_FONT}; font-size: 30px; font-weight: 700; line-height: 1.15; }}
  .cf-summary p {{ font-size: 15px; line-height: 1.55; margin: .3rem 0 0; color: {INK}; }}
  .cf-ring {{ width: 128px; height: 128px; border-radius: 50%; flex: none; display: flex;
             align-items: center; justify-content: center; }}
  .cf-ring .in {{ width: 100px; height: 100px; border-radius: 50%; background: {CARD}; display: flex;
                 flex-direction: column; align-items: center; justify-content: center; }}
  .cf-ring .n {{ font-family: {HEAD_FONT}; font-size: 32px; font-weight: 700; line-height: 1; }}
  .cf-ring .o {{ font-size: 12px; color: {MUTED}; margin-top: .2rem; }}

  /* health score scale under the ring */
  .cf-score {{ margin-top: 1.1rem; }}
  .cf-score .track {{ position: relative; height: 8px; background: {TRACK}; border-radius: 999px; }}
  .cf-score .fill {{ height: 100%; border-radius: 999px; }}
  .cf-score .tick {{ position: absolute; top: 0; width: 2px; height: 100%; background: {CARD}; }}
  .cf-score .marker {{ position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%;
                      background: {CARD}; border: 3px solid; transform: translate(-50%, -50%);
                      box-sizing: border-box; }}
  .cf-score .bands {{ display: flex; font-size: 12px; color: {MUTED}; margin-top: .4rem; }}
  .cf-score .bands span {{ text-align: center; }}
  .cf-score .cap {{ font-size: 12px; color: {MUTED}; margin-top: .45rem; }}

  /* cash runway card */
  .cf-runway {{ height: 100%; box-sizing: border-box; }}
  .cf-runway .v {{ font-family: {HEAD_FONT}; font-size: 34px; font-weight: 700; margin: .5rem 0 .1rem;
                  line-height: 1.1; }}
  .cf-runway .bar {{ position: relative; height: 12px; background: {TRACK}; border-radius: 999px;
                    margin: 1.1rem 0 .3rem; }}
  .cf-runway .fill {{ height: 100%; border-radius: 999px; min-width: 6px; }}
  .cf-runway .mk {{ position: absolute; top: -5px; width: 2px; height: 22px; background: {NAVY}; }}
  .cf-runway .ml {{ position: absolute; top: 22px; transform: translateX(-50%); font-size: 12px;
                   color: {MUTED}; white-space: nowrap; font-variant-numeric: tabular-nums; }}
  .cf-runway .m {{ font-size: 14px; color: {INK}; margin-top: 2rem; line-height: 1.45; }}

  /* KPI tiles */
  .cf-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: .9rem; }}
  .cf-kpi {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}; box-shadow: {SHADOW};
            padding: 1rem 1.1rem; }}
  .cf-kpi .top {{ display: flex; justify-content: space-between; align-items: center; gap: .5rem; }}
  .cf-kpi .l {{ font-size: 13px; font-weight: 600; color: {MUTED}; }}
  .cf-kpi .v {{ font-family: {HEAD_FONT}; font-size: 28px; font-weight: 700; color: {INK}; margin: .45rem 0 .1rem; }}
  .cf-kpi .b {{ font-size: 12px; color: {MUTED}; }}

  /* all figures (in the expander) */
  .cf-kfs {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr)); gap: .8rem; }}
  .cf-kf {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; padding: .8rem .95rem; }}
  .cf-kf .top {{ display: flex; justify-content: space-between; align-items: center; gap: .5rem; }}
  .cf-kf .l {{ font-size: 14px; font-weight: 600; color: {INK}; }}
  .cf-kf .v {{ font-size: 20px; font-weight: 700; color: {INK}; margin: .3rem 0 .1rem;
              font-variant-numeric: tabular-nums; }}
  .cf-kf .b {{ font-size: 12px; color: {MUTED}; }}
  .cf-kf .m {{ font-size: 14px; color: {INK}; margin-top: .45rem; line-height: 1.45; }}

  /* problems */
  .cf-item {{ display: flex; gap: .6rem 1rem; flex-wrap: wrap; background: {CARD};
             border: 1px solid {BORDER}; border-left: 4px solid {BORDER}; border-radius: {RADIUS};
             box-shadow: {SHADOW}; padding: .9rem 1.1rem; margin-bottom: .6rem; }}
  .cf-item .sev {{ flex: none; padding-top: .1rem; }}
  .cf-item .main {{ flex: 1 1 18rem; min-width: 0; }}
  .cf-item .title {{ font-family: {HEAD_FONT}; font-weight: 600; font-size: 16px; color: {INK}; }}
  .cf-item .desc {{ color: {MUTED}; font-size: 14px; margin-top: .2rem; }}
  .cf-item .meta {{ color: {MUTED}; font-size: 13px; margin-top: .3rem; }}
  .cf-item .conf {{ flex: none; text-align: right; font-variant-numeric: tabular-nums; min-width: 6.5rem; }}
  .cf-bar {{ height: 5px; background: {TRACK}; margin-top: .35rem; border-radius: 999px; }}
  .cf-bar > div {{ height: 5px; background: {NAVY}; border-radius: 999px; }}

  /* actions checklist */
  ol.cf-actions {{ list-style: none; padding: 0; margin: 0; counter-reset: act; }}
  ol.cf-actions li {{ counter-increment: act; position: relative; background: {CARD};
                     border: 1px solid {BORDER}; border-radius: {RADIUS}; box-shadow: {SHADOW};
                     padding: .9rem 1.1rem .9rem 3.6rem; margin-bottom: .6rem; }}
  ol.cf-actions li::before {{ content: counter(act); position: absolute; left: 1.1rem; top: .95rem;
                             width: 28px; height: 28px; border-radius: 50%; background: {TEAL};
                             color: #FFFFFF; font-weight: 700; font-size: 13px;
                             display: flex; align-items: center; justify-content: center; }}
  ol.cf-actions .title {{ font-family: {HEAD_FONT}; font-weight: 600; font-size: 16px; color: {INK}; }}
  ol.cf-actions .meta {{ color: {MUTED}; font-size: 14px; margin-top: .25rem; }}
  ol.cf-actions .tech {{ color: {MUTED}; font-size: 13px; margin-left: .5rem; }}

  .cf-note {{ border: 1px solid #FDE68A; border-left: 4px solid #B45309; border-radius: {RADIUS};
             padding: .7rem 1rem; margin: .6rem 0; background: #FEF3C7; font-size: 14px; color: {INK}; }}
  .cf-goods {{ display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; margin-top: .8rem; }}

  /* stat tiles (Knowledge Base) */
  .cf-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: .9rem;
              margin: 0 0 1.4rem; }}
  .cf-stat {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}; box-shadow: {SHADOW};
             padding: 1rem 1.1rem; display: flex; gap: .9rem; align-items: center; }}
  .cf-stat .i {{ width: 42px; height: 42px; border-radius: 10px; background: {TEAL_SOFT}; color: {TEAL};
                display: flex; align-items: center; justify-content: center; flex: none; }}
  .cf-stat .i .cf-ico {{ vertical-align: 0; font-size: 22px; }}
  .cf-stat .v {{ font-family: {HEAD_FONT}; font-size: 26px; font-weight: 700; color: {INK};
                line-height: 1.1; font-variant-numeric: tabular-nums; }}
  .cf-stat .l {{ font-size: 13px; color: {MUTED}; }}

  /* HTML tables with a navy header */
  .cf-scroll {{ max-height: 560px; overflow: auto; border: 1px solid {BORDER}; border-radius: {RADIUS};
               background: {CARD}; box-shadow: {SHADOW}; }}
  .cf-table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; background: {CARD}; }}
  .cf-table th {{ position: sticky; top: 0; z-index: 1; background: {NAVY} !important; color: #FFFFFF;
                 text-align: left; font-weight: 600; font-size: 13px; padding: .6rem .8rem;
                 border: none !important; white-space: nowrap; }}
  .cf-table td {{ border: none !important; border-top: 1px solid {BORDER} !important; padding: .6rem .8rem;
                 vertical-align: top; color: {INK}; background: {CARD} !important; }}
  .cf-table tr:first-child td {{ border-top: none !important; }}
  .cf-table .num {{ text-align: right; white-space: nowrap; }}
  .cf-table .sub {{ display: block; font-size: 12px; color: {MUTED}; margin-top: .15rem; }}
  .cf-table code {{ font-size: 12.5px; }}
  .cf-review {{ border: 1px solid {BORDER}; border-radius: 10px; overflow: hidden; margin-bottom: 1rem; }}
  .cf-review .cf-table td:first-child {{ color: {MUTED}; }}
  .cf-groupbar {{ display: grid; grid-template-columns: 14rem 1fr 2.5rem; gap: .7rem; align-items: center;
                 padding: .45rem 0; border-top: 1px solid {BORDER}; font-size: 14px; }}
  .cf-groupbar:first-child {{ border-top: none; }}
  .cf-groupbar .t {{ height: 10px; background: {TRACK}; border-radius: 999px; }}
  .cf-groupbar .t > div {{ height: 100%; background: {TEAL}; border-radius: 999px; }}

  /* samples (Quick Diagnosis) */
  [class*="st-key-cfsample"] {{ padding: 0 .9rem .9rem; overflow: hidden; gap: .5rem; }}
  .cf-sample .strip {{ height: 5px; margin: 0 -1rem .8rem; }}
  .cf-sample .n {{ font-family: {HEAD_FONT}; font-weight: 600; font-size: 15px; color: {INK}; line-height: 1.3;
                 min-height: 2.6em; }}
  .cf-sample .ty {{ font-size: 13px; color: {MUTED}; margin: .15rem 0 .55rem; }}
  .cf-sample {{ padding-bottom: .35rem; }}

  /* threshold group cards */
  .cf-thr-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: .6rem; }}

  .cf-field-error {{ color: #B91C1C; font-size: 13px; margin: -.3rem 0 .2rem; }}
  [data-testid="stPopover"] {{ margin-top: -.55rem; margin-bottom: .35rem; }}
  [data-testid="stPopover"] button {{ border: none !important; background: transparent !important;
      box-shadow: none !important; padding: 0 !important; min-height: 0 !important;
      color: {TEAL} !important; }}
  [data-testid="stPopover"] button p {{ font-size: 13px !important; }}
  .cf-skip {{ color: {MUTED}; font-size: 13px; font-style: italic; margin: .2rem 0 .8rem;
             padding-left: .7rem; border-left: 2px solid {BORDER}; }}
  .cf-tip {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}; box-shadow: {SHADOW};
            padding: 1rem 1.1rem; font-size: 14px; color: {INK}; line-height: 1.6; }}
  .cf-tip b {{ color: {NAVY}; }}

  @media (max-width: 640px) {{
    [data-testid="stMainBlockContainer"] {{ padding-top: 1rem; }}
    .cf-page .t, .cf-hero .t {{ font-size: 26px; }}
    [class*="st-key-cfhero"] {{ padding: 1.4rem 1.2rem 1.2rem; }}
    .cf-stepper .name {{ display: none; }}
    .cf-stepper .seg.current .name {{ display: block; }}
    .cf-stepper .dot {{ width: 28px; height: 28px; font-size: 12px; }}
    .cf-stepper .seg::before {{ top: 13px; }}
    .cf-item .conf {{ text-align: left; min-width: 0; }}
    .cf-item .main {{ flex-basis: 100%; order: 2; }}
    .cf-status .label {{ font-size: 26px; }}
    .cf-groupbar {{ grid-template-columns: 8rem 1fr 2rem; }}
  }}
</style>
"""
