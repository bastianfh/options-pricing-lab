"""Design tokens and the shared Plotly chart theme.

Every chart in the app goes through :func:`style_figure`, so fonts, gridlines,
hover labels, margins and series colours are defined once here.

Colour roles
------------
* ``accent``     the single brand accent (petrol); used for the primary series
* ``series``     fixed categorical order for multi-series charts
                 (validated for colour-vision deficiency in both modes)
* ``gain/loss``  green/red reserved for profit and loss
* ``ramp``       single-hue ordinal ramp for multi-expiry lines
* ``surface_scale`` single-hue petrol scale for heatmaps and the vol surface

Light and dark values are separate selections, mirroring
``.streamlit/config.toml``. Background and font colours are left to
Streamlit's Plotly theme so charts follow the active theme client-side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import plotly.graph_objects as go
import streamlit as st

FONT_FAMILY = "Archivo, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


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
    rule: str
    series: tuple[str, ...]
    ramp: tuple[str, ...]
    surface_scale: tuple[str, ...]


LIGHT = Palette(
    accent="#0d5c61",
    accent_soft="rgba(13, 92, 97, 0.08)",
    ink="#16212a",
    muted="#5a6670",
    grid="rgba(22, 33, 42, 0.07)",
    axis="rgba(22, 33, 42, 0.24)",
    gain="#1f7a4d",
    loss="#b42318",
    gain_fill="rgba(31, 122, 77, 0.11)",
    loss_fill="rgba(180, 35, 24, 0.09)",
    reference="#16212a",
    card="#e9eeec",
    card_shadow="none",
    rule="rgba(22, 33, 42, 0.12)",
    # blue, orange, aqua, yellow: validated categorical order (adjacent CVD dE >= 9)
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100"),
    ramp=("#7dbab4", "#4c9e98", "#24827d", "#126866", "#08474a"),
    surface_scale=("#d9ecea", "#9fd0cb", "#4fa39d", "#16706f", "#0a3f42"),
)

DARK = Palette(
    accent="#5fb4ae",
    accent_soft="rgba(95, 180, 174, 0.12)",
    ink="#e1e7e5",
    muted="#95a3a8",
    grid="rgba(225, 231, 229, 0.07)",
    axis="rgba(225, 231, 229, 0.24)",
    gain="#45b880",
    loss="#ef7468",
    gain_fill="rgba(69, 184, 128, 0.13)",
    loss_fill="rgba(239, 116, 104, 0.12)",
    reference="#e1e7e5",
    card="#182225",
    card_shadow="none",
    rule="rgba(225, 231, 229, 0.12)",
    series=("#3987e5", "#d95926", "#199e70", "#c98500"),
    ramp=("#1e6b68", "#2f8a85", "#4fa8a2", "#7cc6c0", "#aee0db"),
    surface_scale=("#0a3f42", "#16706f", "#4fa39d", "#9fd0cb", "#d9ecea"),
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
            camera=dict(eye=dict(x=1.3, y=-1.45, z=0.5), center=dict(x=0, y=0, z=-0.15)),
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
