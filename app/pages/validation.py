"""Validation: convergence of every numerical method to Black-Scholes, error tables and consistency checks."""

from __future__ import annotations

import html
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app.content import t
from app.theme import DASHES, MARKERS, palette, show, style_figure
from app.ui import cached, card, count_tests, explain, is_pro, page_header, section, stat, tx
from pricing.convergence import (
    MC_VARIANTS,
    binomial_study,
    empirical_order,
    monte_carlo_study,
    pde_study,
    standard_error_order,
)
from pricing.engine import Method, NumericalSettings, OptionSpec, greeks, price
from pricing.greeks import GREEK_NAMES
from pricing.implied_vol import implied_volatility_solve, price_bounds
from pricing.models.binomial import binomial_price
from pricing.models.black_scholes import black_scholes_price
from pricing.models.finite_difference import finite_difference_price

page_header("val.title", "val.lede")

CASES = {
    "atm": dict(S=100.0, K=100.0),
    "otm": dict(S=100.0, K=110.0),
    "itm": dict(S=100.0, K=90.0),
}
CASE_LABELS = {
    "atm": {"Plain English": "Agreed price = today's price", "Pro": "ATM (K = 100)"},
    "otm": {"Plain English": "Agreed price above today's", "Pro": "OTM call (K = 110)"},
    "itm": {"Plain English": "Agreed price below today's", "Pro": "ITM call (K = 90)"},
}

c1, c2 = st.columns([2, 1], gap="large")
with c1:
    case = st.segmented_control(
        tx("val.case"), list(CASES), format_func=lambda c: CASE_LABELS[c]["Pro" if is_pro() else "Plain English"],
        key="val_case", default="atm", required=True, help=t("val.case.help"), persist_state="session",
        width="stretch",
    )
with c2:
    opt = st.segmented_control(
        tx("in.option_type.label"), ["call", "put"], format_func=lambda v: tx(f"in.option_type.{v}"),
        key="val_type", default="call", required=True, persist_state="session", width="stretch",
    )
spec = OptionSpec(T=1.0, r=0.05, sigma=0.20, q=0.02, option_type=opt, **CASES[case])
bs = float(black_scholes_price(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type))
st.caption(
    f"S = {spec.S:g} · K = {spec.K:g} · T = {spec.T:g} · r = {spec.r:.0%} · σ = {spec.sigma:.0%} · "
    f"q = {spec.q:.0%} · {spec.option_type.value} · Black-Scholes = {bs:.6f}"
)

BIN_DENSE = np.unique(np.geomspace(10, 2000, 45).astype(int))
BIN_ZIGZAG = np.arange(10, 201)
PDE_GRIDS = np.array([25, 50, 100, 200, 400, 800])
MC_PATHS = np.array([1_000, 3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000])


@cached
def run_studies(spec: OptionSpec):
    return (
        binomial_study(spec, BIN_DENSE),
        binomial_study(spec, BIN_ZIGZAG),
        pde_study(spec, PDE_GRIDS),
        monte_carlo_study(spec, MC_PATHS),
    )


@cached
def american_study(spec: OptionSpec):
    am = spec.with_(option_type="put", exercise="american")
    steps = np.array([50, 100, 200, 400, 800, 1600, 3200])
    grids = np.array([50, 100, 200, 400, 800, 1600])
    tree = np.array([binomial_price(am.S, am.K, am.T, am.r, am.sigma, am.q, "put", "american", int(n)) for n in steps])
    pde = np.array([finite_difference_price(am.S, am.K, am.T, am.r, am.sigma, am.q, "put", "american", int(n), int(n))
                    for n in grids])
    rows = []
    for s0 in (80.0, 90.0, 100.0, 110.0, 120.0):
        t_val = binomial_price(s0, am.K, am.T, am.r, am.sigma, am.q, "put", "american", 3200)
        p_val = finite_difference_price(s0, am.K, am.T, am.r, am.sigma, am.q, "put", "american", 1600, 1600)
        euro = float(black_scholes_price(s0, am.K, am.T, am.r, am.sigma, am.q, "put"))
        rows.append((s0, t_val, p_val, abs(t_val - p_val), t_val - euro))
    return steps, tree, grids, pde, rows


