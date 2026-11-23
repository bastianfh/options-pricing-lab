"""Simple mode: two stripped-down screens for complete beginners.

* **Option price**: pick a stock and a bet (up or down), see the cost, break-even, the most you
  can lose and make, the chance of profit, and a profit/loss chart.
* **Backtest**: pick a stock and a strategy, see what a starting amount became next to just
  owning the shares, the biggest drop, a risk level and winning months.

Everything technical (volatility, interest rate, dividends, costs, roll period, strikes) is
filled in automatically, using the same pricing engine and backtester as the full lab. All
wording lives in :mod:`app.content` under ``simple.*``.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.content import t
from app.data import POPULAR, dividends_on_dates, load_history, load_risk_free
from app.report import Report
from app.theme import palette, show, snapshot_name, style_figure
from app.ui import cells, lbl, page_header, panel, panel_title, section, upper
from marketdata import parse
from marketdata.parse import MarketDataError, PriceHistory
from pricing.backtest import BacktestConfig, performance, run_backtest, template_legs
from pricing.historical import historical_volatility
from pricing.models.black_scholes import black_scholes_price
from pricing.strategies import long_call, long_put, probability_of_profit

EXPIRIES = {"1w": 7, "1m": 30, "3m": 91, "6m": 182, "1y": 365}
MOVES = {"calm": 0.15, "normal": 0.30, "wild": 0.50}
PERIODS = ["1y", "2y", "5y", "10y"]
STRATEGIES = ["covered_call", "protective_put", "collar", "cash_secured_put", "long_straddle", "iron_condor"]
SCENARIOS = (-0.20, -0.10, 0.0, 0.10, 0.20)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def money(x: float, signed: bool = False, cents: bool = False) -> str:
    """$1,234 or −$1,234 (+$1,234 when ``signed``)."""
    body = f"${abs(x):,.2f}" if cents else f"${abs(x):,.0f}"
    if x < 0 and round(abs(x), 2 if cents else 0) > 0:
        return f"−{body}"
    return f"+{body}" if signed and x > 0 else body


def pct(x: float, signed: bool = True) -> str:
    if x is None or not math.isfinite(x):
        return "–"
    return (f"{100 * x:+.1f}%" if signed else f"{100 * abs(x):.1f}%").replace("-", "−")


def tone(x: float) -> str:
    if x is None or not math.isfinite(x) or abs(x) < 1e-12:
        return ""
    return "pos" if x > 0 else "neg"


def nice_strike(spot: float) -> float:
    """Round today's price to a strike that would be listed: $1 steps under $200, $5 above."""
    step = 1.0 if spot < 200 else 5.0
    return max(step, round(spot / step) * step)


def risk_level(annual_vol: float, max_drawdown: float) -> str:
    """Low / medium / high from yearly ups and downs and the biggest drop (whichever is worse)."""
    def level(x: float, lo: float, hi: float) -> int:
        return 0 if x < lo else (1 if x < hi else 2)

    vol = level(annual_vol if math.isfinite(annual_vol) else 1.0, 0.10, 0.20)
    drop = level(max_drawdown if math.isfinite(max_drawdown) else 1.0, 0.15, 0.30)
    return ("low", "medium", "high")[max(vol, drop)]


def _ticker_picker(key: str) -> str:
    s = st.session_state
    options = POPULAR if s[key] in POPULAR else [s[key], *POPULAR]
    st.selectbox(lbl("simple.ticker"), options, key=key, accept_new_options=True, label_visibility="collapsed")
    return str(s[key]).upper()


# ---------------------------------------------------------------------------
# Option price
# ---------------------------------------------------------------------------

