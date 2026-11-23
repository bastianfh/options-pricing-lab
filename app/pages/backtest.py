"""Backtest: how a rolling option strategy would have performed on a real stock."""

from __future__ import annotations

import html
import math
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.content import t
from app.data import POPULAR, dividends_on_dates, load_history, load_risk_free
from app.report import APP_URL, Report, citation
from app.share import MAX_COMPARE, clean_name, decode_compare, encode_compare
from app.theme import palette, show, style_figure
from app.ui import cells, explain, finish_page, is_pro, lbl, page_header, panel, panel_title, section, tx, upper
from marketdata import parse
from marketdata.parse import MarketDataError, PriceHistory
from pricing.backtest import (
    MAX_LEGS,
    MAX_QUANTITY,
    TEMPLATE_NAMES,
    BacktestConfig,
    LegTemplate,
    cycle_payoff,
    legs_from_code,
    legs_to_code,
    performance,
    run_backtest,
    sized_legs,
    sizes_from_code,
    sizes_to_code,
    template_legs,
    upside_exposure,
)
from pricing import __version__
from pricing.historical import rolling_volatility

if st.session_state.get("mode") == "Simple":  # beginners get a stripped-down screen (app/simple.py)
    from app.simple import backtest_page

    backtest_page()
    st.stop()

PERIODS = ["1y", "2y", "5y", "10y"]
TENORS = [7, 14, 21, 30, 45, 60, 90, 120, 180]
USES_CALL = {"covered_call", "collar", "long_strangle", "bull_call_spread", "iron_condor"}
COMPARE_COLOURS = ("#FF5500", "#4DA3FF", "#C77DFF", "#F4F4F6")  # neutral of gain/loss/vol meanings
USES_PUT = {"protective_put", "collar", "cash_secured_put", "long_strangle", "bear_put_spread", "iron_condor"}
STRATEGY_OPTIONS = (*TEMPLATE_NAMES, "custom")
SIDES = ("buy", "sell")
KINDS = ("call", "put", "stock")

s = st.session_state
s.setdefault("bt_ticker", s.get("mk_applied", ("AAPL", "2y"))[0])
s.setdefault("bt_period", "5y")
s.setdefault("bt_applied", (s["bt_ticker"], s["bt_period"]))
DEFAULTS = dict(bt_strategy="covered_call", bt_tenor=30, bt_otm_call=5.0, bt_otm_put=5.0, bt_wing=5.0,
                bt_window=21, bt_vol_premium=10.0, bt_spread=5.0, bt_commission=0.65, bt_strike_step=1.0,
                bt_exits=False, bt_tp=50.0, bt_sl=200.0, bt_view="single")
for key, value in DEFAULTS.items():
    s.setdefault(key, value)
# Inputs that are only drawn for some strategies: re-assigning keeps their values while hidden
# (Streamlit otherwise drops the state of widgets that weren't drawn on the last run).
for key in ("bt_otm_call", "bt_otm_put", "bt_wing", "bt_name", "bt_exits", "bt_tp", "bt_sl", *(k for k in list(s.keys()) if str(k).startswith("bt_qty_"))):
    if key in s:
        s[key] = s[key]


def _size_key(name: str, i: int) -> str:
    return f"bt_qty_{name}_{i}"


def _sizes(name: str) -> list[float]:
    return [float(s.get(_size_key(name, i), 1.0)) for i in range(len(template_legs(name)))]


if not s.get("_bt_qty_seeded"):  # sizes from a shared link apply to the linked strategy, once
    s["_bt_qty_seeded"] = True
    if s.get("bt_qty") and s["bt_strategy"] in TEMPLATE_NAMES:
        try:
            shared_sizes = sizes_from_code(s["bt_qty"])
        except ValueError:
            shared_sizes = ()
        if len(shared_sizes) == len(template_legs(s["bt_strategy"])):
            for i, x in enumerate(shared_sizes):
                s[_size_key(s["bt_strategy"], i)] = x


if s["bt_strategy"] != "custom":
    s["bt_last_template"] = s["bt_strategy"]


def _template_code(name: str) -> str:
    # Also called from callbacks, which run before the defaults above are filled in.
    pct = {k: float(s.get(k, DEFAULTS[k])) / 100 for k in ("bt_otm_call", "bt_otm_put", "bt_wing")}
    legs = template_legs(name, pct["bt_otm_call"], pct["bt_otm_put"], pct["bt_wing"])
    return legs_to_code(sized_legs(legs, _sizes(name)))


