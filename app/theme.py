"""Design tokens and the shared Plotly chart theme.

Every chart in the app goes through :func:`style_figure`, so fonts, gridlines,
hover labels, margins and series colours are defined once here.

Colour roles
------------
* ``accent``     the single brand accent (indigo); used for the primary series
* ``series``     fixed categorical order for multi-series charts
                 (validated for colour-vision deficiency in both modes)
* ``gain/loss``  green/red reserved for profit and loss
* ``ramp``       single-hue sequential/ordinal ramp (light -> dark)

Light and dark values are separate selections, mirroring
``.streamlit/config.toml``. Background and font colours are left to
Streamlit's Plotly theme so charts follow the active theme client-side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import plotly.graph_objects as go
import streamlit as st

FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


@dataclass(frozen=True)
class Palette:
    """Colour tokens for one theme mode."""

    accent: str
    accent_soft: str
    ink: str
    muted: str
    grid: str
    axis: str
    gain: str
    loss: str
    gain_fill: str
    loss_fill: str
    reference: str
    card: str
    card_shadow: str
    series: tuple[str, ...]
    ramp: tuple[str, ...]
    surface_scale: tuple[str, ...]


LIGHT = Palette(
    accent="#4f46e5",
    accent_soft="rgba(79, 70, 229, 0.10)",
    ink="#111827",
    muted="#6b7280",
    grid="rgba(17, 24, 39, 0.07)",
    axis="rgba(17, 24, 39, 0.22)",
    gain="#15803d",
    loss="#dc2626",
    gain_fill="rgba(21, 128, 61, 0.12)",
    loss_fill="rgba(220, 38, 38, 0.10)",
    reference="#111827",
    card="#ffffff",
    card_shadow="0 1px 2px rgba(17, 24, 39, 0.04), 0 4px 16px rgba(17, 24, 39, 0.04)",
    # blue, orange, aqua, yellow: validated categorical order (adjacent CVD dE >= 9)
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100"),
    ramp=("#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"),
    surface_scale=("#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"),
)

DARK = Palette(
    accent="#8b8cf8",
    accent_soft="rgba(139, 140, 248, 0.14)",
    ink="#e6e8ee",
    muted="#9aa1ad",
    grid="rgba(230, 232, 238, 0.07)",
    axis="rgba(230, 232, 238, 0.22)",
    gain="#34c46b",
    loss="#f06565",
    gain_fill="rgba(52, 196, 107, 0.14)",
    loss_fill="rgba(240, 101, 101, 0.13)",
    reference="#e6e8ee",
    card="#12151c",
    card_shadow="0 1px 2px rgba(0, 0, 0, 0.3)",
    series=("#3987e5", "#d95926", "#199e70", "#c98500"),
    ramp=("#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"),
    surface_scale=("#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#cde2fb"),
)

# Line dashes and markers give every series a second, non-colour encoding.
DASHES = ("solid", "dash", "dot", "dashdot")
MARKERS = ("circle", "square", "diamond", "triangle-up")


def is_dark() -> bool:
    """Whether the active Streamlit theme is dark (defaults to light if unknown)."""
    try:
        return st.context.theme.type == "dark"
    except Exception:  # pragma: no cover - outside a Streamlit runtime
        return False


def palette() -> Palette:
    """Palette for the active theme."""
    return DARK if is_dark() else LIGHT


def style_figure(
    fig: go.Figure,
    *,
    height: int = 380,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    legend: bool = True,
    hovermode: str = "x unified",
) -> go.Figure:
    """Apply the shared chart theme in place and return the figure."""
    p = palette()
    axis = dict(
        showgrid=True,
        gridcolor=p.grid,
        gridwidth=1,
        zeroline=False,
        showline=True,
        linecolor=p.axis,
        linewidth=1,
        ticks="outside",
        tickcolor=p.axis,
        ticklen=4,
        tickfont=dict(size=12),
        title=dict(font=dict(size=12.5), standoff=10),
        automargin=True,
    )
    fig.update_layout(
        height=height,
        font=dict(family=FONT_FAMILY, size=13),
        margin=dict(l=8, r=12, t=28 if legend else 12, b=8),
        colorway=list(p.series),
        hovermode=hovermode,
        hoverlabel=dict(font=dict(family=FONT_FAMILY, size=12.5), bordercolor=p.axis),
        showlegend=legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.0,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12.5),
            itemclick="toggleothers",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    if x_title is not None:
        fig.update_xaxes(title_text=x_title)
    if y_title is not None:
        fig.update_yaxes(title_text=y_title)
    return fig


def style_scene(fig: go.Figure, *, x_title: str, y_title: str, z_title: str, height: int = 560) -> go.Figure:
    """Shared styling for 3D surface charts."""
    p = palette()
    axis = dict(
        backgroundcolor="rgba(0,0,0,0)",
        gridcolor=p.axis,
        showbackground=False,
        zeroline=False,
        tickfont=dict(size=11),
        title=dict(font=dict(size=12)),
    )
    fig.update_layout(
        height=height,
        font=dict(family=FONT_FAMILY, size=12),
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis=dict(axis, title_text=x_title),
            yaxis=dict(axis, title_text=y_title),
            zaxis=dict(axis, title_text=z_title),
            camera=dict(eye=dict(x=1.55, y=-1.55, z=0.85)),
            aspectmode="manual",
            aspectratio=dict(x=1.25, y=1.0, z=0.7),
        ),
        hoverlabel=dict(font=dict(family=FONT_FAMILY, size=12.5)),
    )
    return fig


def colorscale() -> list[list]:
    """Single-hue sequential colour scale for heatmaps and surfaces."""
    steps = palette().surface_scale
    return [[i / (len(steps) - 1), c] for i, c in enumerate(steps)]


PLOTLY_CONFIG = {
    "displayModeBar": "hover",
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def show(fig: go.Figure, key: Optional[str] = None) -> None:
    """Render a styled figure with the shared config (Streamlit supplies theme-aware font/background)."""
    st.plotly_chart(fig, theme="streamlit", config=PLOTLY_CONFIG, key=key)