@cached
def greeks_table(spec: OptionSpec):
    settings = NumericalSettings(binomial_steps=1000, mc_paths=500_000, pde_space_steps=400, pde_time_steps=400)
    return {m: greeks(spec, m, settings) for m in Method}


@cached
def parity_table(spec: OptionSpec):
    settings = NumericalSettings(binomial_steps=1000, mc_paths=500_000)
    out = {}
    for m in Method:
        c = price(spec.with_(option_type="call"), m, settings).price
        p_ = price(spec.with_(option_type="put"), m, settings).price
        out[m] = c - p_ - (spec.S * math.exp(-spec.q * spec.T) - spec.K * math.exp(-spec.r * spec.T))
    return out


@cached
def iv_round_trip():
    S, r, q = 100.0, 0.03, 0.01
    n = vol_err = price_err = bisect = 0.0
    for kind in ("call", "put"):
        for K in (60, 80, 90, 100, 110, 120, 150):
            for T in (0.02, 0.1, 0.25, 1.0, 3.0):
                for sigma in (0.05, 0.1, 0.2, 0.4, 0.8, 1.5):
                    p_ = float(black_scholes_price(S, K, T, r, sigma, q, kind))
                    if p_ - price_bounds(S, K, T, r, q, kind)[0] < 1e-4:
                        continue
                    res = implied_volatility_solve(p_, S, K, T, r, q, kind)
                    n += 1
                    vol_err = max(vol_err, abs(res.sigma - sigma))
                    price_err = max(price_err, abs(float(black_scholes_price(S, K, T, r, res.sigma, q, kind)) - p_))
                    bisect += res.bisection_steps > 0
    return int(n), vol_err, price_err, int(bisect)


with st.spinner(t("val.running")):
    bin_dense, bin_zig, pde, mc = run_studies(spec)

p = palette()
names_mc = {k: tx(f"val.mc.variant.{k}") for k in MC_VARIANTS}
best_mc = mc.studies["antithetic_control_variate"]
plain_mc = mc.studies["plain"]

# --------------------------------------------------------------- summary
section(tx("val.summary.title"))
orders = {
    "binomial": (bin_dense.order, 1.0, 0.3, abs(bin_dense.errors[-1]), f"N = {BIN_DENSE[0]}…{BIN_DENSE[-1]}"),
    "finite_difference": (pde.order, 2.0, 0.25, abs(pde.errors[-1]), f"M = N = {PDE_GRIDS[0]}…{PDE_GRIDS[-1]}"),
    "monte_carlo": (standard_error_order(best_mc), 0.5, 0.1, best_mc.std_errors[-1],
                    f"n = {MC_PATHS[0]:,}…{MC_PATHS[-1]:,}"),
}
with card("val_summary"):
    cols = st.columns(3)
    for col, (m, (measured, expected, tol, final, res)) in zip(cols, orders.items()):
        ok = abs(measured - expected) < tol
        label = tx(f"method.{m}")
        sub = tx("val.summary.sub", expected=f"{expected:g}", final=f"{final:.1e}",
                 what="SE" if m == "monte_carlo" else "error", check=t("val.pass") if ok else t("val.fail"))
        col.html(stat(label + t("val.summary.order_suffix") if is_pro() else label, f"{measured:.2f}", sub=sub,
                      size="lg", tone="gain" if ok else "loss"))
    if is_pro():
        df = pd.DataFrame([
            {t("val.col.method"): t(f"method.{m}", "Pro"), t("val.col.resolution"): res,
             t("val.col.expected"): expected, t("val.col.measured"): round(measured, 3),
             t("val.col.final_error"): f"{final:.2e}",
             t("val.col.status"): t("val.pass") if abs(measured - expected) < tol else t("val.fail")}
            for m, (measured, expected, tol, final, res) in orders.items()
        ])
        st.dataframe(df, hide_index=True, width="stretch")
    else:
        explain(t("val.summary.explain"))


def ref_line(n: np.ndarray, anchor: float, p_: float) -> np.ndarray:
    return anchor * (n / n[0]) ** (-p_)


