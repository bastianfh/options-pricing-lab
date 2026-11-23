"""Shareable links and downloadable reports."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from app.report import Report, build_html
from app.share import ALL_PARAMS, PAGE_PARAMS

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def test_param_names_are_unique_per_page() -> None:
    from app.share import COMMON

    for page, params in PAGE_PARAMS.items():
        names = [p.name for p in COMMON + params]
        assert len(names) == len(set(names)), page


@pytest.mark.parametrize(
    "name,raw,expected",
    [("S", "352.78", 352.78), ("days", "45", 45), ("live", "1", True), ("bt", "iron_condor", "iron_condor"),
     ("ticker", "brk.b", "BRK-B"), ("from", "2024-01-31", "2024-01-31")],
)
def test_params_cast_valid_values(name: str, raw: str, expected: object) -> None:
    param = next(p for p in ALL_PARAMS if p.name == name)
    assert param.cast(raw) == expected


@pytest.mark.parametrize(
    "name,raw",
    [("S", "-5"), ("days", "99999"), ("live", "yes"), ("bt", "martingale"), ("ticker", "AAPL;DROP"),
     ("from", "not-a-date"), ("vol", "nan-ish"), ("legs", "c+1"), ("legs", "x+1@100"), ("name", ""),
     ("name", "x" * 41)],
)
def test_params_reject_bad_values(name: str, raw: str) -> None:
    param = next(p for p in ALL_PARAMS if p.name == name)
    with pytest.raises((ValueError, TypeError)):
        param.cast(raw)


def test_shared_link_settings_are_applied_and_bad_ones_ignored() -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in {"guide": "off", "S": "123.5", "vol": "31", "type": "put", "days": "-4", "a": "crypto"}.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["in_S"] == 123.5 and at.session_state["in_vol"] == 31.0
    assert at.session_state["in_option_type"] == "put"
    assert at.session_state["in_days"] == 182        # out of range -> default kept
    assert at.session_state["in_asset"] == "stock"   # unknown choice -> default kept


def test_share_url_round_trips_through_the_app() -> None:
    from app.share import share_url

    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["guide"] = "off"
    at.query_params["K"] = "105"
    at.run()
    state = {p.key: at.session_state[p.key] for p in ALL_PARAMS if p.key in at.session_state}

    import streamlit as st

    for key, value in state.items():
        st.session_state[key] = value
    try:
        url = share_url("pricer", base_url="https://example.app/")
    finally:
        for key in state:
            del st.session_state[key]
    parts = urlsplit(url)
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    assert parts.scheme == "https" and parts.netloc == "example.app" and parts.path == "/"
    assert query["K"] == "105" and query["guide"] == "off"


def test_report_html_contains_every_section_and_works_offline() -> None:
    r = Report(title="Strategy backtest", subtitle="Covered call on KO")
    r.params("Setup", {"Ticker": "KO", "Tenor": 30})
    r.metrics("Results", [("Total return", "+12.3%"), ("Sharpe", "0.81")])
    r.figure("Equity curve", go.Figure(go.Scatter(x=[1, 2, 3], y=[100, 101, 103])))
    r.table("Trades", pd.DataFrame({"pnl": np.arange(600.0)}), max_rows=50)
    r.text("Method", "Line one.\nLine two.")
    r.share_link = "https://example.app/backtest?bt=covered_call"
    r.data_source = "Yahoo Finance"
    doc = build_html(r)
    for needle in ("Strategy backtest", "Covered call on KO", "Ticker", "+12.3%", "Equity curve",
                   "First 50 of 600 rows", "Line two.", "bt=covered_call", "Yahoo Finance", "How to cite"):
        assert needle in doc, needle
    assert "<script>" not in r.title  # titles are escaped


def _report_with_charts(n: int = 2) -> Report:
    r = Report(title="Strategy backtest")
    for i in range(n):
        r.figure(f"Chart {i}", go.Figure(go.Scatter(x=[1, 2, 3], y=[100, 101 + i, 103])))
    return r


def test_report_charts_are_pictures_that_need_no_javascript(monkeypatch: pytest.MonkeyPatch) -> None:
    """Previews (phone file apps, email, Drive) don't run JavaScript, so charts are embedded as images."""
    import app.report as report_module

    monkeypatch.setattr(report_module, "chart_png", lambda fig: b"\x89PNG fake")
    doc = build_html(_report_with_charts())
    assert doc.count("data:image/png;base64,") == 2
    assert "Plotly.newPlot" not in doc and len(doc) < 100_000  # no 4.5 MB plotly.js bundle needed


def test_report_falls_back_to_interactive_charts_with_a_visible_note(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.report as report_module

    monkeypatch.setattr(report_module, "chart_png", lambda fig: None)  # e.g. no Chromium on the machine
    doc = build_html(_report_with_charts())
    assert doc.count("Plotly.newPlot") == 2 and doc.count("This chart needs JavaScript") == 2
    # plotly.js is embedded once, not loaded from a CDN, so the report still works offline.
    assert "<script src=" not in doc and len(doc) > 1_000_000


def test_kaleido_draws_real_pngs_when_a_browser_is_available() -> None:
    from app.report import chart_png

    png = chart_png(go.Figure(go.Scatter(x=[1, 2, 3], y=[1, 3, 2])))
    if png is None:
        pytest.skip("no headless Chromium on this machine")
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 5_000


def test_report_escapes_user_text() -> None:
    r = Report(title="<script>alert(1)</script>")
    r.params("Setup", {"<b>": "<img src=x onerror=alert(1)>"})
    doc = build_html(r)
    assert "<script>alert(1)</script>" not in doc and "<img src=x" not in doc


def test_custom_backtest_link_carries_its_legs() -> None:
    from app.share import share_url

    import streamlit as st

    param = next(p for p in ALL_PARAMS if p.name == "legs")
    assert param.cast("s+1, c-1@105.0") == "s+1,c-1@105"
    state = {"bt_strategy": "custom", "bt_legs": "s+1,c-1@105", "bt_name": "My collar"}
    for key, value in state.items():
        st.session_state[key] = value
    try:
        query = parse_qs(urlsplit(share_url("backtest", base_url="https://example.app/")).query)
        st.session_state["bt_strategy"] = "covered_call"
        plain = parse_qs(urlsplit(share_url("backtest", base_url="https://example.app/")).query)
    finally:
        for key in state:
            del st.session_state[key]
    assert query["bt"] == ["custom"] and query["legs"] == ["s+1,c-1@105"] and query["name"] == ["My collar"]
    assert "legs" not in plain and "name" not in plain


def test_comparison_lists_round_trip_and_reject_bad_input() -> None:
    from app.share import decode_compare, encode_compare

    entries = decode_compare("s+1,c-1@105~30~0~0~Covered call|c-1@105,p-1@95~45~0.5~2~Short strangle")
    assert entries[1] == dict(legs="c-1@105,p-1@95", tenor=45, tp=0.5, sl=2.0, name="Short strangle")
    assert entries[0]["tp"] is None and entries[0]["sl"] is None
    assert decode_compare(encode_compare(entries)) == entries
    for bad in ["s+1~30~0~0", "x+1~30~0~0~A", "s+1~0~0~0~A", "s+1~30~-1~0~A", "|".join(["s+1~30~0~0~A"] * 5)]:
        with pytest.raises((ValueError, TypeError)):
            decode_compare(bad)
    assert encode_compare([dict(legs="s+1", tenor=30, tp=None, sl=None, name="A|B~C")]) == "s+1~30~0~0~A B C"
