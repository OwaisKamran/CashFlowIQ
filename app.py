"""Streamlit entry point: page setup, styling and navigation."""
import streamlit as st

from knowledge_base.rules import RULES
from ui.components import (
    enable_enter_navigation, footer, init_state, inject_css, thresholds_modified,
)

st.set_page_config(page_title="CashFlow IQ", page_icon=":material/account_balance:",
                   layout="wide")
init_state()
inject_css()
enable_enter_navigation()        # Enter moves to the next box

pages = {
    "For business owners": [
        st.Page("views/consultation.py", title="Consultation", icon=":material/assignment:", default=True),
        st.Page("views/quick_diagnosis.py", title="Quick Diagnosis", icon=":material/bolt:"),
    ],
    "For experts": [
        st.Page("views/knowledge_base.py", title="Knowledge Base", icon=":material/menu_book:"),
        st.Page("views/admin.py", title="Knowledge Acquisition", icon=":material/tune:"),
    ],
    "Info": [
        st.Page("views/about.py", title="About", icon=":material/info:"),
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