def price_page() -> None:
    s = st.session_state
    s.setdefault("sp_ticker", s.get("mk_applied", ("AAPL", "2y"))[0])
    s.setdefault("sp_dir", "up")
    s.setdefault("sp_exp", "1m")
    s.setdefault("sp_contracts", 1)
    s.setdefault("sp_manual_price", 100.0)
    s.setdefault("sp_moves", "normal")

    report = Report(title=t("simple.report.price"))
    page_header("simple.price.title", "simple.price.lede", report=report)
    left, right = st.columns([1, 2.4], gap="small")
    with left, panel("sp_inputs"):
        panel_title(t("simple.stock"))
        ticker = _ticker_picker("sp_ticker")
        hist: PriceHistory | None = None
        try:
            with st.spinner(t("mk.loading", ticker=ticker)):
                hist = load_history(ticker, "1y")
            spot, sigma, q = hist.last_price, historical_volatility(hist.adj_close), hist.dividend_yield
        except (MarketDataError, ValueError):
            st.caption(t("simple.manual"))
            st.number_input(lbl("simple.manual.price"), 0.01, 1e6, step=1.0, format="%.2f", key="sp_manual_price")
            st.segmented_control(lbl("simple.manual.moves"), list(MOVES), key="sp_moves", required=True,
                                 format_func=lambda v: upper(t(f"simple.moves.{v}")), width="stretch")
            spot, sigma, q = float(s["sp_manual_price"]), MOVES[s["sp_moves"]], 0.0
        st.html(f'<p class="opl-note" style="margin:0">{t("simple.today", ticker=ticker)}: '
                f'<b>{money(spot, cents=True)}</b></p>')

        st.html('<div style="height:0.6rem"></div>')
        panel_title(t("simple.bet"))
        st.segmented_control(lbl("simple.bet"), ["up", "down"], key="sp_dir", required=True, width="stretch",
                             format_func=lambda v: upper(t(f"simple.bet.{v}")), label_visibility="collapsed")
        strike_key = f"sp_strike_{ticker}"
        s.setdefault(strike_key, nice_strike(spot))
        st.number_input(lbl("simple.strike"), 0.01, 1e6, step=1.0 if spot < 200 else 5.0, format="%.2f",
                        key=strike_key)
        st.segmented_control(lbl("simple.expiry"), list(EXPIRIES), key="sp_exp", required=True, width="stretch",
                             format_func=lambda v: upper(t(f"simple.exp.{v}")))
        st.number_input(lbl("simple.contracts"), 1, 1000, step=1, key="sp_contracts")

    call = s["sp_dir"] == "up"
    strike, n = float(s[strike_key]), int(s["sp_contracts"])
    days = EXPIRIES[s["sp_exp"]]
    T = days / 365.0
    rf = load_risk_free()
    r = rf if rf is not None else 0.04
    per_share = float(black_scholes_price(spot, strike, T, r, sigma, q, "call" if call else "put"))
    shares = 100 * n
    cost = per_share * shares
    breakeven = strike + per_share if call else strike - per_share
    chance = probability_of_profit((long_call if call else long_put)(strike), per_share, spot, T, r, sigma, q)
    p = palette()

    def pnl(at: np.ndarray) -> np.ndarray:
        payoff = np.maximum(at - strike, 0.0) if call else np.maximum(strike - at, 0.0)
        return (payoff - per_share) * shares

    with right:
        move = breakeven / spot - 1
        gain_cell = ((t("simple.max_gain"), upper(t("simple.unlimited")), upper(t("simple.max_gain.sub.call")), "pos")
                     if call else
                     (t("simple.max_gain"), money((strike - per_share) * shares), upper(t("simple.max_gain.sub.put",
                                                                                           ticker=ticker)), "pos"))
        st.html(cells([
            (t("simple.cost"), money(cost, cents=cost < 1000),
             upper(t("simple.cost.sub", per_share=f"{per_share:,.2f}", n=n)), "acc"),
            (t("simple.breakeven"), money(breakeven, cents=True),
             upper(t("simple.breakeven.sub", ticker=ticker, dir=t("simple.rise") if move >= 0 else t("simple.fall"),
                     pct=pct(move, signed=False))), ""),
            (t("simple.max_loss"), money(-cost, cents=cost < 1000),
             upper(t("simple.max_loss.sub", ticker=ticker, dir=t("simple.ends_below" if call else "simple.ends_above"),
                     strike=money(strike, cents=True))), "neg"),
            gain_cell,
            (t("simple.chance"), f"{100 * chance:.0f}%", upper(t("simple.chance.sub")), ""),
        ], columns=5, extra_class="opl-simple-grid"))

        section(t("simple.scenarios", ticker=ticker))
        ends = np.array([spot * (1 + m) for m in SCENARIOS])
        outcomes = pnl(ends)
        st.html(cells([
            (f"{pct(m) if m else '±0%'} · {money(e, cents=True)}", money(v, signed=True), "", tone(v))
            for m, e, v in zip(SCENARIOS, ends, outcomes)
        ], columns=len(SCENARIOS), extra_class="opl-simple-grid"))

        section(t("simple.chart"))
        lo, hi = min(spot, strike) * 0.6, max(spot, strike) * 1.4
        grid = np.linspace(lo, hi, 401)
        y = pnl(grid)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=grid, y=np.maximum(y, 0), fill="tozeroy", fillcolor=p.positive_fill,
                                 line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=grid, y=np.minimum(y, 0), fill="tozeroy", fillcolor=p.negative_fill,
                                 line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=grid, y=y, line=dict(color=p.ink, width=2), showlegend=False,
                                 hovertemplate="$%{x:,.2f}: %{y:+$,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=[breakeven], y=[0], mode="markers", showlegend=False,
                                 marker=dict(color=p.accent, size=9, symbol="diamond", line=dict(color=p.canvas, width=1.5)),
                                 hovertemplate=f"{t('simple.chart.breakeven')}: $%{{x:,.2f}}<extra></extra>"))
        fig.add_vline(x=spot, line=dict(color=p.accent, width=1, dash="dot"),
                      annotation_text=upper(t("simple.chart.today")), annotation_position="top right",
                      annotation_font_size=11)
        style_figure(fig, height=340, x_title=t("simple.chart.x", ticker=ticker), y_title=t("simple.chart.y"),
                     legend=False, hovermode="closest")
        fig.update_yaxes(tickformat="$,.0f")
        exp_name = t(f"simple.exp.{s['sp_exp']}")
        show(fig, key="sp_chart", snapshot=snapshot_name(ticker, "call" if call else "put", f"{strike:g}", exp_name))
        st.html(f'<p class="opl-note">{t("simple.price.note", ticker=ticker)}</p>')

    bet = t("simple.report.bet.up" if call else "simple.report.bet.down")
    report.subtitle = f"{ticker}: {bet.lower()}, strike {money(strike, cents=True)}, ends in {exp_name}"
    report.data_source = (f"{hist.source}, daily prices for {ticker} up to {hist.last_date}." if hist is not None
                          else t("simple.report.manual"))
    report.params(t("simple.report.setup"), {
        t("simple.report.stock"): ticker, t("simple.report.today"): money(spot, cents=True),
        t("simple.report.bet"): bet, t("simple.strike"): money(strike, cents=True),
        t("simple.expiry"): exp_name, t("simple.contracts"): n,
    })
    report.metrics(t("simple.report.results"), [
        (t("simple.cost"), money(cost, cents=True)), (t("simple.breakeven"), money(breakeven, cents=True)),
        (t("simple.max_loss"), money(-cost, cents=True)),
        (t("simple.max_gain"), t("simple.unlimited") if call else money((strike - per_share) * shares, cents=True)),
        (t("simple.chance"), f"{100 * chance:.0f}%"),
    ])
    report.table(t("simple.scenarios", ticker=ticker), pd.DataFrame({
        t("simple.report.col.ends"): [money(e, cents=True) for e in ends],
        t("simple.report.col.change"): [pct(m) if m else "±0%" for m in SCENARIOS],
        t("simple.report.col.pnl"): [money(v, signed=True) for v in outcomes],
    }))
    report.figure(t("simple.chart"), fig)
    report.text(t("simple.report.how"), t("simple.report.how.price", ticker=ticker, vol=f"{sigma:.0%}",
                                           rate=f"{r:.2%}", div=f"{q:.2%}"))


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def backtest_page() -> None:
    s = st.session_state
    s.setdefault("sb_ticker", s.get("bt_ticker", "AAPL"))
    s.setdefault("sb_period", "5y")
    s.setdefault("sb_strategy", "covered_call")
    s.setdefault("sb_amount", 10_000)

    report = Report(title=t("simple.report.bt"))
    page_header("simple.bt.title", "simple.bt.lede", report=report)
    left, right = st.columns([1, 2.4], gap="small")
    with left, panel("sb_inputs"):
        panel_title(t("simple.stock"))
        ticker = _ticker_picker("sb_ticker")
        st.segmented_control(lbl("simple.bt.period"), PERIODS, key="sb_period", required=True, width="stretch",
                             format_func=str.upper)
        with st.expander(upper(t("simple.bt.file"))):
            uploaded = st.file_uploader(lbl("mk.upload"), type=list(parse.UPLOAD_TYPES), key="sb_upload",
                                        label_visibility="collapsed")
        st.html('<div style="height:0.6rem"></div>')
        panel_title(t("simple.bt.strategy"))
        st.selectbox(lbl("simple.bt.strategy"), STRATEGIES, key="sb_strategy", label_visibility="collapsed",
                     format_func=lambda k: t(f"simple.strat.{k}"))
        st.number_input(lbl("simple.bt.amount"), 100, 10_000_000, step=1000, key="sb_amount")

    with right:
        hist: PriceHistory | None = None
        try:
            if uploaded is not None:
                hist = parse.parse_price_file(uploaded.getvalue(), uploaded.name)
            else:
                with st.spinner(t("mk.loading", ticker=ticker)):
                    hist = load_history(ticker, s["sb_period"])
        except MarketDataError as exc:
            st.error(str(exc))
            return

        rf = load_risk_free()
        strategy = s["sb_strategy"]
        config = BacktestConfig(
            legs=template_legs(strategy), tenor_days=30, vol_window=21, vol_premium=0.10,
            rate=rf if rf is not None else 0.04, dividend_yield=hist.dividend_yield,
            spread=0.05, commission=0.0065, strike_step=1.0,
        )
        try:
            result = run_backtest(hist.dates, hist.close, config, dividends=dividends_on_dates(hist).to_numpy())
        except ValueError as exc:
            st.warning(str(exc))
            return

        amount = float(s["sb_amount"])
        value = result.value * amount / result.value[0]
        shares = result.benchmark * amount / result.benchmark[0]
        mine = performance(result.value, result.dates, config.rate)
        bench = performance(result.benchmark, result.dates, config.rate)
        gain, bench_gain = value[-1] - amount, shares[-1] - amount
        diff = value[-1] - shares[-1]
        wins = sum(c.pnl > 0 for c in result.cycles)
        risk = risk_level(mine["annual_volatility"], mine["max_drawdown"])
        bench_risk = risk_level(bench["annual_volatility"], bench["max_drawdown"])
        name = t(f"simple.strat.{strategy}").split(" · ")[0]

        st.html(cells([
            (t("simple.bt.became", amount=money(amount)), money(value[-1]),
             f"{money(gain, signed=True)} ({pct(mine['total_return'])})", tone(gain)),
            (t("simple.bt.shares"), money(shares[-1]), f"{money(bench_gain, signed=True)} ({pct(bench['total_return'])})",
             tone(bench_gain)),
            (t("simple.bt.vs"), money(diff, signed=True),
             upper(t("simple.bt.vs.sub", more_less=t("simple.more") if diff >= 0 else t("simple.less"))), tone(diff)),
        ], columns=3, extra_class="opl-simple-grid opl-simple-hero"))
        st.html(cells([
            (t("simple.bt.per_year"), pct(mine["annual_return"]), upper(t("simple.bt.shares_sub",
                                                                         value=pct(bench["annual_return"]))),
             tone(mine["annual_return"])),
            (t("simple.bt.drop"), pct(-mine["max_drawdown"]),
             upper(t("simple.bt.shares_sub", value=pct(-bench["max_drawdown"]))), "neg"),
            (t("simple.bt.risk"), upper(t(f"simple.risk.{risk}")),
             upper(t("simple.bt.shares_sub", value=t(f"simple.risk.{bench_risk}"))), "vol"),
            (t("simple.bt.wins"), t("simple.bt.wins.value", wins=wins, total=len(result.cycles)), "", ""),
        ], columns=4, extra_class="opl-simple-grid"))

        p = palette()
        section(t("simple.bt.chart"))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result.dates, y=shares, name=t("simple.bt.shares"),
                                 line=dict(color=p.label, width=1.4, dash="dash"), hovertemplate="$%{y:,.0f}"))
        fig.add_trace(go.Scatter(x=result.dates, y=value, name=name, line=dict(color=p.accent, width=2),
                                 hovertemplate="$%{y:,.0f}"))
        style_figure(fig, height=340, y_title=t("simple.bt.chart.y"))
        fig.update_yaxes(tickformat="$,.0f")
        label = hist.label if uploaded is not None else ticker
        show(fig, key="sb_chart", snapshot=snapshot_name(label, strategy.replace("_", "-"), s["sb_period"], "value"))

        if result.cycles:
            section(t("simple.bt.months"))
            scale = amount / result.value[0]
            pnl = np.array([c.pnl for c in result.cycles]) * scale
            bars = go.Figure(go.Bar(
                x=pd.to_datetime([c.expiry_date for c in result.cycles]), y=pnl,
                marker=dict(color=np.where(pnl >= 0, p.positive, p.negative), line=dict(width=0)),
                hovertemplate="%{x|%b %Y}: %{y:+$,.0f}<extra></extra>",
            ))
            style_figure(bars, height=240, legend=False, hovermode="closest")
            bars.update_yaxes(tickformat="$,.0f")
            show(bars, key="sb_months", snapshot=snapshot_name(label, strategy.replace("_", "-"), s["sb_period"],
                                                               "monthly"))
        st.html(f'<p class="opl-note">{t("simple.bt.note")}</p>')

    start, end = result.dates[0].date(), result.dates[-1].date()
    report.subtitle = f"{name} on {label}, {start} to {end}"
    report.data_source = f"{hist.source}, daily prices and dividends for {label} up to {hist.last_date}."
    report.params(t("simple.report.setup"), {
        t("simple.report.stock"): label, t("simple.report.period"): f"{start} to {end}",
        t("simple.report.strategy"): t(f"simple.strat.{strategy}"), t("simple.bt.amount"): money(amount),
    })
    report.metrics(t("simple.report.results"), [
        (t("simple.bt.became", amount=money(amount)), money(value[-1])),
        (t("simple.report.profit"), f"{money(gain, signed=True)} ({pct(mine['total_return'])})"),
        (t("simple.bt.shares"), money(shares[-1])), (t("simple.bt.vs"), money(diff, signed=True)),
        (t("simple.bt.per_year"), pct(mine["annual_return"])), (t("simple.bt.drop"), pct(-mine["max_drawdown"])),
        (t("simple.bt.risk"), t(f"simple.risk.{risk}")),
        (t("simple.bt.wins"), t("simple.bt.wins.value", wins=wins, total=len(result.cycles))),
    ])
    report.figure(t("simple.bt.chart"), fig)
    if result.cycles:
        report.figure(t("simple.bt.months"), bars)
        report.table(t("simple.bt.months"), pd.DataFrame({
            t("simple.report.col.month"): [c.expiry_date.date() for c in result.cycles],
            t("simple.report.col.pnl"): [money(v, signed=True) for v in pnl],
        }))
    report.text(t("simple.report.how"), t("simple.report.how.bt", rate=f"{config.rate:.2%}"))
