"""Volatility surface: invert a grid of option prices into implied vols; 3D surface, smiles, term structure."""

from __future__ import annotations

import html
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.content import FX_PAIRS, t
from app.theme import colorscale, palette, show, style_figure, style_scene
from app.ui import (
    _on_asset_change,
    _on_pair_change,
    cached,
    cells,
    context,
    explain,
    init_state,
    is_pro,
    lbl,
    page_header,
    panel,
    panel_title,
    section,
    tx,
    upper,
)
from pricing.implied_vol import (
    SmileParameters,
    VolSurface,
    implied_vol_surface,
    implied_volatility_solve,
    synthetic_surface,
    synthetic_vol,
)

page_header("vs.title", "vs.lede")
init_state()

left, right = st.columns([1, 2.3], gap="large")
with left, panel("vs_inputs"):
    panel_title(tx("vs.source"))
    source = "synthetic"
    if is_pro():
        source = st.segmented_control(
            lbl("vs.source"), ["synthetic", "upload"], format_func=lambda v: upper(tx(f"vs.source.{v}")),
            key="vs_source", default="synthetic", required=True, label_visibility="collapsed",
            persist_state="session", width="stretch",
        )
    uploaded = None
    if source == "upload":
        uploaded = st.file_uploader(upper(t("vs.upload.help")), type=["csv"], key="vs_upload")
    else:
        st.slider(lbl("vs.atm"), 3.0, 80.0, 20.0, 0.5, key="vs_atm", help=tx("vs.atm.help"), persist_state="session")
        st.slider(lbl("vs.skew"), -0.30, 0.30, -0.10, 0.01, key="vs_skew", help=tx("vs.skew.help"), persist_state="session")
        st.slider(lbl("vs.curv"), 0.0, 0.30, 0.06, 0.01, key="vs_curv", help=tx("vs.curv.help"), persist_state="session")
        st.slider(lbl("vs.term"), -0.15, 0.15, 0.03, 0.01, key="vs_term", help=tx("vs.term.help"), persist_state="session")

    st.html('<div style="height:0.8rem"></div>')
    panel_title(tx("inputs.market"))
    st.segmented_control(
        lbl("in.asset.label"), ["stock", "fx"], format_func=lambda v: upper(tx(f"in.asset.{v}")), key="in_asset",
        required=True, on_change=_on_asset_change, persist_state="session", width="stretch",
    )
    ctx = context()
    if ctx.is_fx:
        st.selectbox(lbl("in.pair.label"), list(FX_PAIRS), key="in_pair", on_change=_on_pair_change,
                     persist_state="session")
        ctx = context()
    fmt = "%.4f" if ctx.is_fx else "%.2f"
    st.number_input(lbl("in.S.label"), min_value=1e-4, step=ctx.spot_step, format=fmt, key="in_S",
                    help=tx("in.S.help"), persist_state="session")
    rate_key, carry_key = ("in.r_fx", "in.q_fx") if ctx.is_fx else ("in.r", "in.q")
    names = dict(base=ctx.base, quote=ctx.quote)
    st.number_input(lbl(f"{rate_key}.label", **names), -5.0, 50.0, step=0.25, format="%.2f", key="in_r",
                    help=tx(f"{rate_key}.help"), persist_state="session")
    st.number_input(lbl(f"{carry_key}.label", **names), -5.0, 50.0, step=0.25, format="%.2f", key="in_q",
                    help=tx(f"{carry_key}.help"), persist_state="session")

s = st.session_state
S, r, q = float(s["in_S"]), float(s["in_r"]) / 100, float(s["in_q"]) / 100


@cached
def build_synthetic(S: float, r: float, q: float, params: SmileParameters) -> tuple[VolSurface, dict]:
    strikes = S * np.linspace(0.7, 1.3, 31)
    expiries = np.array([1 / 12, 2 / 12, 3 / 12, 6 / 12, 9 / 12, 1.0, 1.5, 2.0])
    surface = synthetic_surface(S, r, q, params, strikes, expiries)
    truth = synthetic_vol(strikes, expiries, S, r, q, params)
    iters, newton, total_steps = [], 0, 0
    for i, T in enumerate(expiries):
        for j, K in enumerate(strikes):
            res = implied_volatility_solve(surface.prices[i, j], S, K, T, r, q, surface.option_types[i, j])
            iters.append(res.iterations)
            newton += res.newton_steps
            total_steps += res.newton_steps + res.bisection_steps
    solved = np.isfinite(surface.vols)
    diag = dict(
        points=surface.vols.size,
        solved=int(solved.sum()),
        max_err=float(np.nanmax(np.abs(surface.vols - truth))),
        newton_share=newton / max(total_steps, 1),
        mean_iters=float(np.mean(iters)),
    )
    return surface, diag


def build_uploaded(data: bytes, S: float, r: float, q: float) -> VolSurface:
    df = pd.read_csv(io.BytesIO(data))
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"strike", "expiry", "price", "type"}
    if not required <= set(df.columns):
        raise ValueError("missing columns")
    strikes = np.sort(df["strike"].unique())
    expiries = np.sort(df["expiry"].unique())
    prices = np.full((len(expiries), len(strikes)), np.nan)
    types = np.full(prices.shape, "call", dtype=object)
    for row in df.itertuples():
        i, j = np.searchsorted(expiries, row.expiry), np.searchsorted(strikes, row.strike)
        prices[i, j], types[i, j] = row.price, str(row.type).strip().lower()
    return implied_vol_surface(prices, strikes, expiries, S, r, q, types)