def _seed_legs(code: str) -> None:
    """Replace the custom-legs table with ``code`` (a fresh editor key discards pending edits)."""
    s["bt_legs"] = s["bt_legs_seed"] = code
    s["bt_legs_ver"] = s.get("bt_legs_ver", 0) + 1


def _on_strategy_change() -> None:
    if s["bt_strategy"] == "custom" and not s.get("bt_legs"):
        _seed_legs(_template_code(s.get("bt_last_template", "covered_call")))


def _on_load_template() -> None:
    if s.get("bt_custom_from"):
        _seed_legs(_template_code(s["bt_custom_from"]))
    s["bt_custom_from"] = None


s.setdefault("bt_legs_ver", 0)
LEGS_EDITOR = f"bt_legs_editor_{s['bt_legs_ver']}"
if LEGS_EDITOR not in s:  # first draw, or back from another page: rebuild the table from the saved legs
    try:
        s["bt_legs_seed"] = legs_to_code(legs_from_code(s.get("bt_legs") or ""))
    except ValueError:
        s["bt_legs_seed"] = _template_code(s.get("bt_last_template", "covered_call"))


def _legs_frame(code: str) -> pd.DataFrame:
    rows = [{
        "side": t(f"bt.custom.side.{'buy' if leg.quantity > 0 else 'sell'}"),
        "kind": t(f"bt.custom.kind.{leg.kind}"),
        "qty": abs(leg.quantity),
        "strike": None if leg.kind == "stock" else round(100 * leg.moneyness, 2),
    } for leg in legs_from_code(code)]
    return pd.DataFrame(rows, columns=["side", "kind", "qty", "strike"]).astype({"qty": float, "strike": float})


def _frame_legs(frame: pd.DataFrame) -> list[LegTemplate]:
    """Legs from the edited table; incomplete or zero-quantity rows are skipped."""
    side_of = {t(f"bt.custom.side.{v}"): v for v in SIDES}
    kind_of = {t(f"bt.custom.kind.{v}"): v for v in KINDS}
    legs = []
    for row in frame.itertuples(index=False):
        side, kind = side_of.get(row.side), kind_of.get(row.kind)
        qty = float(row.qty) if row.qty is not None and pd.notna(row.qty) else 0.0
        if side is None or kind is None or qty <= 0:
            continue
        qty = min(qty, MAX_QUANTITY) * (1 if side == "buy" else -1)
        if kind == "stock":
            legs.append(LegTemplate("stock", qty))
        else:
            strike = float(row.strike) if row.strike is not None and pd.notna(row.strike) else 100.0
            legs.append(LegTemplate(kind, qty, min(max(strike, 1.0), 500.0) / 100))
    return legs


def _strategy_name(strategy: str) -> str:
    if strategy == "custom":
        return clean_name(s.get("bt_name") or "") or t("bt.custom.default_name")
    name = tx(f"bt.strategy.{strategy}")
    sizes = _sizes(strategy)
    if any(x != 1 for x in sizes):
        name += f" ({':'.join(f'{x:g}' for x in sizes)})"
    return name


def _exit_levels() -> tuple[Optional[float], Optional[float]]:
    """Take-profit and stop-loss levels as fractions of the premium (``None`` when off)."""
    if not s.get("bt_exits") or s.get("bt_strategy") == "buy_and_hold":
        return None, None
    tp, sl = float(s.get("bt_tp") or 0), float(s.get("bt_sl") or 0)
    return (tp / 100 if tp > 0 else None), (sl / 100 if sl > 0 else None)


def _compare_entries() -> list[dict]:
    try:
        return decode_compare(s.get("bt_cmp") or "")
    except (ValueError, TypeError):
        return []


def _add_to_compare() -> None:
    entries = _compare_entries()
    code = s.get("bt_legs") if s["bt_strategy"] == "custom" else _template_code(s["bt_strategy"])
    if not code:
        return
    tp, sl = _exit_levels()
    entry = dict(legs=code, tenor=int(s["bt_tenor"]), tp=tp, sl=sl, name=_strategy_name(s["bt_strategy"]))
    same = [e for e in entries if (e["legs"], e["tenor"], e["tp"], e["sl"]) == (code, entry["tenor"], tp, sl)]
    if same:
        st.toast(t("bt.cmp.duplicate"))
    elif len(entries) >= MAX_COMPARE:
        st.toast(t("bt.cmp.full"))
    else:
        entries.append(entry)
        s["bt_cmp"] = encode_compare(entries)
        st.toast(t("bt.cmp.added", name=entry["name"], n=len(entries)))


