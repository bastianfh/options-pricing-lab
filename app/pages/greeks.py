"""Greeks explorer: how each Greek varies with spot and with time to expiry."""

from __future__ import annotations

import html

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app.content import t
from app.theme import DASHES, colorscale, palette, show, style_figure
from app.ui import explain, input_panel, is_pro, page_header, panel, panel_title, section, tx
from pricing.greeks import GREEK_NAMES, black_scholes_greeks

page_header("gx.title", "gx.lede")

left, right = st.columns([1, 2.3], gap="large")
with left, panel("gx_inputs"):
    panel_title(tx("inputs.contract"))
    spec, _, ctx = input_panel(exercise=False, numerics=False)

SCALE = {"vega": 0.01, "theta": 1 / 365, "rho": 0.01}  # market units: per vol pt, per day, per 1%


def greek_grid(name: str, S: np.ndarray, T: np.ndarray) -> np.ndarray:
    """Greek ``name`` on the outer product of spots ``S`` and expiries ``T`` -> shape (len(T), len(S))."""
    g = black_scholes_greeks(S[None, :], spec.K, T[:, None], spec.r, spec.sigma, spec.q, spec.option_type)
    return np.asarray(getattr(g, name)) * SCALE.get(name, 1.0)


with right:
    choice = st.segmented_control(
        tx("gx.select"),
        options=list(GREEK_NAMES),
        format_func=lambda n: t(f"greek.{n}.short") if is_pro() else tx(f"greek.{n}.name"),
        key="gx_greek",
        default="delta",
        required=True,
        persist_state="session",
        width="stretch",
    )
    name = choice or "delta"
    label = t(f"greek.{name}.name", "Pro")
    unit = t(f"greek.{name}.unit")
    p = palette()
    if is_pro():
        st.caption(f"{label}, {unit}")
    insight = tx(f"gx.insight.{name}")
    if is_pro():
        st.html(f'<p class="opl-note">{html.escape(insight)}</p>')
    else:
        explain(insight)

    days_now = int(st.session_state["in_days"])
    sd = spec.sigma * np.sqrt(max(spec.T, 30 / 365))
    spots = np.linspace(spec.K * np.exp(-3 * sd), spec.K * np.exp(3 * sd), 301)

    # ---------------------------------------------------------- vs spot
    section(tx("gx.vs_spot.title", greek=label))
    day_list = sorted({max(int(round(days_now * f)), 2) for f in (1.0, 0.5, 0.25)} | {7}, reverse=True)
    ramp = p.ramp[-len(day_list):] if len(day_list) <= len(p.ramp) else p.ramp
    fig = go.Figure()
    for i, d in enumerate(day_list):
        y = greek_grid(name, spots, np.array([d / 365]))[0]
        fig.add_trace(go.Scatter(
            x=spots, y=y, name=tx("gx.days_left", d=d),
            line=dict(color=ramp[min(i, len(ramp) - 1)], width=2.2),
            hovertemplate="%{y:.4f}",
        ))
    fig.add_vline(x=spec.K, line=dict(color=p.axis, width=1, dash="dot"),
                  annotation_text="K" if is_pro() else t("in.K.label", "Plain English"),
                  annotation_position="top left", annotation_font_size=11)
    fig.add_vline(x=spec.S, line=dict(color=p.accent, width=1, dash="dash"))
    style_figure(fig, height=340, x_title=tx("gx.x_spot"), y_title=f"{label} ({unit})" if is_pro() else tx(f"greek.{name}.name"))
    show(fig, key="gx_spot")

    # ---------------------------------------------------------- vs time
    section(tx("gx.vs_time.title", greek=label))
    horizon = max(days_now, 30)
    days_axis = np.linspace(horizon, 1, 240)
    fig = go.Figure()
    for i, (m_key, factor) in enumerate([("itm", 0.9), ("atm", 1.0), ("otm", 1.1)]):
        # Moneyness by strike relative to spot; for puts, ITM means K above S.
        k_over_s = factor if spec.option_type.value == "call" else 2 - factor
        s_val = spec.K / k_over_s
        y = greek_grid(name, np.array([s_val]), days_axis / 365)[:, 0]
        fig.add_trace(go.Scatter(
            x=days_axis, y=y, name=tx(f"gx.{m_key}", m=k_over_s),
            line=dict(color=p.series[i], width=2.2, dash=DASHES[i]),
            hovertemplate="%{y:.4f}",
        ))
    fig.update_xaxes(autorange="reversed")
    style_figure(fig, height=340, x_title=tx("gx.x_time"), y_title=f"{label} ({unit})" if is_pro() else tx(f"greek.{name}.name"))
    show(fig, key="gx_time")

    # ---------------------------------------------------------- heatmap
    section(tx("gx.heatmap.title", greek=label))
    days_hm = np.linspace(1, horizon, 120)
    z = greek_grid(name, spots, days_hm / 365)
    lo, hi = float(np.nanmin(z)), float(np.nanmax(z))
    if lo < 0 < hi:  # diverging: two hues around a neutral midpoint at zero
        bound = max(abs(lo), abs(hi))
        scale = [[0, p.loss], [0.5, "rgba(128,128,128,0.15)"], [1, p.series[0]]]
        zmin, zmax = -bound, bound
    else:  # one sign: single-hue ramp, darkest at the largest magnitude
        scale = colorscale()
        if hi <= 0:
            scale = [[1 - pos, c] for pos, c in reversed(scale)]
        zmin, zmax = lo, hi
    fig = go.Figure(go.Heatmap(
        x=spots, y=days_hm, z=z, colorscale=scale, zmin=zmin, zmax=zmax,
        colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(size=11)),
        hovertemplate=f"{tx('gx.x_spot')}: %{{x:.4f}}<br>{tx('gx.x_time')}: %{{y:.0f}}<br>{label}: %{{z:.4f}}<extra></extra>",
    ))
    fig.add_vline(x=spec.K, line=dict(color=p.ink, width=1, dash="dot"))
    style_figure(fig, height=360, x_title=tx("gx.x_spot"), y_title=tx("gx.x_time"), legend=False, hovermode="closest")
    show(fig, key="gx_heat")
