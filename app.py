"""
app.py - Streamlit entry point for CashFlow IQ.

Run locally:   streamlit run app.py

This file only sets up the page, shared session state, styling and navigation.
Each page lives in views/ ; all reasoning lives in engine/ + knowledge_base/.
"""
import streamlit as st

from knowledge_base.rules import RULES
from ui.components import (
    enable_enter_navigation, footer, init_state, inject_css, thresholds_modified,
)

st.set_page_config(page_title="CashFlow IQ", page_icon=":material/account_balance:",
                   layout="wide")
init_state()
inject_css()
enable_enter_navigation()        # Enter moves to the next box / presses Next

pages = {
    "For business owners": [
        st.Page("views/consultation.py", title="Consultation", default=True),
        st.Page("views/quick_diagnosis.py", title="Quick Diagnosis"),
    ],
    "For experts": [
        st.Page("views/knowledge_base.py", title="Knowledge Base"),
        st.Page("views/admin.py", title="Knowledge Acquisition"),
    ],
    "Info": [
        st.Page("views/about.py", title="About"),
    ],
}
navigation = st.navigation(pages)

with st.sidebar:
    st.markdown("### CashFlow IQ")
    st.caption("Business liquidity & cash flow decision expert system")
    st.caption(f"{len(RULES)} rules · forward chaining · certainty factors")
    if thresholds_modified():
        st.caption(":orange[Custom thresholds are active for this session.]")

navigation.run()
footer()