def _remove_compare(i: int) -> None:
    entries = _compare_entries()
    if 0 <= i < len(entries):
        entries.pop(i)
    if entries:
        s["bt_cmp"] = encode_compare(entries)
    else:
        s.pop("bt_cmp", None)


def _clear_compare() -> None:
    s.pop("bt_cmp", None)


def _where(m: float) -> str:
    """A strike multiple in words: 'at the price', '5% above the price'."""
    gap = round(100 * (m - 1), 2)
    if abs(gap) < 1e-9:
        return "at the price"
    return f"{abs(gap):g}% {'above' if gap > 0 else 'below'} the price"


def describe_legs(legs, short: bool = False) -> str:
    """'buy 1 share, sell 1 call 5% above the price', or 'BUY 1 SH · SELL 1 C 105%' when short."""
    out = []
    for leg in legs:
        side, n = ("buy" if leg.quantity > 0 else "sell"), abs(leg.quantity)
        if short:
            what = "SH" if leg.kind == "stock" else f"{leg.kind[0].upper()} {round(100 * leg.moneyness, 2):g}%"
            out.append(f"{side.upper()} {n:g} {what}")
        elif leg.kind == "stock":
            out.append(f"{side} {n:g} share{'s' if n != 1 else ''}")
        else:
            out.append(f"{side} {n:g} {leg.kind}{'s' if n != 1 else ''} {_where(leg.moneyness)}")
    return (" · " if short else ", ").join(out)


def _exit_phrase(tp: Optional[float], sl: Optional[float]) -> str:
    parts = []
    if tp is not None:
        parts.append(f"once the options had gained {100 * tp:g}% of the premium (take profit)")
    if sl is not None:
        parts.append(f"once they had lost {100 * sl:g}% of it (stop loss)")
    return "" if not parts else ", or closed early " + " or ".join(parts)


