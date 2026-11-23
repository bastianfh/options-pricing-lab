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
    at.query_params["mode"] = mode or "Plain"  # Simple is the default; these tests cover the full lab
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
    at.query_params["mode"] = "Plain"  # the guide tours the full lab
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
    at.query_params["mode"] = "Plain"
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


def test_backtest_exit_rules_are_off_by_default_and_work_when_enabled() -> None:
    at = _start(None)
    at.session_state["bt_strategy"] = "iron_condor"
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception and at.session_state["bt_exits"] is False
    assert not [n for n in at.number_input if n.key in ("bt_tp", "bt_sl")]  # hidden until switched on

    at = _start("Pro")
    at.session_state["bt_strategy"] = "iron_condor"
    at.session_state["bt_exits"] = True
    at.session_state["bt_tp"] = 50.0
    at.session_state["bt_sl"] = 200.0
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any("closed early" in str(h.proto) for h in at.get("html"))  # the exit summary line


COMPARE = "s+1,c-1@105~30~0~0~Covered call|s+1,p+1@95,c-1@105~30~0~0~Collar|p+1@90,p-1@95,c-1@105,c+1@110~30~0.5~2~Condor"


@pytest.mark.parametrize("mode", [None, "Pro"])
def test_backtest_compare_view_runs_every_strategy(mode: str | None) -> None:
    at = _start(mode)
    at.session_state["bt_cmp"] = COMPARE
    at.session_state["bt_view"] = "compare"
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    table = next(df for df in at.dataframe if "strategy" in df.value.columns)
    assert list(table.value["strategy"])[:3] == ["Covered call", "Collar", "Condor"]
    assert len(table.value) == 4  # plus buy & hold


def test_backtest_compare_view_without_strategies_explains_what_to_do() -> None:
    at = _start(None)
    at.session_state["bt_view"] = "compare"
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception
    assert any("Nothing to compare yet" in i.value for i in at.info)


def test_feedback_link_is_in_the_top_bar() -> None:
    at = _start(None)
    assert not at.exception
    from app.ui import DEFAULT_FEEDBACK_URL, feedback_url

    assert feedback_url() == DEFAULT_FEEDBACK_URL


def test_feedback_link_can_point_at_a_form(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ui import feedback_url

    monkeypatch.setenv("OPL_FEEDBACK_URL", "https://forms.gle/example")
    assert feedback_url() == "https://forms.gle/example"
    monkeypatch.setenv("OPL_FEEDBACK_URL", "javascript:alert(1)")
    assert feedback_url().startswith("https://github.com/")


# --------------------------------------------------------------------------- Simple mode

@pytest.mark.parametrize("direction", ["up", "down"])
def test_simple_price_screen_shows_the_essentials(direction: str) -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["mode"] = "Simple"
    at.session_state["sp_dir"] = direction
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    html_text = " ".join(str(h.proto) for h in at.get("html"))
    for label in ("COST", "BREAK-EVEN", "MOST YOU CAN LOSE", "MOST YOU CAN MAKE", "CHANCE OF PROFIT"):
        assert label in html_text
    assert ("UNLIMITED" in html_text) == (direction == "up")
    assert at.session_state["nav_tool"] == "pricer"
    assert not at.session_state.get("guide_active")  # the full-lab guide stays out of Simple mode


@pytest.mark.parametrize("strategy", ["covered_call", "iron_condor", "long_straddle"])
def test_simple_backtest_screen_runs(strategy: str) -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["mode"] = "Simple"
    at.session_state["sb_strategy"] = strategy
    at.session_state["_goto"] = "backtest"
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    html_text = " ".join(str(h.proto) for h in at.get("html"))
    for label in ("YOUR $10,000 BECAME", "JUST OWNING THE SHARES", "BIGGEST DROP", "RISK", "WINNING MONTHS"):
        assert label in html_text


def test_simple_mode_only_offers_the_two_simple_tools() -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["mode"] = "Simple"
    at.query_params["guide"] = "off"
    at.session_state["_goto"] = "greeks"  # an advanced tool: Simple mode sends you back to the price screen
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    nav = next(w for w in at.get("button_group") if w.key == "nav_tool")
    assert list(nav.proto.options) and len(nav.proto.options) == 2
    assert at.session_state["nav_tool"] == "pricer"


def test_simple_wording_falls_back_to_plain_english() -> None:
    from app.content import PLAIN, PRO, SIMPLE, t

    assert t("navshort.pricer", SIMPLE) == "Option price"
    assert t("navshort.pricer", PLAIN) == t("navshort.pricer", PRO) == "Pricer"
    assert t("bt.total_return", SIMPLE) == t("bt.total_return", PLAIN)


def test_simple_helpers() -> None:
    from app.simple import money, nice_strike, risk_level

    assert money(-1006.4) == "−$1,006" and money(41, signed=True) == "+$41" and money(0, signed=True) == "$0"
    assert nice_strike(349.08) == 350 and nice_strike(42.4) == 42
    assert risk_level(0.06, 0.08) == "low" and risk_level(0.15, 0.12) == "medium" and risk_level(0.12, 0.34) == "high"


def test_simple_is_the_default_for_a_plain_visit() -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["mode"] == "Simple"
    assert not at.session_state.get("guide_active")


@pytest.mark.parametrize("query, expected", [
    ({}, "Simple"), ({"guide": "off"}, "Simple"), ({"mode": "simple"}, "Simple"),
    ({"mode": "Plain"}, "Plain English"), ({"mode": "Plain English"}, "Plain English"), ({"mode": "pro"}, "Pro"),
    ({"bt": "collar", "guide": "off"}, "Plain English"),  # an older share link without a mode
    ({"K": "105"}, "Plain English"),
])
def test_mode_from_url(query: dict, expected: str) -> None:
    from app.ui import mode_from_url

    assert mode_from_url(query) == expected


@pytest.mark.parametrize("page", ["pricer", "backtest"])
def test_simple_screens_offer_a_report_and_chart_snapshots(page: str) -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["mode"] = "Simple"
    at.session_state["_goto"] = page
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any(getattr(w, "key", None) == "report_download" or "report" in str(w.proto).lower()
               for w in at.get("download_button"))
    charts = [c for c in at.get("plotly_chart")]
    assert charts and all('"toImage"' in c.proto.spec or "toImage" in str(c.proto) for c in charts)


def test_snapshot_names_are_safe() -> None:
    from app.theme import snapshot_name

    assert snapshot_name("AAPL", "call", "350", "1 month") == "AAPL-call-350-1-month"
    assert snapshot_name("BRK.B", "put", "", "1/2 year?") == "BRK.B-put-1-2-year"
