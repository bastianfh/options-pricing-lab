"""Market data: load a real US stock, analyse its history and option chain, and send its numbers to the lab."""

from __future__ import annotations

import html
import math
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import norm

from app.content import t
from app.report import Report
from app.theme import palette, show, style_figure
from app.ui import apply_values, cells, explain, finish_page, is_pro, lbl, page_header, panel, panel_title, section, tx, upper
from app.data import FALLBACK_RATE, POPULAR, load_chain, load_expiries, load_history, load_risk_free
from marketdata import fetch, parse
from marketdata.parse import MarketDataError, PriceHistory
from pricing.historical import historical_volatility, log_returns, rolling_volatility, summarize

PERIOD_KEYS = ["6mo", "1y", "2y", "5y"]
DEFAULT = ("AAPL", "2y")
HV_WINDOWS = {"30D": 30, "90D": 90, "1Y": 365}


def _on_load() -> None:
    st.session_state["mk_applied"] = (st.session_state["mk_ticker"], st.session_state["mk_period"])


def _send_to_pricer(values: dict, label: str) -> None:
    apply_values(**values)
    st.session_state["mk_sent"] = label
    st.session_state["_goto"] = "pricer"


def _pct(x: float, digits: int = 1) -> str:
    return "–" if x is None or not math.isfinite(x) else f"{100 * x:.{digits}f}%".replace("-", "−")


def _money(x: float) -> str:
    return "–" if x is None or not math.isfinite(x) else f"${x:,.2f}"


def _hv(hist: PriceHistory, days: int) -> float:
    try:
        return historical_volatility(hist.window(days))
    except ValueError:
        return float("nan")


# --------------------------------------------------------------------------- layout

report = Report(title=t("mk.report_title"))
actions = page_header("mk.title", "mk.lede", page="market", report=report)
st.session_state.setdefault("mk_ticker", DEFAULT[0])
st.session_state.setdefault("mk_period", DEFAULT[1])
st.session_state.setdefault("mk_applied", DEFAULT)

left, right = st.columns([1, 3.1], gap="small")
with left, panel("market_inputs"):
    panel_title(tx("mk.source"))
    source = st.segmented_control(
        lbl("mk.source"), ["ticker", "upload"], format_func=lambda v: upper(tx(f"mk.source.{v}")),
        key="mk_source", default="ticker", required=True, label_visibility="collapsed",
        persist_state="session", width="stretch",
    )
    uploaded = None
    if source == "ticker":
        options = POPULAR if st.session_state["mk_ticker"] in POPULAR else [st.session_state["mk_ticker"], *POPULAR]
        st.selectbox(lbl("mk.ticker"), options, key="mk_ticker", accept_new_options=True,
                     help=tx("mk.ticker.help"), persist_state="session")
        st.segmented_control(
            lbl("mk.period"), PERIOD_KEYS, format_func=lambda k: k.upper(), key="mk_period",
            required=True, persist_state="session", width="stretch",
        )
        st.button(upper(t("mk.load")), key="mk_load", type="primary", on_click=_on_load, width="stretch")
    else:
        uploaded = st.file_uploader(lbl("mk.upload"), type=["csv"], key="mk_upload", help=t("mk.upload.help"))
        template = pd.DataFrame({
            "Date": pd.bdate_range(end=date.today(), periods=5).strftime("%Y-%m-%d"),
            "Close": [100.0, 101.2, 100.7, 102.3, 103.1],
            "Dividends": [0.0, 0.0, 0.25, 0.0, 0.0],
        })
        st.download_button(upper(t("mk.upload.sample")), template.to_csv(index=False), "price_history_template.csv",
                           "text/csv", key="mk_template")

# --------------------------------------------------------------------------- load data

hist: PriceHistory | None = None
error = None
if source == "ticker":
    ticker, period = st.session_state["mk_applied"]
    try:
        with st.spinner(t("mk.loading", ticker=str(ticker).upper())):
            hist = load_history(str(ticker), period)
    except MarketDataError as exc:
        error = str(exc)
elif uploaded is not None:
    try:
        hist = parse.parse_price_csv(uploaded.getvalue(), uploaded.name.rsplit(".", 1)[0].upper())
    except MarketDataError as exc:
        error = str(exc)