# ------------------------------------------------------- work-precision
section(tx("val.work.title"), tx("val.work.lede"))
fig = go.Figure()
series = [
    (tx("method.binomial"), bin_dense.runtime_ms[::3], np.abs(bin_dense.errors[::3])),
    (tx("method.monte_carlo") + (" (std. error)" if is_pro() else ""), best_mc.runtime_ms, best_mc.std_errors),
    (tx("method.finite_difference"), pde.runtime_ms, np.abs(pde.errors)),
]
for i, (name, x, y) in enumerate(series):
    fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines+markers",
                             line=dict(color=p.series[i], width=2, dash=DASHES[i]),
                             marker=dict(size=7, symbol=MARKERS[i], line=dict(color="white", width=1)),
                             hovertemplate="%{x:.2f} ms → %{y:.2e}<extra>" + name + "</extra>"))
fig.update_xaxes(type="log")
fig.update_yaxes(type="log", exponentformat="power")
style_figure(fig, height=400, x_title=tx("val.work.x"), y_title=tx("val.work.y"), hovermode="closest")
show(fig, key="val_work")

# --------------------------------------------------------------- binomial
section(tx("val.bin.title"), tx("val.bin.lede"))
b1, b2 = st.columns(2, gap="medium")
with b1:
    even = bin_zig.resolution % 2 == 0
    fig = go.Figure()
    fig.add_hline(y=bs, line=dict(color=p.reference, width=1.5, dash="dash"),
                  annotation_text=tx("val.exact"), annotation_position="top right", annotation_font_size=11)
    for i, (mask, label) in enumerate([(even, t("val.bin.even")), (~even, t("val.bin.odd"))]):
        fig.add_trace(go.Scatter(x=bin_zig.resolution[mask], y=bin_zig.prices[mask], name=label, mode="lines",
                                 line=dict(color=p.series[i], width=1.8, dash=DASHES[i]),
                                 hovertemplate="N=%{x}: %{y:.6f}"))
    style_figure(fig, height=330, x_title=tx("val.bin.x"), y_title=tx("val.price_y"))
    show(fig, key="val_bin_price")
with b2:
    err = np.abs(bin_dense.errors)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bin_dense.resolution, y=err, name="|error|", mode="lines+markers",
                             line=dict(color=p.series[0], width=1.5), marker=dict(size=5),
                             hovertemplate="N=%{x}: %{y:.2e}"))
    fig.add_trace(go.Scatter(x=bin_dense.resolution, y=ref_line(bin_dense.resolution, err.max() * 1.2, 1.0),
                             name=tx("val.ref_slope", p=1), line=dict(color=p.muted, width=1.5, dash="dot"),
                             hoverinfo="skip"))
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log", exponentformat="power")
    style_figure(fig, height=330, x_title=tx("val.bin.x"), y_title=tx("val.error_y"), hovermode="closest")
    show(fig, key="val_bin_err")
bin_table = pd.DataFrame({
    "N": BIN_DENSE, t("table.price"): bin_dense.prices, t("table.error"): bin_dense.errors,
    t("table.n_error"): BIN_DENSE * np.abs(bin_dense.errors), t("table.runtime"): bin_dense.runtime_ms,
}).iloc[::4]
with st.expander(tx("val.table"), expanded=is_pro()):
    st.dataframe(bin_table, hide_index=True, width="stretch", column_config={
        t("table.price"): st.column_config.NumberColumn(format="%.6f"),
        t("table.error"): st.column_config.NumberColumn(format="%.2e"),
        t("table.n_error"): st.column_config.NumberColumn(format="%.3f"),
        t("table.runtime"): st.column_config.NumberColumn(format="%.2f"),
    })

# ------------------------------------------------------------ monte carlo
section(tx("val.mc.title"), tx("val.mc.lede"))
m1, m2 = st.columns(2, gap="medium")
with m1:
    fig = go.Figure()
    fig.add_hline(y=bs, line=dict(color=p.reference, width=1.5, dash="dash"),
                  annotation_text=tx("val.exact"), annotation_position="top right", annotation_font_size=11)
    for i, key in enumerate(["plain", "antithetic_control_variate"]):
        study = mc.studies[key]
        color = p.series[i if i == 0 else 2]
        x = study.resolution * (1.0 if i == 0 else 1.08)  # slight offset so the bars don't overlap
        fig.add_trace(go.Scatter(
            x=x, y=study.prices, name=names_mc[key], mode="markers",
            marker=dict(size=8, color=color, symbol=MARKERS[i], line=dict(color="white", width=1)),
            error_y=dict(type="data", array=1.96 * study.std_errors, color=color, thickness=1.5, width=4),
            hovertemplate="n=%{x:,.0f}: %{y:.5f}",
        ))
    fig.update_xaxes(type="log")
    style_figure(fig, height=330, x_title=tx("val.mc.x"), y_title=tx("val.mc.price_y"), hovermode="closest")
    show(fig, key="val_mc_price")
