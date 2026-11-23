"""Simple mode: every strategy the lab offers, on two clean screens for complete beginners.

* **Option price**: pick a stock and any strategy (or build your own). One big number for what
  you pay or receive, one profit/loss chart, and four stats: break-even, max profit, max loss,
  chance of profit.
* **Backtest**: pick a stock and any strategy (or build your own). One big number for what your
  money became, one chart against just owning the shares, and a few stats.

Volatility, interest rate, dividends, costs and roll period are filled in automatically, using
the same pricing engine and backtester as the full lab. All wording lives in :mod:`app.content`
under ``simple.*``.
"""

from __future__ import annotations

import html
import math
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.content import t
from app.data import POPULAR, dividends_on_dates, load_history, load_risk_free
from app.report import Report
from app.theme import palette, show, snapshot_name, style_figure
from app.ui import cells, lbl, page_header, panel, upper
from marketdata import parse
from marketdata.parse import MarketDataError, PriceHistory
from pricing.backtest import MAX_LEGS, MAX_QUANTITY, BacktestConfig, LegTemplate, performance, run_backtest, template_legs
from pricing.historical import historical_volatility
from pricing.strategies import Leg, Strategy, probability_of_profit, risk_summary

EXPIRIES = {"1w": 7, "1m": 30, "3m": 91, "6m": 182, "1y": 365}
MOVES = {"calm": 0.15, "normal": 0.30, "wild": 0.50}
PERIODS = ["1y", "2y", "5y", "10y"]
CATALOG = ["long_call", "long_put", "covered_call", "protective_put", "collar", "cash_secured_put",
           "long_straddle", "long_strangle", "bull_call_spread", "bear_put_spread", "iron_condor", "custom"]
USES_GAP = {"covered_call", "protective_put", "collar", "cash_secured_put", "long_strangle",
            "bull_call_spread", "bear_put_spread", "iron_condor"}
SIDES, KINDS = ("buy", "sell"), ("call", "put", "stock")


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


def tone(x: Optional[float]) -> str:
    if x is None or not math.isfinite(x) or abs(x) < 1e-12:
        return ""
    return "pos" if x > 0 else "neg"


def nice_strike(price: float) -> float:
    """Round to a strike that would be listed: 50¢ steps under $25, $1 under $200, $5 above."""
    step = 0.5 if price < 25 else (1.0 if price < 200 else 5.0)
    return max(step, round(price / step) * step)


def risk_level(annual_vol: float, max_drawdown: float) -> str:
    """Low / medium / high from yearly ups and downs and the biggest drop (whichever is worse)."""
    def level(x: float, lo: float, hi: float) -> int:
        return 0 if x < lo else (1 if x < hi else 2)

    vol = level(annual_vol if math.isfinite(annual_vol) else 1.0, 0.10, 0.20)
    drop = level(max_drawdown if math.isfinite(max_drawdown) else 1.0, 0.15, 0.30)
    return ("low", "medium", "high")[max(vol, drop)]


def catalog_legs(name: str, gap: float = 0.05) -> tuple[LegTemplate, ...]:
    """Legs of a Simple-mode strategy, strikes as multiples of today's price."""
    if name == "long_call":
        return (LegTemplate("call", 1, 1.0),)
    if name == "long_put":
        return (LegTemplate("put", 1, 1.0),)
    return template_legs(name, gap, gap, gap)


def legs_line(rows: list[tuple[str, float, Optional[str]]]) -> str:
    """'BUY 1 CALL $350 · SELL 1 CALL $365' from (kind, signed quantity, strike text) rows."""
    out = []
    for kind, qty, strike in rows:
        side = t("bt.custom.side.buy" if qty > 0 else "bt.custom.side.sell")
        what = t(f"bt.custom.kind.{kind}")
        if kind == "stock" and abs(qty) == 1:
            what = what.rstrip("s")
        out.append(f"{side} {abs(qty):g} {what}" + (f" {strike}" if strike else ""))
    return upper(" · ".join(out))


def hero(label: str, value: str, delta: str = "", delta_tone: str = "", meta: str = "") -> None:
    """The one big number at the top of a Simple screen."""
    st.html(
        f'<div class="opl-hero"><div class="k">{html.escape(upper(label))}</div>'
        f'<div class="v">{html.escape(value)}</div>'
        + (f'<div class="d {delta_tone}">{html.escape(delta)}</div>' if delta else "")
        + (f'<div class="m">{html.escape(meta)}</div>' if meta else "")
        + "</div>"
    )