diag = None
if source == "upload":
    if uploaded is None:
        params = SmileParameters()
        surface, _ = build_synthetic(S, r, q, params)
        sample = pd.DataFrame(
            [(K, T, surface.prices[i, j], surface.option_types[i, j])
             for i, T in enumerate(surface.expiries) for j, K in enumerate(surface.strikes)],
            columns=["strike", "expiry", "price", "type"],
        )
        with right:
            st.info(t("vs.upload.help"))
            st.download_button("Download a sample CSV", sample.to_csv(index=False), "sample_quotes.csv", "text/csv")
        st.stop()
    try:
        surface = build_uploaded(uploaded.getvalue(), S, r, q)
    except Exception:
        with right:
            st.error(t("vs.upload.error"))
        st.stop()
else:
    params = SmileParameters(
        atm_vol=s["vs_atm"] / 100, skew=s["vs_skew"], curvature=s["vs_curv"], term_slope=s["vs_term"]
    )
    surface, diag = build_synthetic(S, r, q, params)

p = palette()
moneyness = surface.strikes / S
vols_pct = surface.vols * 100

with right:
    if not is_pro():
        explain(tx("vs.insight"))
    # ----------------------------------------------------------- 3D surface
    section(tx("vs.surface.title"))
    fig = go.Figure(go.Surface(
        x=moneyness, y=surface.expiries, z=vols_pct, colorscale=colorscale("vol"),
        colorbar=dict(thickness=8, len=0.6, x=0.94, outlinewidth=0, title=dict(text="%", side="top"),
                      tickfont=dict(family="JetBrains Mono, monospace", size=10)),
        contours=dict(z=dict(show=True, usecolormap=True, project=dict(z=False), width=1)),
        hovertemplate=(f"{tx('vs.x_moneyness')}: %{{x:.3f}}<br>{tx('vs.y_expiry')}: %{{y:.2f}}"
                       f"<br>{tx('vs.z_vol')}: %{{z:.2f}}<extra></extra>"),
        lighting=dict(ambient=0.75, diffuse=0.5, specular=0.08, roughness=0.9),
    ))
    style_scene(fig, x_title=tx("vs.x_moneyness"), y_title=tx("vs.y_expiry"), z_title=tx("vs.z_vol"), height=480)
    show(fig, key="vs_chart_surface")

    # -------------------------------------------------------------- smiles
    c1, c2 = st.columns([1.4, 1], gap="medium")
    with c1:
        section(tx("vs.smile.title"))
        picks = [i for i, T in enumerate(surface.expiries) if np.isclose(T, [1 / 12, 3 / 12, 6 / 12, 1.0, 2.0]).any()]
        if len(picks) < 2:
            picks = list(range(min(5, len(surface.expiries))))
        ramp = p.vol_ramp[::-1][: len(picks)] if len(picks) <= len(p.vol_ramp) else p.vol_ramp
        fig = go.Figure()
        for n, i in enumerate(picks):
            T = surface.expiries[i]
            label = f"{T * 12:.0f}M" if T < 1 else f"{T:g}Y"
            fig.add_trace(go.Scatter(x=moneyness, y=vols_pct[i], name=label, mode="lines",
                                     line=dict(color=ramp[min(n, len(ramp) - 1)], width=2.2),
                                     hovertemplate="%{y:.2f}%"))
        fig.add_vline(x=1.0, line=dict(color=p.muted, width=1, dash="dash"))
        style_figure(fig, height=340, x_title=tx("vs.x_moneyness"), y_title=tx("vs.z_vol"))
        show(fig, key="vs_chart_smiles")
    with c2:
        section(tx("vs.term_structure.title"))
        forwards = S * np.exp((r - q) * surface.expiries)
        atm = []
        for i, F in enumerate(forwards):
            row = surface.vols[i]
            ok = np.isfinite(row)
            atm.append(np.interp(np.log(F), np.log(surface.strikes[ok]), row[ok]) * 100 if ok.sum() > 1 else np.nan)
        fig = go.Figure(go.Scatter(x=surface.expiries, y=atm, mode="lines+markers", name="ATM",
                                   line=dict(color=p.vol, width=2), marker=dict(size=7, symbol="square"),
                                   hovertemplate="%{y:.2f}%"))
        style_figure(fig, height=340, x_title=tx("vs.y_expiry"), y_title=tx("vs.z_vol"), legend=False)
        show(fig, key="vs_chart_term")

    # ---------------------------------------------------------- diagnostics
    if is_pro() and diag is not None:
        section(t("vs.diag.title"))
        with st.container(key="vs_diag"):
            st.html(cells([
                (t("vs.diag.solved"), f"{diag['solved']}/{diag['points']}", "", "pos"),
                (t("vs.diag.max_err"), f"{diag['max_err']:.1e}", "", ""),
                (t("vs.diag.newton"), f"{100 * diag['newton_share']:.0f}%", "", ""),
                (t("vs.diag.iters"), f"{diag['mean_iters']:.1f}", "", ""),
            ]))
        st.html(f'<p class="opl-note">{html.escape(tx("vs.insight"))}</p>')