with m2:
    fig = go.Figure()
    for i, (key, study) in enumerate(mc.studies.items()):
        fig.add_trace(go.Scatter(x=study.resolution, y=study.std_errors, name=names_mc[key], mode="lines+markers",
                                 line=dict(color=p.series[i], width=2, dash=DASHES[i]),
                                 marker=dict(size=6, symbol=MARKERS[i]), hovertemplate="%{y:.2e}"))
    fig.add_trace(go.Scatter(x=MC_PATHS, y=ref_line(MC_PATHS, plain_mc.std_errors[0] * 1.3, 0.5),
                             name=tx("val.ref_slope", p="1/2"), line=dict(color=p.muted, width=1.5, dash="dot"),
                             hoverinfo="skip"))
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log", exponentformat="power")
    style_figure(fig, height=330, x_title=tx("val.mc.x"), y_title=tx("val.mc.se_y"), hovermode="x unified")
    show(fig, key="val_mc_se")
mc_rows = []
for key, study in mc.studies.items():
    vrf = mc.variance_reduction_factor(key)
    mc_rows.append({
        t("val.col.method"): names_mc[key],
        f"SE @ {MC_PATHS[-1]:,}": study.std_errors[-1],
        t("table.error"): study.errors[-1],
        t("table.contains"): "✓" if abs(study.errors[-1]) <= 1.96 * study.std_errors[-1] else "✗",
        t("val.col.measured"): standard_error_order(study),
        t("val.mc.vrf"): float(np.median(vrf)),
    })
st.dataframe(pd.DataFrame(mc_rows), hide_index=True, width="stretch", column_config={
    f"SE @ {MC_PATHS[-1]:,}": st.column_config.NumberColumn(format="%.2e"),
    t("table.error"): st.column_config.NumberColumn(format="%+.2e"),
    t("val.col.measured"): st.column_config.NumberColumn("SE order", format="%.3f"),
    t("val.mc.vrf"): st.column_config.NumberColumn(format="%.1f×", help=t("val.mc.vrf_help")),
})

# -------------------------------------------------------------------- PDE
section(tx("val.pde.title"), tx("val.pde.lede"))
d1, d2 = st.columns([1.2, 1], gap="medium")
with d1:
    err = np.abs(pde.errors)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=PDE_GRIDS, y=err, name="|error|", mode="lines+markers",
                             line=dict(color=p.series[2], width=2), marker=dict(size=8, symbol="diamond"),
                             hovertemplate="M=%{x}: %{y:.2e}"))
    fig.add_trace(go.Scatter(x=PDE_GRIDS, y=ref_line(PDE_GRIDS, err[0] * 1.3, 2.0), name=tx("val.ref_slope", p=2),
                             line=dict(color=p.muted, width=1.5, dash="dot"), hoverinfo="skip"))
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log", exponentformat="power")
    style_figure(fig, height=330, x_title=tx("val.pde.x"), y_title=tx("val.error_y"), hovermode="closest")
    show(fig, key="val_pde")
with d2:
    ratios = ["–"] + [f"{a / b:.2f}" for a, b in zip(np.abs(pde.errors[:-1]), np.abs(pde.errors[1:]))]
    st.dataframe(pd.DataFrame({
        "M = N": PDE_GRIDS, t("table.price"): pde.prices, t("table.error"): pde.errors,
        t("table.ratio"): ratios, t("table.runtime"): pde.runtime_ms,
    }), hide_index=True, width="stretch", column_config={
        t("table.price"): st.column_config.NumberColumn(format="%.7f"),
        t("table.error"): st.column_config.NumberColumn(format="%.2e"),
        t("table.ratio"): st.column_config.TextColumn(help="Error(n/2) / Error(n); 4.0 = second order"),
        t("table.runtime"): st.column_config.NumberColumn(format="%.1f"),
    })