def paper_panel(hist: PriceHistory, dates: pd.DatetimeIndex, runs: list[tuple[str, BacktestConfig]]) -> None:
    """'For your paper': a methods paragraph built from the current settings, a checklist and the citation."""
    cfg = runs[0][1]
    divs = " and dividends" if float(np.sum(dividends_on_dates(hist))) > 0 else ""
    text = [f"Data: daily closing prices{divs} for {hist.label} from {dates[0].date()} to {dates[-1].date()} "
            f"(source: {hist.source})."]
    for name, c in runs:
        held = "held to expiry" if any(leg.kind != "stock" for leg in c.legs) else "held throughout"
        rolled = f", opened every {c.tenor_days} calendar days and {held}" if held == "held to expiry" else f", {held}"
        text.append(f"{name}: {describe_legs(c.legs)}{rolled}{_exit_phrase(c.take_profit, c.stop_loss)}.")
    step = "exact strikes" if cfg.strike_step == 0 else f"strikes rounded to the nearest ${cfg.strike_step:g}"
    text.append(
        "Option prices are model prices, not historical quotes: each option is priced with the Black-Scholes model "
        f"using the stock's trailing {cfg.vol_window}-day realised volatility multiplied by {1 + cfg.vol_premium:.2f} "
        "(to approximate the premium implied volatility usually carries over realised volatility, with a 5% "
        f"minimum), a {cfg.rate:.2%} risk-free rate and a {cfg.dividend_yield:.2%} dividend yield, with {step}."
    )
    text.append(f"Trading costs: half of a {cfg.spread:.1%} bid-ask spread on every option traded, plus "
                f"${100 * cfg.commission:.2f} commission per contract.")
    text.append("The benchmark is buying one share at the start and holding it, with dividends kept in cash earning "
                "the risk-free rate.")
    text.append(f"Backtests were run in Options Pricing Lab (v{__version__}), {APP_URL}.")
    with st.expander(upper(tx("bt.paper"))):
        st.caption(t("bt.paper.method"))
        st.code(" ".join(text), language=None, wrap_lines=True)
        st.markdown(f"**{t('bt.paper.checklist_title')}**")
        st.markdown(t("bt.paper.checklist"))
        st.code(citation(), language=None, wrap_lines=True)


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
        uploaded = st.file_uploader(lbl("mk.upload"), type=list(parse.UPLOAD_TYPES), key="bt_upload", help=t("mk.upload.help"))

    st.html('<div style="height:0.6rem"></div>')
    panel_title(tx("bt.strategy"))
    strategy = st.selectbox(lbl("bt.strategy"), STRATEGY_OPTIONS, key="bt_strategy", on_change=_on_strategy_change,
                            format_func=lambda k: upper(tx(f"bt.strategy.{k}")), label_visibility="collapsed")
    st.html(f'<p class="opl-note" style="margin:0">{html.escape(tx(f"bt.strategy.{strategy}.desc"))}</p>')
    custom_legs: list[LegTemplate] = []
    if strategy == "custom":
        st.selectbox(lbl("bt.custom.start"), TEMPLATE_NAMES, index=None, key="bt_custom_from",
                     on_change=_on_load_template, format_func=lambda k: upper(tx(f"bt.strategy.{k}")),
                     placeholder=upper(t("bt.custom.start.placeholder")), help=tx("bt.custom.start.help"))
        edited = st.data_editor(
            _legs_frame(s["bt_legs_seed"]), key=LEGS_EDITOR, num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "side": st.column_config.SelectboxColumn(
                    t("bt.custom.col.side"), options=[t(f"bt.custom.side.{v}") for v in SIDES],
                    default=t("bt.custom.side.buy"), required=True, width=58),
                "kind": st.column_config.SelectboxColumn(
                    t("bt.custom.col.kind"), options=[t(f"bt.custom.kind.{v}") for v in KINDS],
                    default=t("bt.custom.kind.call"), required=True, width=70),
                "qty": st.column_config.NumberColumn(t("bt.custom.col.qty"), min_value=0.0, max_value=MAX_QUANTITY,
                                                     step=0.5, default=1.0, format="%g", width=48),
                "strike": st.column_config.NumberColumn(t("bt.custom.col.strike"), min_value=1.0, max_value=500.0,
                                                        step=0.5, default=100.0, format="%g", width=74),
            },
        )
        st.caption(tx("bt.custom.legs.help"))
        custom_legs = _frame_legs(edited)
        if len(custom_legs) > MAX_LEGS:
            st.caption(t("bt.custom.trimmed"))
            custom_legs = custom_legs[:MAX_LEGS]
        if custom_legs:
            s["bt_legs"] = legs_to_code(custom_legs)
        st.text_input(lbl("bt.custom.name"), key="bt_name", max_chars=40, placeholder=t("bt.custom.default_name"),
                      help=tx("bt.custom.name.help"))
    st.select_slider(lbl("bt.tenor"), TENORS, key="bt_tenor", format_func=lambda d: f"{d}D", help=tx("bt.tenor.help"))
    if strategy in USES_CALL:
        st.number_input(lbl("bt.otm_call"), 0.0, 50.0, step=1.0, format="%.1f", key="bt_otm_call",
                        help=tx("bt.otm_call.help"))
    if strategy in USES_PUT:
        st.number_input(lbl("bt.otm_put"), 0.0, 50.0, step=1.0, format="%.1f", key="bt_otm_put",
                        help=tx("bt.otm_put.help"))
    if strategy == "iron_condor":
        st.number_input(lbl("bt.wing"), 0.5, 50.0, step=1.0, format="%.1f", key="bt_wing", help=tx("bt.wing.help"))
    if strategy in TEMPLATE_NAMES and strategy != "buy_and_hold":
        st.html('<div style="height:0.6rem"></div>')
        panel_title(tx("bt.sizes"))
        base_legs = template_legs(strategy)
        size_cols = st.columns(2, gap="small")
        for i, leg in enumerate(base_legs):
            side = t(f"bt.custom.side.{'buy' if leg.quantity > 0 else 'sell'}")
            s.setdefault(_size_key(strategy, i), 1.0)
            with size_cols[i % 2]:
                st.number_input(upper(f"{side} {t(f'bt.custom.kind.{leg.kind}')}"), 0.5, MAX_QUANTITY, step=0.5,
                                format="%g", key=_size_key(strategy, i), help=tx("bt.sizes.help"))
    if strategy != "buy_and_hold":
        st.html('<div style="height:0.6rem"></div>')
        panel_title(tx("bt.exits"))
        st.toggle(lbl("bt.exits.toggle"), key="bt_exits", help=tx("bt.exits.help"))
        if s["bt_exits"]:
            tp_col, sl_col = st.columns(2, gap="small")
            with tp_col:
                st.number_input(lbl("bt.tp"), 0.0, 1000.0, step=10.0, format="%.0f", key="bt_tp", help=tx("bt.tp.help"))
            with sl_col:
                st.number_input(lbl("bt.sl"), 0.0, 1000.0, step=25.0, format="%.0f", key="bt_sl", help=tx("bt.sl.help"))
            st.caption(t("bt.exits.note"))

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

