"""Backtest: how a rolling option strategy would have performed on a real stock."""

from __future__ import annotations

import html
import math
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.content import t
from app.data import POPULAR, dividends_on_dates, load_history, load_risk_free
from app.report import Report
from app.theme import palette, show, style_figure
from app.ui import cells, explain, finish_page, is_pro, lbl, page_header, panel, panel_title, section, tx, upper
from marketdata import parse
from marketdata.parse import MarketDataError, PriceHistory
from pricing.backtest import TEMPLATE_NAMES, BacktestConfig, performance, run_backtest, template_legs

PERIODS = ["1y", "2y", "5y", "10y"]
TENORS = [7, 14, 21, 30, 45, 60, 90, 120, 180]
USES_CALL = {"covered_call", "collar", "long_strangle", "bull_call_spread", "iron_condor"}
USES_PUT = {"protective_put", "collar", "cash_secured_put", "long_strangle", "bear_put_spread", "iron_condor"}

s = st.session_state
s.setdefault("bt_ticker", s.get("mk_applied", ("AAPL", "2y"))[0])
s.setdefault("bt_period", "5y")
s.setdefault("bt_applied", (s["bt_ticker"], s["bt_period"]))
for key, value in dict(bt_strategy="covered_call", bt_tenor=30, bt_otm_call=5.0, bt_otm_put=5.0, bt_wing=5.0,
                       bt_window=21, bt_vol_premium=10.0, bt_spread=5.0, bt_commission=0.65,
                       bt_strike_step=1.0).items():
    s.setdefault(key, value)


if "bt_rate" not in s:  # default to today's 13-week T-bill rate, before the input is drawn
    _rf0 = load_risk_free()
    s["bt_rate"] = round(100 * _rf0, 2) if _rf0 is not None else 4.0


report = Report(title=t("bt.report_title"))
actions = page_header("bt.title", "bt.lede", page="backtest", report=report)


def _apply_ticker() -> None:
    s["bt_applied"] = (s["bt_ticker"], s["bt_period"])
    s.pop("bt_start", None)
    s.pop("bt_end", None)


left, right = st.columns([1, 3.1], gap="small")
with left, panel("bt_inputs"):
    panel_title(tx("bt.data"))
    source = st.segmented_control(
        lbl("mk.source"), ["ticker", "upload"], format_func=lambda v: upper(tx(f"mk.source.{v}")),
        key="bt_source", default="ticker", required=True, label_visibility="collapsed", width="stretch",
    )
    uploaded = None
    if source == "ticker":
        options = POPULAR if s["bt_ticker"] in POPULAR else [s["bt_ticker"], *POPULAR]
        st.selectbox(lbl("mk.ticker"), options, key="bt_ticker", accept_new_options=True, help=tx("mk.ticker.help"))
        st.segmented_control(lbl("mk.period"), PERIODS, format_func=str.upper, key="bt_period", required=True,
                             width="stretch")
        st.button(upper(t("mk.load")), key="bt_load", on_click=_apply_ticker, width="stretch")
    else:
        uploaded = st.file_uploader(lbl("mk.upload"), type=["csv"], key="bt_upload", help=t("mk.upload.help"))

    st.html('<div style="height:0.6rem"></div>')
    panel_title(tx("bt.strategy"))
    strategy = st.selectbox(lbl("bt.strategy"), TEMPLATE_NAMES, key="bt_strategy",
                            format_func=lambda k: upper(tx(f"bt.strategy.{k}")), label_visibility="collapsed")
    st.html(f'<p class="opl-note" style="margin:0">{html.escape(tx(f"bt.strategy.{strategy}.desc"))}</p>')
    st.select_slider(lbl("bt.tenor"), TENORS, key="bt_tenor", format_func=lambda d: f"{d}D", help=tx("bt.tenor.help"))
    if strategy in USES_CALL:
        st.number_input(lbl("bt.otm_call"), 0.0, 50.0, step=1.0, format="%.1f", key="bt_otm_call",
                        help=tx("bt.otm_call.help"))
    if strategy in USES_PUT:
        st.number_input(lbl("bt.otm_put"), 0.0, 50.0, step=1.0, format="%.1f", key="bt_otm_put",
                        help=tx("bt.otm_put.help"))
    if strategy == "iron_condor":
        st.number_input(lbl("bt.wing"), 0.5, 50.0, step=1.0, format="%.1f", key="bt_wing", help=tx("bt.wing.help"))

    with st.expander(upper(tx("bt.assumptions")), expanded=is_pro()):
        st.segmented_control(lbl("bt.window"), [21, 63, 126], format_func=lambda w: f"{w}D", key="bt_window",
                             required=True, help=tx("bt.window.help"), width="stretch")
        st.number_input(lbl("bt.vol_premium"), -50.0, 200.0, step=5.0, format="%.0f", key="bt_vol_premium",
                        help=tx("bt.vol_premium.help"))
        st.number_input(lbl("bt.rate"), -5.0, 50.0, step=0.25, format="%.2f", key="bt_rate", help=tx("bt.rate.help"))
        st.number_input(lbl("bt.spread"), 0.0, 100.0, step=1.0, format="%.1f", key="bt_spread",
                        help=tx("bt.spread.help"))
        st.number_input(lbl("bt.commission"), 0.0, 50.0, step=0.05, format="%.2f", key="bt_commission",
                        help=tx("bt.commission.help"))
        st.segmented_control(lbl("bt.strike_step"), [0.0, 0.5, 1.0, 2.5, 5.0],
                             format_func=lambda v: upper(t("bt.exact")) if v == 0 else f"${v:g}", key="bt_strike_step",
                             required=True, help=tx("bt.strike_step.help"), width="stretch")