# --------------------------------------------------------------- american
section(tx("val.am.title"), tx("val.am.lede"))
steps, tree, grids, pde_am, am_rows = american_study(spec)
a1, a2 = st.columns([1.2, 1], gap="medium")
with a1:
    euro_am = float(black_scholes_price(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, "put"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=steps, y=tree, name=tx("method.binomial"), mode="lines+markers",
                             line=dict(color=p.series[0], width=2), marker=dict(size=7, symbol=MARKERS[0]),
                             hovertemplate="%{y:.6f}"))
    fig.add_trace(go.Scatter(x=grids, y=pde_am, name=tx("method.finite_difference"), mode="lines+markers",
                             line=dict(color=p.series[2], width=2, dash="dash"), marker=dict(size=7, symbol=MARKERS[2]),
                             hovertemplate="%{y:.6f}"))
    fig.add_hline(y=euro_am, line=dict(color=p.muted, width=1.2, dash="dot"),
                  annotation_text=tx("val.am.european"), annotation_position="bottom right", annotation_font_size=11)
    fig.update_xaxes(type="log")
    style_figure(fig, height=330, x_title=tx("val.am.x"), y_title=tx("val.price_y"), hovermode="closest")
    show(fig, key="val_am")
with a2:
    st.dataframe(pd.DataFrame(am_rows, columns=[
        "S", t("method.short.binomial"), t("method.short.finite_difference"), "|Δ|", tx("val.am.premium"),
    ]), hide_index=True, width="stretch", column_config={
        c: st.column_config.NumberColumn(format="%.4f") for c in
        [t("method.short.binomial"), t("method.short.finite_difference"), tx("val.am.premium")]
    } | {"|Δ|": st.column_config.NumberColumn(format="%.1e"), "S": st.column_config.NumberColumn(format="%.0f")})

# ----------------------------------------------------------------- greeks
section(tx("val.greeks.title"), tx("val.greeks.lede"))
gt = greeks_table(spec)
scale = {"vega": 0.01, "theta": 1 / 365, "rho": 0.01}
rows = []
for n in GREEK_NAMES:
    exact = getattr(gt[Method.BLACK_SCHOLES], n) * scale.get(n, 1)
    row = {"Greek": t(f"greek.{n}.name", "Pro"), t("pricer.greeks.col.analytical"): exact}
    worst = 0.0
    for m in (Method.BINOMIAL, Method.MONTE_CARLO, Method.FINITE_DIFFERENCE):
        v = getattr(gt[m], n) * scale.get(n, 1)
        row[t(f"method.short.{m.value}")] = v
        worst = max(worst, abs(v - exact))
    row[t("pricer.greeks.col.maxdiff")] = worst
    rows.append(row)
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
    c: st.column_config.NumberColumn(format="%.5f") for c in
    [t("pricer.greeks.col.analytical"), "CRR", "MC", "PDE"]
} | {t("pricer.greeks.col.maxdiff"): st.column_config.NumberColumn(format="%.1e")})

# ------------------------------------------------------- parity & IV
q1, q2 = st.columns(2, gap="medium")
with q1:
    section(tx("val.parity.title"), tx("val.parity.lede"))
    par = parity_table(spec)
    st.dataframe(pd.DataFrame([{t("val.col.method"): tx(f"method.{m.value}"), t("val.parity.col"): v}
                               for m, v in par.items()]),
                 hide_index=True, width="stretch",
                 column_config={t("val.parity.col"): st.column_config.NumberColumn(format="%+.2e")})
with q2:
    section(tx("val.iv.title"), tx("val.iv.lede"))
    n_iv, vol_err, price_err, n_bis = iv_round_trip()
    with card("val_iv"):
        i1, i2 = st.columns(2)
        i1.html(stat(t("val.iv.cases"), f"{n_iv}", size="md"))
        i2.html(stat(t("val.iv.max_vol_err"), f"{vol_err:.1e}", size="md"))
        i3, i4 = st.columns(2)
        i3.html(stat(t("val.iv.max_price_err"), f"{price_err:.1e}", size="md"))
        i4.html(stat(t("val.iv.bisection"), f"{n_bis}", size="md"))

st.html(f'<p class="opl-note" style="margin-top:1.6rem">{html.escape(tx("val.tests", n=count_tests()))}</p>')
