"""Smoke tests for the Streamlit app: every tool loads and page switching works in both modes.

Regression test for a crash where switching pages in Pro mode raised
``StreamlitAPIException``: ``st.switch_page`` clears query parameters, and the
Plain/Pro toggle used to be bound to ``?mode=``, which Streamlit refuses to clear.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")
PAGES = ["pricer", "greeks", "payoff", "surface", "validation", "methods"]


def _start(mode: str | None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    if mode:
        at.query_params["mode"] = mode
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


@pytest.mark.parametrize("target", PAGES)
@pytest.mark.parametrize("mode", ["Pro", None])
def test_switching_to_every_page_works_in_both_modes(target: str, mode: str | None) -> None:
    at = _start(mode)
    at.session_state["_goto"] = target  # what clicking a tool tab in the top bar does
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["nav_tool"] == target
    assert at.session_state["mode"] == ("Pro" if mode == "Pro" else "Plain English")


def test_shared_pro_link_opens_in_pro_mode() -> None:
    at = _start("Pro")
    assert at.session_state["mode"] == "Pro"