def _fmt_pct(x: float, digits: int = 1) -> str:
    return "–" if x is None or not math.isfinite(x) else f"{100 * x:+.{digits}f}%".replace("-", "−")


def _signed_colour(v: float) -> str:
    """Table cell colour: green for a gain, red for a loss."""
    if not isinstance(v, (int, float)) or v == 0 or not math.isfinite(v):
        return ""
    pal = palette()
    return f"color: {pal.positive if v > 0 else pal.negative}"


def render_comparison(entries: list[dict], hist: PriceHistory, window: tuple, base: dict, divs: np.ndarray,
                      report: Report) -> None:
    """Up to four strategies on the same stock, dates and assumptions: list, table, overlaid charts, report."""
    p = palette()
    report.title = t("bt.cmp.report_title")
    if not entries:
        st.info(t("bt.cmp.empty"))
        return
    section(tx("bt.cmp.title"))
    runs = []
    for i, e in enumerate(entries):
        colour = COMPARE_COLOURS[i % len(COMPARE_COLOURS)]
        exits = (t("bt.cmp.exits", tp=f"{100 * e['tp']:g}%" if e["tp"] else t("bt.cmp.off"),
                   sl=f"{100 * e['sl']:g}%" if e["sl"] else t("bt.cmp.off")) if (e["tp"] or e["sl"]) else "")
        legs = legs_from_code(e["legs"])
        meta = " · ".join(x for x in (describe_legs(legs, short=True), upper(t("bt.cmp.rolls", tenor=e["tenor"])),
                                      exits) if x)
        with st.container(horizontal=True, gap="small", vertical_alignment="center", key=f"bt_cmp_row_{i}"):
            st.html(f'<div class="opl-cmp-row"><i style="background:{colour}"></i><b>{html.escape(e["name"])}</b>'
                    f'<span>{html.escape(meta)}</span></div>')
            st.button(upper(t("bt.cmp.remove")), key=f"bt_cmp_rm_{i}", on_click=_remove_compare, args=(i,),
                      type="tertiary")
        try:
            cfg = BacktestConfig(legs=legs, tenor_days=e["tenor"], take_profit=e["tp"], stop_loss=e["sl"], **base)
            res = run_backtest(hist.dates, hist.close, cfg, dividends=divs, start=pd.Timestamp(window[0]),
                               end=pd.Timestamp(window[1]))
        except ValueError as exc:
            st.warning(t("bt.cmp.error", name=e["name"], error=exc))
            continue
        runs.append((e, cfg, res, colour))
    st.button(upper(t("bt.cmp.clear")), key="bt_cmp_clear", on_click=_clear_compare, type="tertiary")
    if not runs:
        return

    first = runs[0][2]
    bench = performance(first.benchmark, first.dates, base["rate"])
    bh_name = t("bt.bh_long", ticker=hist.label)
    rows = []
    for e, cfg, res, _ in runs:
        perf = performance(res.value, res.dates, base["rate"])
        rows.append({
            "strategy": e["name"], "total": 100 * perf["total_return"], "annual": 100 * perf["annual_return"],
            "vol": 100 * perf["annual_volatility"], "sharpe": perf["sharpe"], "dd": -100 * perf["max_drawdown"],
            "win": 100 * res.win_rate if res.cycles else float("nan"), "premium": res.total_premium,
            "costs": res.total_costs, "early": sum(c.exit_reason != "expiry" for c in res.cycles),
        })
    rows.append({"strategy": bh_name, "total": 100 * bench["total_return"], "annual": 100 * bench["annual_return"],
                 "vol": 100 * bench["annual_volatility"], "sharpe": bench["sharpe"], "dd": -100 * bench["max_drawdown"],
                 "win": float("nan"), "premium": 0.0, "costs": 0.0, "early": 0})
    frame = pd.DataFrame(rows)

    section(tx("bt.cmp.table"))
    styled = (frame.style.map(_signed_colour, subset=["total", "annual", "sharpe", "premium"])
              .map(lambda v: f"color: {p.negative}" if isinstance(v, float) and v < 0 else "", subset=["dd"])
              .format("{:.0f}", na_rep="–", subset=["win"]))
    st.dataframe(styled, hide_index=True, width="stretch", column_config={
        "strategy": st.column_config.TextColumn(t("bt.cmp.col.strategy"), pinned=True),
        "total": st.column_config.NumberColumn(t("bt.cmp.col.total"), format="%+.1f"),
        "annual": st.column_config.NumberColumn(t("bt.cmp.col.annual"), format="%+.1f"),
        "vol": st.column_config.NumberColumn(t("bt.cmp.col.vol"), format="%.1f"),
        "sharpe": st.column_config.NumberColumn(t("bt.cmp.col.sharpe"), format="%.2f"),
        "dd": st.column_config.NumberColumn(t("bt.cmp.col.dd"), format="%.1f"),
        "win": st.column_config.NumberColumn(t("bt.cmp.col.win"), format="%.0f"),
        "premium": st.column_config.NumberColumn(t("bt.cmp.col.premium"), format="%+.2f"),
        "costs": st.column_config.NumberColumn(t("bt.cmp.col.costs"), format="%.2f"),
        "early": st.column_config.NumberColumn(t("bt.cmp.col.early"), format="%d"),
    })
    strategies = frame.iloc[:-1]
    best_ret = strategies.loc[strategies["total"].idxmax()]
    finite_sharpe = strategies.dropna(subset=["sharpe"])
    best_sharpe = finite_sharpe.loc[finite_sharpe["sharpe"].idxmax()] if len(finite_sharpe) else None
    finite_dd = strategies.dropna(subset=["dd"])
    best_dd = finite_dd.loc[finite_dd["dd"].idxmax()] if len(finite_dd) else None
    explain(t("bt.cmp.best", ret_name=best_ret["strategy"], ret=f"{best_ret['total']:+.1f}%".replace("-", "−"),
              sharpe_name=best_sharpe["strategy"] if best_sharpe is not None else "–",
              sharpe=f"{best_sharpe['sharpe']:.2f}" if best_sharpe is not None else "–",
              dd_name=best_dd["strategy"] if best_dd is not None else "–",
              dd=f"{best_dd['dd']:.1f}%".replace("-", "−") if best_dd is not None else "–"))
    st.html(f'<p class="opl-note">{html.escape(t("bt.caveat"))}</p>')

    section(tx("bt.equity"))
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=first.dates, y=100 * first.benchmark / first.benchmark[0], name=bh_name,
                                line=dict(color=p.label, width=1.4, dash="dash"), hovertemplate="%{y:.1f}"))
    for e, _, res, colour in runs:
        fig_eq.add_trace(go.Scatter(x=res.dates, y=100 * res.value / res.value[0], name=e["name"],
                                    line=dict(color=colour, width=1.8), hovertemplate="%{y:.1f}"))
    style_figure(fig_eq, height=360, y_title=tx("bt.equity.y"))
    show(fig_eq, key="bt_cmp_equity")

    section(tx("bt.drawdown_chart"))
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=first.dates, y=100 * (first.benchmark / np.maximum.accumulate(first.benchmark) - 1),
                                name=bh_name, line=dict(color=p.label, width=1.2, dash="dash"), hovertemplate="%{y:.1f}%"))
    for e, _, res, colour in runs:
        fig_dd.add_trace(go.Scatter(x=res.dates, y=100 * (res.value / np.maximum.accumulate(res.value) - 1),
                                    name=e["name"], line=dict(color=colour, width=1.4), hovertemplate="%{y:.1f}%"))
    style_figure(fig_dd, height=280, y_title=tx("bt.drawdown.y"))
    show(fig_dd, key="bt_cmp_drawdown")

    paper_panel(hist, first.dates, [(e["name"], cfg) for e, cfg, _, _ in runs])

    daily = pd.DataFrame({"date": first.dates.date, "buy_and_hold": first.benchmark,
                          **{e["name"]: res.value for e, _, res, _ in runs}})
    st.download_button(upper(t("bt.cmp.download")), daily.to_csv(index=False), f"comparison-{hist.label}-daily.csv",
                       "text/csv", key="bt_cmp_dl", on_click="ignore")

    report.subtitle = f"{len(runs)} strategies on {hist.label}, {first.dates[0].date()} to {first.dates[-1].date()}"
    report.data_source = f"{hist.source}, daily closes and dividends for {hist.label} up to {hist.last_date}."
    cfg0 = runs[0][1]
    report.params(t("bt.report.setup"), {
        "Underlying": hist.label, "Period": f"{first.dates[0].date()} to {first.dates[-1].date()}",
        "Volatility": f"trailing {cfg0.vol_window}-day realised, x{1 + cfg0.vol_premium:.2f}",
        "Risk-free rate": f"{cfg0.rate:.2%}", "Dividend yield (pricing)": f"{cfg0.dividend_yield:.2%}",
        "Bid-ask spread": f"{cfg0.spread:.1%} of option price (half paid per trade)",
        "Commission": f"${100 * cfg0.commission:.2f} per contract",
        "Strike rounding": "exact" if cfg0.strike_step == 0 else f"${cfg0.strike_step:g}",
    })
    report.table("Strategies", pd.DataFrame([{
        "Strategy": e["name"], "Legs": describe_legs(cfg.legs), "Roll every (days)": cfg.tenor_days,
        "Take profit": f"{100 * cfg.take_profit:g}% of premium" if cfg.take_profit else "off",
        "Stop loss": f"{100 * cfg.stop_loss:g}% of premium" if cfg.stop_loss else "off",
    } for e, cfg, _, _ in runs]))
    report.table(t("bt.cmp.table.pro"), frame.rename(columns={
        "strategy": "Strategy", "total": "Total return %", "annual": "Annual return %", "vol": "Volatility %",
        "sharpe": "Sharpe", "dd": "Max drawdown %", "win": "Win rate %", "premium": "Net premium $",
        "costs": "Costs $", "early": "Closed early"}))
    report.figure(t("bt.equity.pro"), fig_eq)
    report.figure(t("bt.drawdown_chart.pro"), fig_dd)
    report.text(t("bt.report.method"), t("bt.report.method_body"))


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
        hist = parse.parse_price_file(uploaded.getvalue(), uploaded.name)
    except MarketDataError as exc:
        error = str(exc)