def _ticker_picker(key: str) -> str:
    s = st.session_state
    options = POPULAR if s[key] in POPULAR else [s[key], *POPULAR]
    st.selectbox(lbl("simple.ticker"), options, key=key, accept_new_options=True)
    return str(s[key]).upper()


def _strategy_picker(key: str) -> str:
    st.selectbox(lbl("simple.strategy"), CATALOG, key=key, format_func=lambda k: t(f"simple.strat.{k}"))
    name = st.session_state[key]
    st.html(f'<p class="opl-note" style="margin:-0.3rem 0 0.2rem 0">{html.escape(t(f"simple.tag.{name}"))}</p>')
    return name


def _legs_editor(key: str, rows: list[dict], strike_label: str, strike_max: float, help_key: str) -> list[tuple]:
    """Editable table of legs -> [(kind, signed quantity, strike)]; incomplete rows are skipped."""
    frame = pd.DataFrame(rows, columns=["side", "kind", "qty", "strike"]).astype({"qty": float, "strike": float})
    edited = st.data_editor(
        frame, key=key, num_rows="dynamic", hide_index=True, width="stretch",
        column_config={
            "side": st.column_config.SelectboxColumn(t("bt.custom.col.side"), required=True, width=58,
                                                     options=[t(f"bt.custom.side.{v}") for v in SIDES],
                                                     default=t("bt.custom.side.buy")),
            "kind": st.column_config.SelectboxColumn(t("bt.custom.col.kind"), required=True, width=70,
                                                     options=[t(f"bt.custom.kind.{v}") for v in KINDS],
                                                     default=t("bt.custom.kind.call")),
            "qty": st.column_config.NumberColumn(t("bt.custom.col.qty"), min_value=0.0, max_value=MAX_QUANTITY,
                                                 step=1.0, default=1.0, format="%g", width=48),
            "strike": st.column_config.NumberColumn(strike_label, min_value=0.01, max_value=strike_max,
                                                    step=1.0, format="%g", width=74),
        },
    )
    st.caption(t(help_key))
    side_of = {t(f"bt.custom.side.{v}"): v for v in SIDES}
    kind_of = {t(f"bt.custom.kind.{v}"): v for v in KINDS}
    legs = []
    for row in edited.itertuples(index=False):
        side, kind = side_of.get(row.side), kind_of.get(row.kind)
        qty = float(row.qty) if row.qty is not None and pd.notna(row.qty) else 0.0
        strike = float(row.strike) if row.strike is not None and pd.notna(row.strike) else None
        if side is None or kind is None or qty <= 0 or (kind != "stock" and strike is None):
            continue
        legs.append((kind, min(qty, MAX_QUANTITY) * (1 if side == "buy" else -1), strike))
    return legs[:MAX_LEGS]


def _editor_rows(legs: tuple[LegTemplate, ...], strike_of) -> list[dict]:
    return [{
        "side": t(f"bt.custom.side.{'buy' if leg.quantity > 0 else 'sell'}"),
        "kind": t(f"bt.custom.kind.{leg.kind}"),
        "qty": abs(leg.quantity),
        "strike": None if leg.kind == "stock" else strike_of(leg.moneyness),
    } for leg in legs]


def _pnl_figure(grid: np.ndarray, y: np.ndarray, spot: float, marks: list[float], x_title: str) -> go.Figure:
    p = palette()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid, y=np.maximum(y, 0), fill="tozeroy", fillcolor=p.positive_fill,
                             line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=grid, y=np.minimum(y, 0), fill="tozeroy", fillcolor=p.negative_fill,
                             line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=grid, y=y, line=dict(color=p.ink, width=2), showlegend=False,
                             hovertemplate="$%{x:,.2f} → %{y:$,.0f}<extra></extra>"))
    if marks:
        fig.add_trace(go.Scatter(x=marks, y=[0] * len(marks), mode="markers", showlegend=False, hoverinfo="skip",
                                 marker=dict(color=p.accent, size=9, symbol="diamond",
                                             line=dict(color=p.canvas, width=1.5))))
    fig.add_vline(x=spot, line=dict(color=p.accent, width=1, dash="dot"),
                  annotation_text=upper(t("simple.today")), annotation_position="top right", annotation_font_size=11)
    style_figure(fig, height=340, x_title=x_title, legend=False, hovermode="closest")
    fig.update_yaxes(tickformat="$,.0f")
    fig.update_xaxes(tickprefix="$")
    return fig


