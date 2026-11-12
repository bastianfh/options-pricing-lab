"""Methods: a concise write-up of each model (plain summaries, or equations in Pro mode)."""

from __future__ import annotations

import html

import streamlit as st

from app.content import METHODS, t
from app.ui import card, is_pro, page_header, tx

page_header("methods.title", "methods.lede")

tabs = st.tabs([m["title"] for m in METHODS])
for tab, method in zip(tabs, METHODS):
    with tab, card(f"method_doc_{method['title'][:12].replace(' ', '_')}"):
        if is_pro():
            st.markdown(method["pro"])
        else:
            st.html(f'<p class="opl-method-plain">{html.escape(method["plain"])}</p>')
        st.html(f'<div class="opl-refs"><b>{html.escape(t("methods.references"))}:</b> '
                f'{html.escape(method["refs"]).replace("*", "")}</div>')
