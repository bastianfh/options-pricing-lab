"""Payoff & P&L: expiry payoff and mark-to-model P&L for single and multi-leg strategies."""

from __future__ import annotations

import html
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.content import t
from app.theme import palette, show, style_figure
from app.ui import cells, explain, input_panel, is_pro, lbl, page_header, panel, panel_title, preset_pills, section, tx, upper
from pricing.greeks import GREEK_NAMES
from pricing.strategies import PRESETS, Leg, from_legs, risk_summary

page_header("pay.title", "pay.lede")
if not is_pro():
    preset_pills()

STRATEGIES = list(PRESETS) + ["custom"]
NEEDS_WIDTH = {"strangle", "bull_call_spread", "bear_put_spread"}

left, right = st.columns([1, 2.3], gap="large")
with left, panel("pay_inputs"):
    panel_title(tx("pay.strategy"))
    st.session_state.setdefault("pay_strategy", "straddle")
    strategy_key = st.selectbox(
        lbl("pay.strategy"), STRATEGIES, format_func=lambda k: upper(tx(f"strategy.{k}")), key="pay_strategy",
        label_visibility="collapsed", persist_state="session",
    )
    spot_now = float(st.session_state.get("in_S", 100.0))
    is_fx = st.session_state.get("in_asset") == "fx"
    st.session_state.setdefault("pay_center", spot_now)
    st.session_state.setdefault("pay_width", round(spot_now * 0.05, 4 if is_fx else 0))
    fmt = "%.4f" if is_fx else "%.2f"
    step = 0.001 if is_fx else 1.0
    if strategy_key != "custom":
        st.number_input(lbl("pay.center"), min_value=1e-4, step=step, format=fmt, key="pay_center",
                        help=tx("pay.center.help"), persist_state="session")
        if strategy_key in NEEDS_WIDTH:
            st.number_input(lbl("pay.width"), min_value=step, step=step, format=fmt, key="pay_width",
                            help=tx("pay.width.help"), persist_state="session")
    st.html('<div style="height:0.8rem"></div>')
    panel_title(tx("inputs.market"))
    spec, _, ctx = input_panel(contract=False, numerics=False, strike=False)
    days_total = int(st.session_state["in_days"])
    st.session_state.setdefault("pay_horizon", days_total // 2)
    if st.session_state["pay_horizon"] >= days_total:
        st.session_state["pay_horizon"] = max(days_total // 2, 0)
    horizon = st.slider(lbl("pay.horizon"), 0, max(days_total - 1, 1), key="pay_horizon",
                        help=tx("pay.horizon.help"), persist_state="session")

center = float(st.session_state["pay_center"])
width = float(st.session_state["pay_width"])

# ------------------------------------------------------------- strategy
if strategy_key == "custom":
    with right:
        section(tx("pay.legs.title"), t("pay.legs.custom_hint"))
        default = pd.DataFrame(
            [{"Instrument": "call", "Quantity": 1.0, "Strike": round(spec.S * 0.95, 4)},
             {"Instrument": "call", "Quantity": -2.0, "Strike": round(spec.S, 4)},
             {"Instrument": "call", "Quantity": 1.0, "Strike": round(spec.S * 1.05, 4)}]
        )
        edited = st.data_editor(
            st.session_state.get("pay_custom_df", default),
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="pay_custom_editor",
            column_config={
                "Instrument": st.column_config.SelectboxColumn(options=["call", "put", "stock"], required=True),
                "Quantity": st.column_config.NumberColumn(step=1.0, format="%.2f"),
                "Strike": st.column_config.NumberColumn(min_value=0.0001, format="%.4f" if ctx.is_fx else "%.2f"),
            },
        )
        st.session_state["pay_custom_df"] = edited
        legs = [
            Leg(str(r.Instrument), float(r.Quantity), float(r.Strike) if r.Instrument != "stock" else 0.0)
            for r in edited.dropna(subset=["Instrument", "Quantity"]).itertuples()
            if r.Instrument in ("call", "put", "stock") and (r.Instrument == "stock" or (r.Strike or 0) > 0)
        ]
        strategy = from_legs(tx("strategy.custom"), legs)
else:
    strategy = PRESETS[strategy_key](center, width)

if not strategy.legs:
    with right:
        st.info(t("pay.legs.custom_hint"))
    st.stop()

# ------------------------------------------------------------- analytics
r, sigma, q, T = spec.r, spec.sigma, spec.q, spec.T
cost = strategy.cost(spec.S, T, r, sigma, q)
strikes = [leg.strike for leg in strategy.legs if leg.kind != "stock"] or [spec.S]
sd = sigma * math.sqrt(max(T, 1 / 365))
lo = min(spec.S * math.exp(-3.2 * sd), min(strikes) * 0.85)
hi = max(spec.S * math.exp(3.2 * sd), max(strikes) * 1.15)
grid = np.linspace(lo, hi, 700)
pnl_expiry = strategy.pnl_at_expiry(grid, cost)
pnl_today = strategy.pnl_before_expiry(grid, T, r, sigma, cost, q)
summary = risk_summary(strategy, cost, grid)
p = palette()

with right:
    # ---------------------------------------------------- headline numbers
    with st.container(key="pay_metrics"):
        cost_label = tx("pay.cost.debit") if cost >= 0 else tx("pay.cost.credit")
        mp = tx("pay.unlimited") if summary.max_profit is None else ctx.money(summary.max_profit)
        ml = tx("pay.unlimited") if summary.max_loss is None else ctx.money(summary.max_loss)
        be = summary.breakevens
        be_txt = " / ".join(ctx.spot(b) for b in be[:2]) if be else t("pay.none")
        st.html(cells([
            (cost_label, ctx.money(abs(cost)), "", "acc"),
            (tx("pay.max_profit"), upper(mp), "", "pos"),
            (tx("pay.max_loss"), upper(ml), "", "neg"),
            (tx("pay.breakeven"), be_txt, "", ""),
        ]))
        summary_txt = t(f"strategy.{strategy_key}.summary")
        if is_pro():
            g = strategy.greeks(spec.S, T, r, sigma, q)
            st.html(f'<p class="opl-note">{html.escape(tx("strategy." + strategy_key))}: '
                    + ", ".join(f"{t(f'greek.{n}.short')} {v:+.4f}" for n, v in
                                 zip(GREEK_NAMES, (g.delta, g.gamma, g.vega / 100, g.theta / 365, g.rho / 100)))
                    + "</p>")
        else:
            explain(tx("pay.explain", summary=summary_txt))

    # ------------------------------------------------------------- chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid, y=np.where(pnl_expiry >= 0, pnl_expiry, 0), fill="tozeroy",
                             fillcolor=p.gain_fill, line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=grid, y=np.where(pnl_expiry < 0, pnl_expiry, 0), fill="tozeroy",
                             fillcolor=p.loss_fill, line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_hline(y=0, line=dict(color=p.muted, width=1, dash="dash"))
    fig.add_trace(go.Scatter(x=grid, y=pnl_expiry, name=tx("pay.chart.expiry"),
                             line=dict(color=p.ink, width=2), hovertemplate="%{y:,.4f}"))
    if 0 < horizon < days_total:
        pnl_h = strategy.pnl_before_expiry(grid, T - horizon / 365, r, sigma, cost, q)
        fig.add_trace(go.Scatter(x=grid, y=pnl_h, name=tx("pay.chart.horizon", d=horizon),
                                 line=dict(color=p.series[1], width=2, dash="dash"), hovertemplate="%{y:,.4f}"))
    fig.add_trace(go.Scatter(x=grid, y=pnl_today, name=tx("pay.chart.today"),
                             line=dict(color=p.accent, width=2.5), hovertemplate="%{y:,.4f}"))
    if be:
        fig.add_trace(go.Scatter(x=be, y=[0] * len(be), mode="markers", name=tx("pay.breakeven"),
                                 marker=dict(color=p.accent, size=8, symbol="diamond", line=dict(color=p.canvas, width=1.5)),
                                 hovertemplate="%{x:,.4f}"))
    fig.add_vline(x=spec.S, line=dict(color=p.accent, width=1, dash="dot"),
                  annotation_text=tx("pricer.chart.spot"), annotation_position="bottom right", annotation_font_size=11)
    style_figure(fig, height=420, x_title=tx("pay.chart.x"), y_title=tx("pay.chart.y"))
    show(fig, key="pay_chart")

    # -------------------------------------------------------------- legs
    l_col, g_col = st.columns([1.5, 1], gap="medium")
    with l_col:
        section(tx("pay.legs.title"))
        rows = []
        for leg in strategy.legs:
            side = tx("pay.leg.long") if leg.quantity > 0 else tx("pay.leg.short")
            if leg.kind == "stock":
                inst, strike_txt, prem = tx("pay.leg.stock"), "–", spec.S
            else:
                inst = tx(f"in.option_type.{leg.kind}")
                strike_txt = ctx.spot(leg.strike)
                prem = float(Leg(leg.kind, 1, leg.strike).value(np.array(spec.S), T, r, sigma, q))
            rows.append({t("pay.col.side"): side, t("pay.col.qty"): abs(leg.quantity),
                         t("pay.col.instrument"): inst, t("pay.col.strike"): strike_txt,
                         t("pay.col.premium"): ctx.money(prem)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with g_col:
        section(tx("pay.greeks.title"))
        g = strategy.greeks(spec.S, T, r, sigma, q)
        values = dict(zip(GREEK_NAMES, (g.delta, g.gamma, g.vega / 100, g.theta / 365, g.rho / 100)))
        greek_rows = [{"": tx(f"greek.{n}.name"), "Value": round(v, 4)} for n, v in values.items()]
        st.dataframe(pd.DataFrame(greek_rows), hide_index=True, width="stretch",
                     column_config={"Value": st.column_config.NumberColumn(format="%.4f")})
