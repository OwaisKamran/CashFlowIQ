"""Colour palette and CSS for the whole UI (colour only carries meaning)."""

# base palette
NAVY = "#1E3A5F"           # primary: header band, current step, headings
TEAL = "#0F766E"           # accent: buttons, done steps, number badges
TEAL_SOFT = "#E6F4F2"
PAGE_BG = "#F7F9FC"
CARD = "#FFFFFF"
BORDER = "#E3E8EF"
INK = "#1F2937"            # body text
MUTED = "#6B7280"
MUTED_ON_TINT = "#4B5563"  # muted text on coloured backgrounds (keeps AA contrast)
NAVY_SOFT = "#EEF2F7"      # table header rows, input fill
BAND_SUB = "#C9D6E6"       # subtitle text on the navy band

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

# action priority pill: (text colour, soft background)
PRIORITY = {
    "Critical": ("#B91C1C", "#FEE2E2"),     # Do this now
    "High": ("#B45309", "#FEF3C7"),         # Do this soon
    "Medium": (TEAL, TEAL_SOFT),            # Worth doing
    "Low": ("#4B5563", "#F3F4F6"),          # When convenient
}

# key figure state: (dot colour, pill text, soft background)
STATE = {
    "good": ("#15803D", "Safe", "#DCFCE7"),
    "neutral": ("#B45309", "Borderline", "#FEF3C7"),
    "bad": ("#B91C1C", "Warning", "#FEE2E2"),
    "na": ("#4B5563", "Not available", "#F3F4F6"),
}
STATE_COLOR = {k: v[0] for k, v in STATE.items()}

RADIUS = "8px"
SHADOW = "0 1px 2px rgba(15, 23, 42, .06)"

