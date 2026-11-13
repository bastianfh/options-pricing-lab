"""Options Pricing Lab: Streamlit entry point.

Run locally with ``streamlit run streamlit_app.py``. Streamlit Community Cloud
picks this file up by default.

The app is laid out as one instrument: a telemetry bar across the top (tool
tabs, live parameter readout, Plain/Pro switch), then the selected tool from
``app/pages``. It opens straight into the Pricer.
"""

from __future__ import annotations

import streamlit as st

from app.content import t
from app.ui import handle_navigation, init_state, inject_css, render_topbar, reset_module_index

st.set_page_config(page_title=t("app.name"), layout="wide", initial_sidebar_state="collapsed")

PAGES = {
    "pricer": st.Page("app/pages/pricer.py", title=t("nav.pricer"), default=True),
    "greeks": st.Page("app/pages/greeks.py", title=t("nav.greeks"), url_path="greeks"),
    "payoff": st.Page("app/pages/payoff.py", title=t("nav.payoff"), url_path="payoff"),
    "surface": st.Page("app/pages/surface.py", title=t("nav.surface"), url_path="surface"),
    "validation": st.Page("app/pages/validation.py", title=t("nav.validation"), url_path="validation"),
    "methods": st.Page("app/pages/methods.py", title=t("nav.methods"), url_path="methods"),
}

init_state()
navigation = st.navigation(list(PAGES.values()), position="hidden")
handle_navigation(PAGES)
current = next(key for key, page in PAGES.items() if page.title == navigation.title)
inject_css()
reset_module_index()
render_topbar(current)
navigation.run()
