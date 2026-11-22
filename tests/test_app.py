"""Smoke tests for the Streamlit app: every tool loads and page switching works in both modes.

Regression test for a crash where switching pages in Pro mode raised
``StreamlitAPIException``: ``st.switch_page`` clears query parameters, and the
Plain/Pro toggle used to be bound to ``?mode=``, which Streamlit refuses to clear.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.test_marketdata import FakeTicker

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")
PAGES = ["pricer", "market", "greeks", "payoff", "surface", "validation", "methods"]


@pytest.fixture(autouse=True)
def offline_market_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never call Yahoo Finance from tests: the Market page gets a fake yfinance with synthetic data."""
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker))
    st.cache_data.clear()


def _start(mode: str | None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["guide"] = "off"  # keep the first-run guide out of the navigation tests
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


def test_first_run_guide_opens_and_walks_through_every_step() -> None:
    """A first-time visitor (no cookie) gets the guide; clicking through every step closes it cleanly."""
    from app.guide import STEPS

    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["guide_active"] is True

    for expected_step in range(1, len(STEPS)):
        at.button(key="guide_next").click().run()
        assert not at.exception, [e.message for e in at.exception]
        assert at.session_state["guide_step"] == expected_step

    at.button(key="guide_finish").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["guide_active"] is False


def test_guide_can_be_skipped_and_reopened() -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.button(key="guide_skip").click().run()
    assert at.session_state["guide_active"] is False
    at.button(key="guide_btn").click().run()  # GUIDE in the top bar
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["guide_active"] is True and at.session_state["guide_step"] == 0


def test_market_page_sends_real_numbers_to_the_pricer() -> None:
    at = _start(None)
    at.session_state["_goto"] = "market"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    at.button(key="mk_send").click().run()
    at.run()  # follow the page switch requested by the button
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["nav_tool"] == "pricer"
    assert at.session_state["mk_sent"] == "AAPL"
    assert at.session_state["in_asset"] == "stock" and at.session_state["in_r"] == pytest.approx(100 * 0.040420, abs=1e-3)


def test_market_option_chain_builds_a_surface() -> None:
    at = _start("Pro")
    at.session_state["_goto"] = "market"
    at.run()
    at.button(key="mk_build_surface").click().run()
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["nav_tool"] == "surface"
    assert at.session_state["mk_surface"]["ticker"] == "AAPL"
    assert at.session_state["vs_source"] == "market"


# Note: Streamlit's AppTest cannot re-run a page whose select boxes use format_func (it fails while
# serialising their state), so these tests set widget state before a single run instead of clicking.

@pytest.mark.parametrize("strategy", ["covered_call", "collar", "iron_condor", "long_straddle", "buy_and_hold"])
def test_backtest_page_runs_every_kind_of_strategy(strategy: str) -> None:
    at = _start("Pro")
    at.session_state["bt_strategy"] = strategy
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["nav_tool"] == "backtest"
    assert at.session_state["bt_start"] and at.session_state["bt_end"]  # range recorded for share links


def test_payoff_live_chain_mode_is_off_by_default() -> None:
    at = _start(None)
    at.session_state["_goto"] = "payoff"
    at.run()
    assert not at.exception and at.session_state["pay_live"] is False


@pytest.mark.parametrize("strategy", ["bull_call_spread", "covered_call", "straddle"])
def test_payoff_live_chain_mode_prices_legs_from_quotes(strategy: str) -> None:
    at = _start("Pro")
    at.session_state["pay_live"] = True
    at.session_state["pay_strategy"] = strategy
    at.session_state["_goto"] = "payoff"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["pay_expiry"] in ("2026-12-18", "2027-01-15")


@pytest.mark.parametrize("legs", ["s+1,p+1@95,c-1@110", "c-1@105", "p+2@90,s+1", "c+1@100,c-2@105,c+1@110"])
def test_backtest_runs_a_custom_strategy(legs: str) -> None:
    at = _start("Pro")
    at.session_state["bt_strategy"] = "custom"
    at.session_state["bt_legs"] = legs
    at.session_state["bt_name"] = "My spread"
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["bt_legs"] == legs
    naked = legs == "c-1@105"
    assert any("no limit" in w.value for w in at.warning) == naked


def test_custom_strategy_without_saved_legs_starts_from_a_template() -> None:
    at = _start(None)
    at.session_state["bt_strategy"] = "custom"
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["bt_legs_seed"] == "s+1,c-1@105"


def test_backtest_template_leg_sizes_change_the_strategy() -> None:
    at = _start("Pro")
    at.session_state["bt_strategy"] = "long_straddle"
    at.session_state["bt_qty_long_straddle_0"] = 2.0  # two calls for every put: a strap
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["bt_qty"] == "2,1"  # recorded for share links
    assert [n.label for n in at.number_input if n.key.startswith("bt_qty_")] == ["BUY CALL", "BUY PUT"]


def test_shared_link_sizes_apply_to_the_linked_strategy() -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in {"guide": "off", "bt": "bull_call_spread", "qty": "1,2"}.items():
        at.query_params[k] = v
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["bt_qty_bull_call_spread_1"] == 2.0
    assert any("no limit" in w.value for w in at.warning)  # a 1x2 call spread is short a naked call