CSS = f"""
<style>
  [data-testid="stMainBlockContainer"] {{ max-width: 1080px; padding-top: 1.6rem; }}
  [data-testid="stSidebar"] {{ background: {CARD}; }}
  h1 {{ font-size: 1.6rem !important; font-weight: 650 !important; color: {INK}; }}
  h2 {{ font-size: 1.3rem !important; font-weight: 600 !important; color: {INK}; }}
  h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; color: {INK}; }}

  .cf-ico {{ font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal;
            font-size: 1.15em; line-height: 1; vertical-align: -.2em; letter-spacing: normal;
            text-transform: none; white-space: nowrap; font-feature-settings: 'liga';
            -webkit-font-smoothing: antialiased; }}

  /* page header band */
  .cf-band {{ background: {NAVY}; border-radius: {RADIUS}; padding: 1rem 1.3rem 1.05rem;
             margin: 0 0 1.4rem; color: #FFFFFF; }}
  .cf-band .brand {{ font-size: .78rem; font-weight: 600; letter-spacing: .06em;
                    text-transform: uppercase; color: {BAND_SUB}; }}
  .cf-band .title {{ font-size: 1.45rem; font-weight: 650; color: #FFFFFF; margin-top: .15rem;
                    line-height: 1.25; }}
  .cf-band .title .cf-ico {{ margin-right: .35rem; }}
  .cf-band .sub {{ font-size: .92rem; color: {BAND_SUB}; margin-top: .25rem; }}

  .cf-eyebrow {{ font-size: .75rem; letter-spacing: .08em; text-transform: uppercase;
                color: {MUTED}; font-weight: 600; margin-bottom: .25rem; }}
  .cf-muted {{ color: {MUTED}; font-size: .9rem; }}
  .cf-section {{ font-size: .82rem; letter-spacing: .05em; text-transform: uppercase;
                color: {NAVY}; font-weight: 700; margin: 1.8rem 0 .7rem; }}
  .cf-section .cf-ico {{ color: {TEAL}; margin-right: .35rem; font-size: 1.25em; }}

  /* cards */
  [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
      background: {CARD}; }}
  .cf-card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS};
             box-shadow: {SHADOW}; padding: 1rem 1.2rem; }}

  /* pills */
  .cf-pill {{ display: inline-block; font-size: .74rem; font-weight: 600; line-height: 1.2;
             padding: .2rem .55rem; border-radius: 999px; white-space: nowrap; }}
  .cf-pill .cf-dot {{ margin-right: .3rem; }}
  .cf-dot {{ display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
            margin-right: .4rem; vertical-align: middle; }}

  /* status banner */
  .cf-status {{ border-left: 4px solid; border-radius: {RADIUS}; padding: 1rem 1.25rem;
               margin: .6rem 0 1rem; display: flex; flex-wrap: wrap; gap: 1rem 2rem;
               align-items: center; }}
  .cf-status .text {{ flex: 1 1 22rem; min-width: 0; }}
  .cf-status .score {{ flex: 0 1 18rem; min-width: 14rem; }}
  .cf-status .label {{ font-size: 1.7rem; font-weight: 750; line-height: 1.2; }}
  .cf-status .summary {{ color: {INK}; margin-top: .2rem; }}
  .cf-status .cf-muted, .cf-status .cf-eyebrow, .cf-status .bands {{ color: {MUTED_ON_TINT}; }}
  .cf-summary p {{ font-size: 1.02rem; line-height: 1.55; margin: 0 0 .35rem; color: {INK}; }}

  /* health score bar */
  .cf-score {{ margin-top: .2rem; }}
  .cf-score .head {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .cf-score .num {{ font-size: 1.7rem; font-weight: 750; font-variant-numeric: tabular-nums; }}
  .cf-score .track {{ position: relative; height: 10px; background: rgba(255,255,255,.75);
                     border: 1px solid {BORDER}; border-radius: 999px; margin-top: .35rem; }}
  .cf-score .fill {{ height: 100%; border-radius: 999px; }}
  .cf-score .tick {{ position: absolute; top: 0; width: 1px; height: 100%; background: #CBD5E1; }}
  .cf-score .marker {{ position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%;
                      background: #FFFFFF; border: 3px solid; transform: translate(-50%, -50%);
                      box-sizing: border-box; }}
  .cf-score .bands {{ display: flex; font-size: .72rem; color: {MUTED}; margin-top: .4rem; }}
  .cf-score .bands span {{ text-align: center; }}

  /* tables (HTML) */
  .cf-table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: .92rem;
              background: {CARD}; border: 1px solid {BORDER} !important; border-radius: {RADIUS};
              overflow: hidden; }}
  .cf-table th, .cf-table td {{ border: none !important; }}
  .cf-table th {{ text-align: left; font-weight: 600; color: {NAVY}; font-size: .78rem;
                 text-transform: uppercase; letter-spacing: .04em; background: {NAVY_SOFT} !important;
                 padding: .5rem .7rem; }}
  .cf-table td {{ border-top: 1px solid {BORDER} !important; padding: .55rem .7rem;
                 vertical-align: top; background: {CARD} !important; }}
  .cf-table tr:first-child td {{ border-top: none !important; }}
  .cf-table .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}

  /* key figure cards */
  .cf-kfs {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr));
            gap: .8rem; margin: .2rem 0 .5rem; }}
  .cf-kf {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS};
           box-shadow: {SHADOW}; padding: .8rem .95rem; }}
  .cf-kf .top {{ display: flex; justify-content: space-between; align-items: center; gap: .5rem; }}
  .cf-kf .l {{ font-size: .85rem; font-weight: 600; color: {INK}; }}
  .cf-kf .v {{ font-size: 1.35rem; font-weight: 700; color: {INK}; margin: .3rem 0 .1rem;
              font-variant-numeric: tabular-nums; }}
  .cf-kf .b {{ font-size: .74rem; color: {MUTED}; }}
  .cf-kf .m {{ font-size: .86rem; color: {INK}; margin-top: .45rem; line-height: 1.4; }}

  /* problem cards */
  .cf-item {{ display: flex; gap: .6rem 1rem; flex-wrap: wrap; background: {CARD};
             border: 1px solid {BORDER}; border-left: 4px solid {BORDER}; border-radius: {RADIUS};
             box-shadow: {SHADOW}; padding: .8rem 1rem; margin-bottom: .6rem; }}
  .cf-item .sev {{ flex: none; padding-top: .1rem; }}
  .cf-item .main {{ flex: 1 1 18rem; min-width: 0; }}
  .cf-item .title {{ font-weight: 600; color: {INK}; }}
  .cf-item .desc {{ color: {MUTED}; font-size: .9rem; margin-top: .15rem; }}
  .cf-item .meta {{ color: {MUTED}; font-size: .8rem; margin-top: .3rem; }}
  .cf-item .conf {{ flex: none; text-align: right; font-variant-numeric: tabular-nums;
                   min-width: 6.5rem; }}
  .cf-bar {{ height: 5px; background: {NAVY_SOFT}; margin-top: .35rem; border-radius: 999px; }}
  .cf-bar > div {{ height: 5px; background: {NAVY}; border-radius: 999px; }}

  /* actions */
  ol.cf-actions {{ list-style: none; padding: 0; margin: .2rem 0; counter-reset: act; }}
  ol.cf-actions li {{ counter-increment: act; position: relative; background: {CARD};
                     border: 1px solid {BORDER}; border-radius: {RADIUS}; box-shadow: {SHADOW};
                     padding: .75rem 1rem .75rem 3.3rem; margin-bottom: .55rem; }}
  ol.cf-actions li::before {{ content: counter(act); position: absolute; left: 1rem; top: .8rem;
                             width: 1.6rem; height: 1.6rem; border-radius: 50%; background: {TEAL};
                             color: #FFFFFF; font-weight: 700; font-size: .85rem;
                             display: flex; align-items: center; justify-content: center; }}
  ol.cf-actions .title {{ font-weight: 600; color: {INK}; }}
  ol.cf-actions .meta {{ color: {MUTED}; font-size: .86rem; margin-top: .2rem; }}
  ol.cf-actions .tech {{ color: {MUTED}; font-size: .8rem; margin-left: .4rem; }}

  .cf-note {{ border-left: 4px solid #B45309; border-radius: {RADIUS}; padding: .6rem .9rem;
             margin: .5rem 0; background: #FEF3C7; font-size: .9rem; color: {INK}; }}

  /* stat figures (Knowledge Base) */
  .cf-figures {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
                gap: .7rem; margin: .4rem 0 1rem; }}
  .cf-figures > div {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS};
                      box-shadow: {SHADOW}; padding: .7rem .9rem; }}
  .cf-figures .v {{ font-size: 1.5rem; font-weight: 700; color: {NAVY}; font-variant-numeric: tabular-nums; }}
  .cf-figures .l {{ font-size: .8rem; color: {MUTED}; }}
  .cf-groups {{ display: flex; flex-wrap: wrap; gap: .4rem; margin: .2rem 0 1rem; }}
  .cf-groups .cf-pill {{ background: {TEAL_SOFT}; color: {TEAL}; font-weight: 600; }}

  .cf-field-error {{ color: #B91C1C; font-size: .85rem; margin: -.3rem 0 .2rem; }}
  [data-testid="stPopover"] {{ margin-top: -.55rem; margin-bottom: .35rem; }}
  [data-testid="stPopover"] button {{ border: none !important; background: transparent !important;
      box-shadow: none !important; padding: 0 !important; min-height: 0 !important;
      color: {TEAL} !important; }}
  [data-testid="stPopover"] button p {{ font-size: .8rem !important; }}
  .cf-skip {{ color: {MUTED}; font-size: .85rem; font-style: italic; margin: .2rem 0 .8rem;
             padding-left: .7rem; border-left: 2px solid {BORDER}; }}

  /* step tracker */
  .cf-stepper {{ margin: 0 0 1.2rem; }}
  .cf-stepper .now {{ font-size: .95rem; color: {INK}; margin-bottom: .7rem; }}
  .cf-stepper .now b {{ color: {NAVY}; }}
  .cf-stepper .track {{ display: flex; align-items: flex-start; }}
  .cf-stepper .seg {{ flex: 1; position: relative; text-align: center; min-width: 0; }}
  .cf-stepper .seg::before {{ content: ""; position: absolute; top: 14px; left: -50%; width: 100%;
                             height: 2px; background: {BORDER}; z-index: 0; }}
  .cf-stepper .seg:first-child::before {{ display: none; }}
  .cf-stepper .seg.done::before, .cf-stepper .seg.current::before {{ background: {TEAL}; }}
  .cf-stepper .dot {{ position: relative; z-index: 1; width: 30px; height: 30px; margin: 0 auto;
                     border-radius: 50%; display: flex; align-items: center; justify-content: center;
                     font-size: .85rem; font-weight: 700; background: {CARD};
                     border: 2px solid #CBD5E1; color: {MUTED}; box-sizing: border-box; }}
  .cf-stepper .seg.done .dot {{ background: {TEAL}; border-color: {TEAL}; color: #FFFFFF; }}
  .cf-stepper .seg.current .dot {{ background: {NAVY}; border-color: {NAVY}; color: #FFFFFF; }}
  .cf-stepper .seg.skipped .dot {{ background: #F3F4F6; border-color: #D1D5DB; color: #9CA3AF; }}
  .cf-stepper .name {{ font-size: .74rem; color: {MUTED}; margin-top: .35rem; padding: 0 .2rem; }}
  .cf-stepper .seg.done .name {{ color: {TEAL}; }}
  .cf-stepper .seg.current .name {{ color: {NAVY}; font-weight: 700; }}
  .cf-stepper .seg.skipped .name {{ text-decoration: line-through; color: #9CA3AF; }}

  .cf-tip {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS};
            padding: .9rem 1rem; font-size: .88rem; color: {INK}; }}
  .cf-tip b {{ color: {NAVY}; }}

  @media (max-width: 640px) {{
    [data-testid="stMainBlockContainer"] {{ padding-top: 1rem; }}
    .cf-band {{ padding: .8rem 1rem; }}
    .cf-band .title {{ font-size: 1.2rem; }}
    .cf-stepper .name {{ display: none; }}
    .cf-stepper .seg.current .name {{ display: block; }}
    .cf-stepper .dot {{ width: 26px; height: 26px; font-size: .78rem; }}
    .cf-stepper .seg::before {{ top: 12px; }}
    .cf-table .hide-sm {{ display: none; }}
    .cf-item .conf {{ text-align: left; min-width: 0; }}
    .cf-item .main {{ flex-basis: 100%; order: 2; }}
    .cf-status .label {{ font-size: 1.45rem; }}
    .cf-kfs {{ grid-template-columns: 1fr; }}
  }}
</style>
"""