# ---------------------------------------------------------------------------
# Option price
# ---------------------------------------------------------------------------

def price_page() -> None:
    s = st.session_state
    s.setdefault("sp_ticker", s.get("mk_applied", ("AAPL", "2y"))[0])
    s.setdefault("sp_strategy", "long_call")
    s.setdefault("sp_gap", 5.0)
    s.setdefault("sp_exp", "1m")
    s.setdefault("sp_contracts", 1)
    s.setdefault("sp_manual_price", 100.0)
    s.setdefault("sp_moves", "normal")
    if s["sp_strategy"] != "custom":
        s["sp_last"] = s["sp_strategy"]

    report = Report(title=t("simple.report.price"))
    page_header("simple.price.title", "simple.price.lede", report=report)
    left, right = st.columns([1, 2.4], gap="small")
    with left, panel("sp_inputs"):
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
        st.html(f'<p class="opl-note" style="margin:-0.3rem 0 0.4rem 0">{html.escape(ticker)} '
                f'<b>{money(spot, cents=True)}</b></p>')

        strategy = _strategy_picker("sp_strategy")
        if strategy == "custom":
            last = s.get("sp_last", "long_call")
            seed = _editor_rows(catalog_legs(last, float(s["sp_gap"]) / 100), lambda m: nice_strike(m * spot))
            rows = _legs_editor(f"sp_editor_{ticker}_{last}", seed, "Strike $", 1e6, "simple.legs.help")
        else:
            if strategy in USES_GAP:
                st.number_input(lbl("simple.gap"), 0.5, 50.0, step=1.0, format="%g", key="sp_gap")
            rows = [(leg.kind, leg.quantity, None if leg.kind == "stock" else nice_strike(leg.moneyness * spot))
                    for leg in catalog_legs(strategy, float(s["sp_gap"]) / 100)]
        st.number_input(lbl("simple.contracts"), 1, 1000, step=1, key="sp_contracts")

    with right:
        if not rows:
            st.info(t("simple.legs.empty"))
            return
        n = int(s["sp_contracts"])
        T = EXPIRIES[s["sp_exp"]] / 365.0
        rf = load_risk_free()
        r = rf if rf is not None else 0.04
        strat = Strategy(t(f"simple.strat.{strategy}"),
                         tuple(Leg(kind, qty, strike or 0.0) for kind, qty, strike in rows))
        per_share = strat.cost(spot, T, r, sigma, q)  # negative means you receive a credit
        size = 100 * n
        strikes = [k for _, _, k in rows if k]
        lo, hi = 0.6 * min([spot, *strikes]), 1.4 * max([spot, *strikes])
        grid = np.linspace(lo, hi, 601)
        risk = risk_summary(strat, per_share, grid)
        chance = probability_of_profit(strat, per_share, spot, T, r, sigma, q)
        y = strat.pnl_at_expiry(grid, per_share) * size
        line = legs_line([(k, qty * n * (100 if k == "stock" else 1), money(st_, cents=st_ % 1 != 0) if st_ else None)
                          for k, qty, st_ in rows])
        paying = per_share >= 0

        hero(t("simple.pay") if paying else t("simple.receive"), money(abs(per_share) * size, cents=True), meta=line)
        fig = _pnl_figure(grid, y, spot, [b for b in risk.breakevens if lo < b < hi],
                          t("simple.chart.x", ticker=ticker))
        exp_long = t(f"simple.exp.long.{s['sp_exp']}")
        show(fig, key="sp_chart", snapshot=snapshot_name(ticker, strategy.replace("_", "-"), exp_long))
        st.segmented_control(lbl("simple.expiry"), list(EXPIRIES), key="sp_exp", required=True, width="stretch",
                             format_func=lambda v: t(f"simple.exp.{v}"), label_visibility="collapsed")

        be = " / ".join(money(b, cents=True) for b in risk.breakevens) or t("simple.none")
        max_profit = t("simple.unlimited") if risk.max_profit is None else money(risk.max_profit * size, cents=True)
        max_loss = t("simple.unlimited") if risk.max_loss is None else money(risk.max_loss * size, cents=True)
        st.html(cells([
            (t("simple.breakeven"), be, "", ""),
            (t("simple.max_profit"), upper(max_profit), "", "pos"),
            (t("simple.max_loss"), upper(max_loss), "", "neg"),
            (t("simple.chance"), f"{100 * chance:.0f}%", "", ""),
        ], columns=4, extra_class="opl-simple-grid"))
        st.html(f'<p class="opl-note">{html.escape(t("simple.price.note", ticker=ticker))}</p>')

    report.subtitle = f"{strat.name} on {ticker}, expires in {exp_long}"
    report.data_source = (f"{hist.source}, daily prices for {ticker} up to {hist.last_date}." if hist is not None
                          else t("simple.report.manual"))
    report.params(t("simple.report.setup"), {
        t("simple.report.stock"): ticker, t("simple.report.today"): money(spot, cents=True),
        t("simple.strategy"): strat.name, t("simple.report.legs"): line.title(),
        t("simple.expiry"): exp_long, t("simple.contracts"): n,
    })
    report.metrics(t("simple.report.results"), [
        (t("simple.pay") if paying else t("simple.receive"), money(abs(per_share) * size, cents=True)),
        (t("simple.breakeven"), be), (t("simple.max_profit"), max_profit),
        (t("simple.max_loss"), max_loss), (t("simple.chance"), f"{100 * chance:.0f}%"),
    ])
    report.figure(t("simple.report.profit"), fig)
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
    s.setdefault("sb_gap", 5.0)
    s.setdefault("sb_amount", 10_000)
    if s["sb_strategy"] != "custom":
        s["sb_last"] = s["sb_strategy"]

    report = Report(title=t("simple.report.bt"))
    page_header("simple.bt.title", "simple.bt.lede", report=report)
    left, right = st.columns([1, 2.4], gap="small")
    with left, panel("sb_inputs"):
        ticker = _ticker_picker("sb_ticker")
        strategy = _strategy_picker("sb_strategy")
        if strategy == "custom":
            last = s.get("sb_last", "covered_call")
            seed = _editor_rows(catalog_legs(last, float(s["sb_gap"]) / 100), lambda m: round(100 * m, 2))
            rows = _legs_editor(f"sb_editor_{last}", seed, t("bt.custom.col.strike"), 500.0, "simple.legs.help.bt")
            legs = tuple(LegTemplate(kind, qty, 1.0 if kind == "stock" else strike / 100) for kind, qty, strike in rows)
        else:
            if strategy in USES_GAP:
                st.number_input(lbl("simple.gap"), 0.5, 50.0, step=1.0, format="%g", key="sb_gap")
            legs = catalog_legs(strategy, float(s["sb_gap"]) / 100)
        st.number_input(lbl("simple.bt.amount"), 100, 10_000_000, step=1000, key="sb_amount")
        with st.expander(upper(t("simple.bt.file"))):
            uploaded = st.file_uploader(lbl("mk.upload"), type=list(parse.UPLOAD_TYPES), key="sb_upload",
                                        label_visibility="collapsed")

    with right:
        if not legs:
            st.info(t("simple.legs.empty"))
            return
        try:
            if uploaded is not None:
                hist = parse.parse_price_file(uploaded.getvalue(), uploaded.name)
            else:
                with st.spinner(t("mk.loading", ticker=ticker)):
                    hist = load_history(ticker, s["sb_period"])
        except MarketDataError as exc:
            st.error(str(exc))
            return
        label = hist.label if uploaded is not None else ticker

        rf = load_risk_free()
        config = BacktestConfig(
            legs=legs, tenor_days=30, vol_window=21, vol_premium=0.10,
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
        gain, diff = value[-1] - amount, value[-1] - shares[-1]
        wins = sum(c.pnl > 0 for c in result.cycles)
        risk = risk_level(mine["annual_volatility"], mine["max_drawdown"])
        name = t(f"simple.strat.{strategy}")
        line = legs_line([(leg.kind, leg.quantity, None if leg.kind == "stock" else f"{100 * leg.moneyness:g}%")
                          for leg in legs])

        hero(t("simple.bt.became", amount=money(amount)), money(value[-1]),
             f"{money(gain, signed=True)} ({pct(mine['total_return'])})", tone(gain),
             t("simple.bt.shares_line", value=money(shares[-1]), ret=pct(bench["total_return"])))
        p = palette()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result.dates, y=shares, name=t("simple.bt.shares"),
                                 line=dict(color=p.label, width=1.4, dash="dash"), hovertemplate="$%{y:,.0f}"))
        fig.add_trace(go.Scatter(x=result.dates, y=value, name=name, line=dict(color=p.accent, width=2),
                                 hovertemplate="$%{y:,.0f}"))
        style_figure(fig, height=340)
        fig.update_yaxes(tickformat="$,.0f")
        show(fig, key="sb_chart", snapshot=snapshot_name(label, strategy.replace("_", "-"), s["sb_period"]))
        st.segmented_control(lbl("simple.report.period"), PERIODS, key="sb_period", required=True, width="stretch",
                             format_func=str.upper, label_visibility="collapsed", disabled=uploaded is not None)

        st.html(cells([
            (t("simple.bt.vs"), money(diff, signed=True), "", tone(diff)),
            (t("simple.bt.per_year"), pct(mine["annual_return"]), "", tone(mine["annual_return"])),
            (t("simple.bt.drop"), pct(-mine["max_drawdown"]), "", "neg"),
            (t("simple.bt.risk"), upper(t(f"simple.risk.{risk}")), "", "vol"),
            (t("simple.bt.wins"), t("simple.bt.wins.value", wins=wins, total=len(result.cycles)), "", ""),
        ], columns=5, extra_class="opl-simple-grid"))
        st.html(f'<p class="opl-note" style="margin:0.4rem 0 0 0">{html.escape(line)}</p>')

        bars, pnl = None, np.empty(0)
        if result.cycles:
            pnl = np.array([c.pnl for c in result.cycles]) * amount / result.value[0]
            bars = go.Figure(go.Bar(
                x=pd.to_datetime([c.expiry_date for c in result.cycles]), y=pnl,
                marker=dict(color=np.where(pnl >= 0, p.positive, p.negative), line=dict(width=0)),
                hovertemplate="%{x|%b %Y}: %{y:+$,.0f}<extra></extra>",
            ))
            style_figure(bars, height=220, legend=False, hovermode="closest")
            bars.update_layout(title=dict(text=upper(t("simple.bt.months")), x=0.01, y=0.97,
                                          font=dict(size=10, color=p.label)))
            bars.update_yaxes(tickformat="$,.0f")
            show(bars, key="sb_months", snapshot=snapshot_name(label, strategy.replace("_", "-"), s["sb_period"],
                                                               "monthly"))
        st.html(f'<p class="opl-note">{html.escape(t("simple.bt.note"))}</p>')

    start, end = result.dates[0].date(), result.dates[-1].date()
    report.subtitle = f"{name} on {label}, {start} to {end}"
    report.data_source = f"{hist.source}, daily prices and dividends for {label} up to {hist.last_date}."
    report.params(t("simple.report.setup"), {
        t("simple.report.stock"): label, t("simple.report.period"): f"{start} to {end}",
        t("simple.strategy"): name, t("simple.report.legs"): line.title(), t("simple.bt.amount"): money(amount),
    })
    report.metrics(t("simple.report.results"), [
        (t("simple.bt.became", amount=money(amount)), money(value[-1])),
        (t("simple.report.profit"), f"{money(gain, signed=True)} ({pct(mine['total_return'])})"),
        (t("simple.bt.shares"), money(shares[-1])), (t("simple.bt.vs"), money(diff, signed=True)),
        (t("simple.bt.per_year"), pct(mine["annual_return"])), (t("simple.bt.drop"), pct(-mine["max_drawdown"])),
        (t("simple.bt.risk"), t(f"simple.risk.{risk}")),
        (t("simple.bt.wins"), t("simple.bt.wins.value", wins=wins, total=len(result.cycles))),
    ])
    report.figure(t("simple.bt.became", amount=money(amount)), fig)
    if bars is not None:
        report.figure(t("simple.bt.months"), bars)
        report.table(t("simple.bt.months"), pd.DataFrame({
            t("simple.report.col.month"): [c.expiry_date.date() for c in result.cycles],
            t("simple.report.col.pnl"): [money(v, signed=True) for v in pnl],
        }))
    report.text(t("simple.report.how"), t("simple.report.how.bt", rate=f"{config.rate:.2%}"))
