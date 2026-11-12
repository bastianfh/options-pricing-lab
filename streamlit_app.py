"""Options Pricing Lab: Streamlit entry point.

Run locally with ``streamlit run streamlit_app.py``. Streamlit Community Cloud
picks this file up by default.

This file sets up the page, theme CSS and the custom sidebar (mode toggle
first, then page links), then hands over to the selected page in ``app/pages``.
"""

from __future__ import annotations

import streamlit as st

from app.content import t
from app.ui import handle_navigation, init_state, inject_css, render_sidebar

st.set_page_config(
    page_title=t("app.name"),
    page_icon=":material/candlestick_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "home": st.Page("app/pages/home.py", title=t("nav.home"), icon=":material/home:", default=True),
    "pricer": st.Page("app/pages/pricer.py", title=t("nav.pricer"), icon=":material/calculate:", url_path="pricer"),
    "greeks": st.Page("app/pages/greeks.py", title=t("nav.greeks"), icon=":material/ssid_chart:", url_path="greeks"),
    "payoff": st.Page("app/pages/payoff.py", title=t("nav.payoff"), icon=":material/stacked_line_chart:", url_path="payoff"),
    "surface": st.Page("app/pages/surface.py", title=t("nav.surface"), icon=":material/3d_rotation:", url_path="surface"),
    "validation": st.Page("app/pages/validation.py", title=t("nav.validation"), icon=":material/verified:", url_path="validation"),
    "methods": st.Page("app/pages/methods.py", title=t("nav.methods"), icon=":material/menu_book:", url_path="methods"),
}
st.session_state["_pages"] = PAGES

init_state()
navigation = st.navigation(list(PAGES.values()), position="hidden")
inject_css()
render_sidebar(PAGES)
handle_navigation(PAGES)
navigation.run()