with right:
    entries = _compare_entries()
    with st.container(horizontal=True, gap="small", vertical_alignment="center", key="bt_viewbar"):
        view = st.segmented_control(
            lbl("bt.view.single"), ["single", "compare"], key="bt_view", required=True, label_visibility="collapsed",
            format_func=lambda v: upper(tx(f"bt.view.{v}", n=len(entries))),
        )
        st.button(upper(t("bt.cmp.add")), key="bt_cmp_add", on_click=_add_to_compare, help=tx("bt.cmp.add.help"),
                  disabled=len(entries) >= MAX_COMPARE or (strategy == "custom" and not custom_legs))
    if error:
        st.error(error)
    if view == "single" and strategy == "custom" and not custom_legs:
        st.info(t("bt.custom.empty"))
        st.stop()
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
    sizes = _sizes(strategy) if strategy in TEMPLATE_NAMES else []
    if sizes and any(x != 1 for x in sizes):
        s["bt_qty"] = sizes_to_code(sizes)
    else:
        s.pop("bt_qty", None)
    base = dict(
        vol_window=int(s["bt_window"]),
        vol_premium=float(s["bt_vol_premium"]) / 100,
        rate=float(s["bt_rate"]) / 100,
        dividend_yield=q,
        spread=float(s["bt_spread"]) / 100,
        commission=float(s["bt_commission"]) / 100,  # dollars per contract -> per share
        strike_step=float(s["bt_strike_step"]),
    )
    divs = dividends_on_dates(hist).to_numpy()
    if view == "compare":
        render_comparison(entries, hist, window, base, divs, report)
        finish_page(actions)
        st.stop()

    take_profit, stop_loss = _exit_levels()
    config = BacktestConfig(
        legs=tuple(custom_legs) if strategy == "custom"
        else sized_legs(template_legs(strategy, s["bt_otm_call"] / 100, s["bt_otm_put"] / 100, s["bt_wing"] / 100),
                        sizes),
        tenor_days=int(s["bt_tenor"]),
        take_profit=take_profit,
        stop_loss=stop_loss,
        **base,
    )
    try:
        result = run_backtest(hist.dates, hist.close, config, dividends=divs,
                              start=pd.Timestamp(window[0]), end=pd.Timestamp(window[1]))
    except ValueError as exc:
        st.warning(str(exc))
        st.stop()

    stats = performance(result.value, result.dates, config.rate)
    bench = performance(result.benchmark, result.dates, config.rate)
    p = palette()
    strat_name = _strategy_name(strategy)

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
    exits_on = take_profit is not None or stop_loss is not None
    if exits_on and result.cycles:
        reasons = [c.exit_reason for c in result.cycles]
        explain(t("bt.exits.summary", early=sum(r != "expiry" for r in reasons), total=len(reasons),
                  tp=reasons.count("take profit"), sl=reasons.count("stop loss")))
    paper_panel(hist, result.dates, [(strat_name, config)])
    if upside_exposure(config.legs) < 0:
        st.warning(t("bt.custom.unlimited"))
    if np.min(result.value) <= 0:
        st.warning(t("bt.custom.blown"))

    # --------------------------------------------------------------- one cycle at expiry
    fig_po = None
    if any(leg.kind != "stock" for leg in config.legs):
        section(tx("bt.payoff"), tx("bt.payoff.lede"))
        hv = rolling_volatility(hist.close, config.vol_window)
        hv_now = hv[min(int(hist.dates.searchsorted(result.dates[-1])), len(hv) - 1)]
        sigma_now = max(float(hv_now) * (1 + config.vol_premium), config.vol_floor)
        strikes = [100 * leg.moneyness for leg in config.legs if leg.kind != "stock"]
        grid = np.linspace(min(70.0, min(strikes) - 15), max(130.0, max(strikes) + 15), 401)
        pnl_po = cycle_payoff(config.legs, grid, config.tenor_days, config.rate, sigma_now, q)
        fig_po = go.Figure()
        fig_po.add_trace(go.Scatter(x=grid, y=np.maximum(pnl_po, 0), fill="tozeroy", fillcolor=p.positive_fill,
                                    line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig_po.add_trace(go.Scatter(x=grid, y=np.minimum(pnl_po, 0), fill="tozeroy", fillcolor=p.negative_fill,
                                    line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig_po.add_trace(go.Scatter(x=grid, y=pnl_po, name=strat_name, line=dict(color=p.ink, width=2),
                                    hovertemplate="%{x:.0f}%: %{y:+.2f}<extra></extra>"))
        fig_po.add_vline(x=100, line=dict(color=p.accent, width=1, dash="dot"), annotation_text=upper(t("bt.payoff.today")),
                         annotation_position="bottom right", annotation_font_size=11)
        style_figure(fig_po, height=280, x_title=tx("bt.payoff.x"), y_title=tx("bt.payoff.y"), legend=False,
                     hovermode="closest")
        show(fig_po, key="bt_payoff_chart")

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
    if len(log):
        if exits_on:
            log["exit"] = [t(f"bt.exit.{r}") for r in log["exit"]]
        else:
            log = log.drop(columns=["closed", "exit"])
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
        styled = log.style.map(_signed_colour, subset=["premium", "payoff", "pnl"])
        st.dataframe(styled, hide_index=True, width="stretch", height=280, column_config={
            "open": st.column_config.DateColumn(t("bt.col.open")),
            "expiry": st.column_config.DateColumn(t("bt.col.expiry")),
            "closed": st.column_config.DateColumn(t("bt.col.closed")),
            "exit": st.column_config.TextColumn(t("bt.col.exit")),
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
        "Exit rules": "none (held to expiry)" if not exits_on else ", ".join(x for x in (
            f"take profit at {100 * take_profit:g}% of premium" if take_profit else "",
            f"stop loss at {100 * stop_loss:g}% of premium" if stop_loss else "") if x),
    })
    report.metrics(t("bt.report.results"), [
        (f"{t('bt.total_return.pro')}", pct(stats["total_return"])), (f"{t('bt.bh_short')} total", pct(bench["total_return"])),
        ("Annual return", pct(stats["annual_return"])), (f"{t('bt.bh_short')} annual", pct(bench["annual_return"])),
        ("Volatility", pct(stats["annual_volatility"]).lstrip("+")), ("Sharpe", num(stats["sharpe"])),
        ("Max drawdown", pct(-stats["max_drawdown"])), ("Win rate", "–" if not result.cycles else f"{100 * result.win_rate:.0f}%"),
    ])
    if fig_po is not None:
        report.figure(t("bt.payoff.pro"), fig_po)
    report.figure(t("bt.equity.pro"), fig_eq)
    report.figure(t("bt.drawdown_chart.pro"), fig_dd)
    if fig_cy is not None:
        report.figure(t("bt.cycle_chart.pro"), fig_cy)
        report.table(t("bt.log.pro"), log)
    report.text(t("bt.report.method"), t("bt.report.method_body"))

finish_page(actions)