with right:
    if error:
        st.error(error)
    if hist is None:
        if not error:
            st.info(t("mk.empty"))
        st.stop()

    rate = load_risk_free() if hist.source == "Yahoo Finance" else None
    r = rate if rate is not None else FALLBACK_RATE
    q = hist.dividend_yield
    hv = {name: _hv(hist, days) for name, days in HV_WINDOWS.items()}
    last_year = hist.close[hist.dates >= hist.dates[-1] - pd.Timedelta(days=365)]
    change = hist.close[-1] / hist.close[-2] - 1.0
    p = palette()

    # ------------------------------------------------------------------ snapshot
    section(tx("mk.snapshot"))
    st.html(cells([
        (tx("mk.last"), _money(hist.last_price), hist.last_date.strftime("%d %b %Y").upper(), "acc"),
        (tx("mk.change"), _pct(change, 2), "", "pos" if change > 0 else ("neg" if change < 0 else "")),
        (t("mk.range"), f"{_money(last_year.min())} – {_money(last_year.max())}", "", ""),
        (tx("mk.yield"), _pct(q, 2), "", ""),
        (tx("mk.hv", w="30D"), _pct(hv["30D"]), "", "vol"),
        (tx("mk.hv", w="90D"), _pct(hv["90D"]), "", "vol"),
        (tx("mk.hv", w="1Y"), _pct(hv["1Y"]), "", "vol"),
        (tx("mk.rf"), _pct(rate, 2) if rate is not None else t("mk.rf_na"), "", ""),
    ], columns=4))
    if not is_pro():
        explain(t("mk.explain", ticker=hist.label, price=_money(hist.last_price), hv1y=hv["1Y"] if
                  math.isfinite(hv["1Y"]) else 0.0, hv30=hv["30D"] if math.isfinite(hv["30D"]) else 0.0, q=q))
    st.html(f'<p class="opl-note">{html.escape(t("mk.source_note", source=hist.source, date=hist.last_date))}</p>')

    # ------------------------------------------------------------- option chain
    chain = pd.DataFrame()
    expiry = None
    expiries: list[str] = []
    if hist.source == "Yahoo Finance":
        try:
            expiries = load_expiries(hist.label)
        except MarketDataError as exc:
            st.warning(str(exc))
        if expiries:
            target = date.fromordinal(hist.last_date.toordinal() + 30)
            default_exp = min(expiries, key=lambda e: abs((fetch.expiry_date(e) - target).days))
            if st.session_state.get("mk_expiry") not in expiries:
                st.session_state["mk_expiry"] = default_exp
            expiry = st.session_state["mk_expiry"]
            try:
                calls, puts = load_chain(hist.label, expiry)
                chain = parse.clean_chain(calls, puts, hist.last_price, fetch.expiry_date(expiry),
                                          hist.last_date, r, q)
            except MarketDataError as exc:
                st.warning(str(exc))
    atm_iv = parse.atm_implied_vol(chain, hist.last_price) if len(chain) else float("nan")
    report.subtitle = f"{hist.label}, {len(hist.dates)} trading days to {hist.last_date}"
    report.data_source = f"{hist.source}, daily prices and dividends for {hist.label} up to {hist.last_date}."
    report.metrics(t("mk.snapshot", "Pro"), [
        (t("mk.last", "Pro"), _money(hist.last_price)), (t("mk.range"), f"{_money(last_year.min())} - {_money(last_year.max())}"),
        (t("mk.yield", "Pro"), _pct(q, 2)), (t("mk.rf", "Pro"), _pct(rate, 2) if rate is not None else "n/a"),
        (t("mk.hv", "Pro", w="30D"), _pct(hv["30D"])), (t("mk.hv", "Pro", w="90D"), _pct(hv["90D"])),
        (t("mk.hv", "Pro", w="1Y"), _pct(hv["1Y"])), ("ATM implied vol", _pct(atm_iv) if math.isfinite(atm_iv) else "n/a"),
    ])

    # -------------------------------------------------------- send to the lab
    section(tx("mk.send.title"), tx("mk.send.lede"))
    sigma_options = list(HV_WINDOWS) + (["ATM"] if math.isfinite(atm_iv) else [])
    sigma_values = {**hv, "ATM": atm_iv}
    with st.container(horizontal=True, vertical_alignment="bottom", gap="small", key="mk_send_row"):
        choice = st.segmented_control(
            lbl("mk.send.sigma"), sigma_options,
            format_func=lambda k: (upper(tx("mk.send.atm_iv")) if k == "ATM" else f"{k}") + f"  {_pct(sigma_values[k])}",
            key="mk_sigma", default="1Y", required=True, help=tx("mk.send.sigma.help"),
        )
        sigma = sigma_values.get(choice or "1Y", hv["1Y"])
        spot = hist.last_price
        strike = round(spot) if spot >= 25 else round(spot * 2) / 2
        values = dict(asset="stock", option_type=st.session_state.get("in_option_type", "call"), S=round(spot, 2),
                      K=float(strike), vol=round(100 * sigma, 2) if math.isfinite(sigma) else 20.0,
                      q=round(100 * q, 3), r=round(100 * r, 3))
        st.button(upper(tx("mk.send.button")), key="mk_send", type="primary", on_click=_send_to_pricer,
                  args=(values, hist.label))

    # ------------------------------------------------------------- price history
    section(tx("mk.history.title"))
    adj = pd.Series(hist.adj_close, index=hist.dates)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.dates, y=hist.adj_close, name=tx("mk.history.close"),
                             line=dict(color=p.accent, width=1.6), hovertemplate="%{y:,.2f}"))
    for window, label, color, dash in ((50, t("mk.history.ma50"), p.label, "dash"), (200, t("mk.history.ma200"), p.vol, "dot")):
        if len(adj) > window:
            fig.add_trace(go.Scatter(x=hist.dates, y=adj.rolling(window).mean(), name=label,
                                     line=dict(color=color, width=1.2, dash=dash), hovertemplate="%{y:,.2f}"))
    style_figure(fig, height=330, y_title=tx("mk.history.y"))
    show(fig, key="mk_history_chart")
    report.figure(t("mk.history.title", "Pro"), fig)


    # ------------------------------------------------------------- volatility
    section(tx("mk.vol.title"), tx("mk.vol.lede"))
    fig = go.Figure()
    for window, color, dash in ((21, p.vol, "solid"), (63, p.vol_ramp[1], "dash")):
        if len(hist.adj_close) > window + 1:
            fig.add_trace(go.Scatter(x=hist.dates, y=100 * rolling_volatility(hist.adj_close, window),
                                     name=f"{window}D", line=dict(color=color, width=1.6, dash=dash),
                                     hovertemplate="%{y:.1f}%"))
    if math.isfinite(atm_iv):
        fig.add_hline(y=100 * atm_iv, line=dict(color=p.accent, width=1, dash="dash"),
                      annotation_text=f"{upper(tx('mk.vol.atm'))} {_pct(atm_iv)}", annotation_position="top left",
                      annotation_font=dict(size=10, color=p.accent))
    style_figure(fig, height=300, y_title=tx("mk.vol.y"))
    show(fig, key="mk_vol_chart")
    report.figure(t("mk.vol.title", "Pro"), fig)


    # ------------------------------------------------------------- returns
    section(tx("mk.returns.title"), tx("mk.returns.lede"))
    rets = log_returns(hist.adj_close)
    summary = summarize(hist.adj_close, risk_free=r)
    c1, c2 = st.columns([1.6, 1], gap="small")
    with c1:
        grid = np.linspace(rets.min(), rets.max(), 300)
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=100 * rets, histnorm="probability density", nbinsx=80,
                                   name=tx("mk.returns.actual"), marker=dict(color=p.accent, line=dict(width=0)),
                                   opacity=0.75, hovertemplate="%{x:.2f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=100 * grid, y=norm.pdf(grid, rets.mean(), rets.std(ddof=1)) / 100,
                                 name=tx("mk.returns.normal"), line=dict(color=p.ink, width=1.4, dash="dash"),
                                 hoverinfo="skip"))
        fig.update_layout(bargap=0.04)
        style_figure(fig, height=300, x_title=tx("mk.returns.x"), y_title=tx("mk.returns.y"), hovermode="closest")
        show(fig, key="mk_returns_chart")
        report.figure(t("mk.returns.title", "Pro"), fig)

    with c2:
        st.html(cells([
            (tx("mk.stat.return"), _pct(summary.annual_return), "", "pos" if summary.annual_return > 0 else "neg"),
            (tx("mk.stat.vol"), _pct(summary.annual_volatility), "", "vol"),
            (tx("mk.stat.sharpe"), f"{summary.sharpe:.2f}", "", ""),
            (tx("mk.stat.drawdown"), _pct(-summary.max_drawdown), "", "neg"),
            (tx("mk.stat.skew"), f"{summary.skewness:+.2f}".replace("-", "−"), "", ""),
            (tx("mk.stat.kurt"), f"{summary.excess_kurtosis:+.2f}".replace("-", "−"), "", ""),
            (tx("mk.stat.worst"), _pct(summary.worst_day), "", "neg"),
            (tx("mk.stat.best"), _pct(summary.best_day), "", "pos"),
        ], columns=2))
    report.metrics(t("mk.returns.title", "Pro"), [
        (t("mk.stat.return", "Pro"), _pct(summary.annual_return)), (t("mk.stat.vol", "Pro"), _pct(summary.annual_volatility)),
        (t("mk.stat.sharpe", "Pro"), f"{summary.sharpe:.2f}"), (t("mk.stat.drawdown", "Pro"), _pct(-summary.max_drawdown)),
        (t("mk.stat.skew", "Pro"), f"{summary.skewness:+.2f}"), (t("mk.stat.kurt", "Pro"), f"{summary.excess_kurtosis:+.2f}"),
        (t("mk.stat.worst", "Pro"), _pct(summary.worst_day)), (t("mk.stat.best", "Pro"), _pct(summary.best_day)),
    ])

    # ------------------------------------------------------------- option chain
    section(tx("mk.chain.title"), tx("mk.chain.lede"))
    if hist.source != "Yahoo Finance":
        st.html(f'<p class="opl-note">{html.escape(t("mk.chain.only_live"))}</p>')
        st.stop()
    if not expiries:
        st.html(f'<p class="opl-note">{html.escape(t("mk.chain.none"))}</p>')
        st.stop()
    with st.container(horizontal=True, vertical_alignment="bottom", gap="small", key="mk_chain_row"):
        st.selectbox(lbl("mk.chain.expiry"), expiries, key="mk_expiry", width=220)
        build = st.button(upper(tx("mk.chain.surface")), key="mk_build_surface", help=t("mk.chain.surface.help"))

    if len(chain):
        fig = go.Figure()
        for kind, color, symbol in (("call", p.positive, "square"), ("put", p.negative, "diamond")):
            part = chain[chain["type"] == kind]
            fig.add_trace(go.Scatter(x=part["strike"], y=100 * part["iv"], mode="markers+lines",
                                     name=f"{upper(tx('mk.chain.ours'))} {kind.upper()}",
                                     line=dict(color=color, width=1), marker=dict(size=6, symbol=symbol, color=color),
                                     hovertemplate="K %{x}: %{y:.1f}%"))
        fig.add_trace(go.Scatter(x=chain["strike"], y=100 * chain["yahoo_iv"], mode="markers",
                                 name=upper(t("mk.chain.yahoo")), marker=dict(size=5, symbol="x-thin", color=p.label,
                                                                             line=dict(width=1, color=p.label)),
                                 hovertemplate="K %{x}: %{y:.1f}%"))
        fig.add_vline(x=hist.last_price, line=dict(color=p.accent, width=1, dash="dash"),
                      annotation_text="S", annotation_font=dict(size=10, color=p.accent))
        style_figure(fig, height=320, x_title=tx("mk.chain.x"), y_title=tx("mk.chain.y"), hovermode="closest")
        show(fig, key="mk_chain_chart")
        report.figure(t("mk.chain.title", "Pro") + f" ({expiry})", fig)


        table = chain.assign(iv=chain["iv"] * 100, yahoo_iv=chain["yahoo_iv"] * 100)[
            ["type", "strike", "bid", "ask", "price", "iv", "yahoo_iv", "volume", "open_interest"]
        ]
        st.dataframe(table, hide_index=True, width="stretch", height=280, column_config={
            "type": st.column_config.TextColumn(t("mk.col.type")),
            "strike": st.column_config.NumberColumn(t("mk.col.strike"), format="%.2f"),
            "bid": st.column_config.NumberColumn(t("mk.col.bid"), format="%.2f"),
            "ask": st.column_config.NumberColumn(t("mk.col.ask"), format="%.2f"),
            "price": st.column_config.NumberColumn(t("mk.col.price"), format="%.3f"),
            "iv": st.column_config.NumberColumn(t("mk.col.iv"), format="%.1f%%"),
            "yahoo_iv": st.column_config.NumberColumn(t("mk.col.yahoo_iv"), format="%.1f%%"),
            "volume": st.column_config.NumberColumn(t("mk.col.volume"), format="%d"),
            "open_interest": st.column_config.NumberColumn(t("mk.col.oi"), format="%d"),
        })
        report.table(t("mk.chain.title", "Pro") + f" ({expiry})", table)

    if build:
        horizon = [e for e in expiries if 7 <= (fetch.expiry_date(e) - hist.last_date).days <= 400]
        picks = [horizon[i] for i in np.unique(np.linspace(0, len(horizon) - 1, min(8, len(horizon))).astype(int))] if horizon else []
        chains = []
        with st.spinner(t("mk.chain.building", n=len(picks))):
            for e in picks:
                try:
                    c, pt = load_chain(hist.label, e)
                except MarketDataError:
                    continue
                chains.append(parse.clean_chain(c, pt, hist.last_price, fetch.expiry_date(e), hist.last_date, r, q))
        usable = [c for c in chains if len(c)]
        if usable:
            quotes = pd.concat(usable, ignore_index=True)[["strike", "years", "iv", "type", "price"]]
            st.session_state["mk_surface"] = dict(
                ticker=hist.label, date=str(hist.last_date), S=hist.last_price, r=r, q=q,
                quotes=quotes.to_dict("list"), expiries=len(usable),
            )
            st.session_state["_goto"] = "surface"
            st.rerun()

finish_page(actions)