# --------------------------------------------------------------------------- data
hist: PriceHistory | None = None
error = None
if source == "ticker":
    ticker, period = s["bt_applied"]
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

    first, last = hist.dates[0].date(), hist.dates[-1].date()
    start_default = date.fromisoformat(s["bt_start"]) if s.get("bt_start") else first
    end_default = date.fromisoformat(s["bt_end"]) if s.get("bt_end") else last
    start_default, end_default = max(first, min(start_default, last)), max(first, min(end_default, last))
    window = st.slider(lbl("bt.range"), min_value=first, max_value=last, value=(start_default, end_default),
                       format="YYYY-MM-DD", key=f"bt_range_{hist.label}_{len(hist.dates)}",
                       help=tx("bt.range.help"))
    s["bt_start"], s["bt_end"] = window[0].isoformat(), window[1].isoformat()

    q = hist.dividend_yield
    config = BacktestConfig(
        legs=template_legs(strategy, s["bt_otm_call"] / 100, s["bt_otm_put"] / 100, s["bt_wing"] / 100),
        tenor_days=int(s["bt_tenor"]),
        vol_window=int(s["bt_window"]),
        vol_premium=float(s["bt_vol_premium"]) / 100,
        rate=float(s["bt_rate"]) / 100,
        dividend_yield=q,
        spread=float(s["bt_spread"]) / 100,
        commission=float(s["bt_commission"]) / 100,  # dollars per contract -> per share
        strike_step=float(s["bt_strike_step"]),
    )
    try:
        result = run_backtest(hist.dates, hist.close, config, dividends=dividends_on_dates(hist).to_numpy(),
                              start=pd.Timestamp(window[0]), end=pd.Timestamp(window[1]))
    except ValueError as exc:
        st.warning(str(exc))
        st.stop()

    stats = performance(result.value, result.dates, config.rate)
    bench = performance(result.benchmark, result.dates, config.rate)
    p = palette()
    strat_name = tx(f"bt.strategy.{strategy}")

    def pct(x: float, digits: int = 1) -> str:
        return "–" if x is None or not math.isfinite(x) else f"{100 * x:+.{digits}f}%".replace("-", "−")

    def num(x: float) -> str:
        return "–" if x is None or not math.isfinite(x) else f"{x:.2f}".replace("-", "−")

    # --------------------------------------------------------------- summary
    section(tx("bt.summary"))
    bh = upper(t("bt.bh_short"))
    def tone(x: float) -> str:
        """Green for a gain, red for a loss: colour always follows the sign, never the benchmark."""
        if x is None or not math.isfinite(x) or x == 0:
            return ""
        return "pos" if x > 0 else "neg"

    excess = stats["total_return"] - bench["total_return"]
    summary_cells = [
        (tx("bt.total_return"), pct(stats["total_return"]), f"{bh} {pct(bench['total_return'])}",
         tone(stats["total_return"])),
        (tx("bt.annual_return"), pct(stats["annual_return"]), f"{bh} {pct(bench['annual_return'])}",
         tone(stats["annual_return"])),
        (tx("bt.excess"), f"{100 * excess:+.1f} pts".replace("-", "−"),
         upper(t("bt.excess.ahead") if excess > 0 else t("bt.excess.behind")), tone(excess)),
        (tx("bt.sharpe"), num(stats["sharpe"]), f"{bh} {num(bench['sharpe'])}", tone(stats["sharpe"])),
        (tx("bt.volatility"), pct(stats["annual_volatility"]).lstrip("+"),
         f"{bh} {pct(bench['annual_volatility']).lstrip('+')}", "vol"),
        (tx("bt.drawdown"), pct(-stats["max_drawdown"]), f"{bh} {pct(-bench['max_drawdown'])}", "neg"),
        (tx("bt.win_rate"), "–" if not result.cycles else f"{100 * result.win_rate:.0f}%",
         f"{len(result.cycles)} {upper(t('bt.cycles'))}", ""),
        (tx("bt.premium"), f"{'+' if result.total_premium > 0 else ''}${result.total_premium:,.2f}".replace("$-", "−$"),
         f"{upper(t('bt.per_share'))}, {upper(t('bt.costs_sub'))} ${result.total_costs:,.2f}", tone(result.total_premium)),
    ]
    st.html(cells(summary_cells, columns=4))
    better = stats["total_return"] > bench["total_return"]
    explain(tx("bt.explain", strategy=strat_name, ticker=hist.label, start=result.dates[0].date(),
               end=result.dates[-1].date(), ret=pct(stats["total_return"]), bh=pct(bench["total_return"]),
               verdict=t("bt.verdict.better") if better else t("bt.verdict.worse"),
               dd=pct(-stats["max_drawdown"]), bhdd=pct(-bench["max_drawdown"])))
    st.html(f'<p class="opl-note">{html.escape(t("bt.caveat"))}</p>')

    # --------------------------------------------------------------- equity curve
    section(tx("bt.equity"))
    norm_s = 100 * result.value / result.value[0]
    norm_b = 100 * result.benchmark / result.benchmark[0]
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=result.dates, y=norm_b, name=t("bt.bh_long", ticker=hist.label),
                                line=dict(color=p.label, width=1.4, dash="dash"), hovertemplate="%{y:.1f}"))
    fig_eq.add_trace(go.Scatter(x=result.dates, y=norm_s, name=strat_name,
                                line=dict(color=p.accent, width=1.8), hovertemplate="%{y:.1f}"))
    style_figure(fig_eq, height=340, y_title=tx("bt.equity.y"))
    show(fig_eq, key="bt_equity_chart")

    # --------------------------------------------------------------- drawdown
    section(tx("bt.drawdown_chart"))
    dd_s = 100 * (result.value / np.maximum.accumulate(result.value) - 1)
    dd_b = 100 * (result.benchmark / np.maximum.accumulate(result.benchmark) - 1)
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=result.dates, y=dd_b, name=t("bt.bh_long", ticker=hist.label),
                                line=dict(color=p.label, width=1.2, dash="dash"), hovertemplate="%{y:.1f}%"))
    fig_dd.add_trace(go.Scatter(x=result.dates, y=dd_s, name=strat_name, fill="tozeroy",
                                fillcolor=p.negative_fill, line=dict(color=p.negative, width=1.4),
                                hovertemplate="%{y:.1f}%"))
    style_figure(fig_dd, height=260, y_title=tx("bt.drawdown.y"))
    show(fig_dd, key="bt_drawdown_chart")

    # --------------------------------------------------------------- cycles
    log = result.cycles_frame()
    fig_cy = None
    if len(log):
        section(tx("bt.cycle_chart"), tx("bt.cycle_chart.lede"))
        fig_cy = go.Figure(go.Bar(
            x=pd.to_datetime(log["expiry"]), y=log["pnl"],
            marker=dict(color=np.where(log["pnl"] >= 0, p.positive, p.negative), line=dict(width=0)),
            hovertemplate="%{x|%Y-%m-%d}: %{y:+.2f}<extra></extra>", name=t("bt.cycle_pnl"),
        ))
        style_figure(fig_cy, height=240, y_title=tx("bt.cycle_chart.y"), legend=False, hovermode="closest")
        show(fig_cy, key="bt_cycle_chart")

        section(tx("bt.log"))
        pal = palette()

        def signed_colour(v: float) -> str:
            if not isinstance(v, (int, float)) or v == 0 or not math.isfinite(v):
                return ""
            return f"color: {pal.positive if v > 0 else pal.negative}"

        styled = log.style.map(signed_colour, subset=["premium", "payoff", "pnl"])
        st.dataframe(styled, hide_index=True, width="stretch", height=280, column_config={
            "open": st.column_config.DateColumn(t("bt.col.open")),
            "expiry": st.column_config.DateColumn(t("bt.col.expiry")),
            "spot_open": st.column_config.NumberColumn(t("bt.col.spot_open"), format="%.2f"),
            "spot_expiry": st.column_config.NumberColumn(t("bt.col.spot_expiry"), format="%.2f"),
            "sigma": st.column_config.NumberColumn(t("bt.col.sigma"), format="%.3f"),
            "strikes": st.column_config.TextColumn(t("bt.col.strikes")),
            "premium": st.column_config.NumberColumn(t("bt.col.premium"), format="%+.2f"),
            "costs": st.column_config.NumberColumn(t("bt.col.costs"), format="%.2f"),
            "payoff": st.column_config.NumberColumn(t("bt.col.payoff"), format="%+.2f"),
            "pnl": st.column_config.NumberColumn(t("bt.col.pnl"), format="%+.2f"),
        })

    daily = pd.DataFrame({"date": result.dates.date, "strategy_value": result.value, "buy_and_hold_value": result.benchmark})
    with st.container(horizontal=True, gap="small"):
        st.download_button(upper(t("bt.download.daily")), daily.to_csv(index=False), f"backtest-{hist.label}-daily.csv",
                           "text/csv", key="bt_dl_daily", on_click="ignore")
        if len(log):
            st.download_button(upper(t("bt.download.log")), log.to_csv(index=False), f"backtest-{hist.label}-trades.csv",
                               "text/csv", key="bt_dl_log", on_click="ignore")

    # --------------------------------------------------------------- report
    report.subtitle = f"{strat_name} on {hist.label}, {result.dates[0].date()} to {result.dates[-1].date()}"
    report.data_source = f"{hist.source}, daily closes and dividends for {hist.label} up to {hist.last_date}."
    legs_txt = ", ".join(f"{'+' if leg.quantity > 0 else '−'}{abs(leg.quantity):g} {leg.kind}"
                         + ("" if leg.kind == "stock" else f" @ {leg.moneyness:.0%} of spot") for leg in config.legs)
    report.params(t("bt.report.setup"), {
        "Underlying": hist.label, "Period": f"{result.dates[0].date()} to {result.dates[-1].date()}",
        "Strategy": strat_name, "Legs": legs_txt, "Roll every (days)": config.tenor_days,
        "Volatility": f"trailing {config.vol_window}-day realised, x{1 + config.vol_premium:.2f}",
        "Risk-free rate": f"{config.rate:.2%}", "Dividend yield (pricing)": f"{q:.2%}",
        "Bid-ask spread": f"{config.spread:.1%} of option price (half paid per trade)",
        "Commission": f"${100 * config.commission:.2f} per contract",
        "Strike rounding": "exact" if config.strike_step == 0 else f"${config.strike_step:g}",
    })
    report.metrics(t("bt.report.results"), [
        (f"{t('bt.total_return.pro')}", pct(stats["total_return"])), (f"{t('bt.bh_short')} total", pct(bench["total_return"])),
        ("Annual return", pct(stats["annual_return"])), (f"{t('bt.bh_short')} annual", pct(bench["annual_return"])),
        ("Volatility", pct(stats["annual_volatility"]).lstrip("+")), ("Sharpe", num(stats["sharpe"])),
        ("Max drawdown", pct(-stats["max_drawdown"])), ("Win rate", "–" if not result.cycles else f"{100 * result.win_rate:.0f}%"),
    ])
    report.figure(t("bt.equity.pro"), fig_eq)
    report.figure(t("bt.drawdown_chart.pro"), fig_dd)
    if fig_cy is not None:
        report.figure(t("bt.cycle_chart.pro"), fig_cy)
        report.table(t("bt.log.pro"), log)
    report.text(t("bt.report.method"), t("bt.report.method_body"))

finish_page(actions)
