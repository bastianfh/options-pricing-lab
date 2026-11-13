"""Design tokens and the shared Plotly chart theme ("quant desk x industrial hardware").

Every chart in the app goes through :func:`style_figure` (or :func:`style_scene`
for 3D), so fonts, gridlines, hover readouts, margins and series colours are
defined once here. The app is locked to a single matte dark palette that
mirrors ``.streamlit/config.toml``.

Colour roles
------------
* ``accent``      signal orange: the active parameter / primary series
* ``positive``    emerald: calls, long, profit, in the money
* ``negative``    crimson: puts, short, loss, out of the money
* ``vol``         amber: volatility and secondary mathematical series
* ``series``      fixed categorical order for multi-series charts; every
                  series also gets its own dash and marker so colour is never
                  the only cue (emerald vs crimson is a red-green pair)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import plotly.graph_objects as go
import streamlit as st

MONO = "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace"
SANS = "Inter, -apple-system, 'Segoe UI', sans-serif"


@dataclass(frozen=True)
class Palette:
    """Colour tokens (single dark palette)."""

    canvas: str
    panel: str
    well: str
    rule: str
    grid: str
    ink: str
    label: str
    muted: str
    accent: str
    positive: str
    negative: str
    vol: str
    positive_fill: str
    negative_fill: str
    series: tuple[str, ...]
    ramp: tuple[str, ...]
    vol_ramp: tuple[str, ...]
    heat_scale: tuple[str, ...]
    vol_scale: tuple[str, ...]

    # Aliases used by older call sites.
    @property
    def muted_ink(self) -> str:
        return self.muted

    @property
    def axis(self) -> str:
        return self.muted

    @property
    def reference(self) -> str:
        return self.ink

    @property
    def gain(self) -> str:
        return self.positive

    @property
    def loss(self) -> str:
        return self.negative

    @property
    def gain_fill(self) -> str:
        return self.positive_fill

    @property
    def loss_fill(self) -> str:
        return self.negative_fill


PALETTE = Palette(
    canvas="#0A0A0B",
    panel="#111113",
    well="#161619",
    rule="#222226",
    grid="#1C1C20",
    ink="#F4F4F6",
    label="#8E8E93",
    muted="#48484D",
    accent="#FF5500",
    positive="#00E676",
    negative="#FF3B30",
    vol="#FFB800",
    positive_fill="rgba(0, 230, 118, 0.10)",
    negative_fill="rgba(255, 59, 48, 0.10)",
    # orange, amber, emerald, technical grey
    series=("#FF5500", "#FFB800", "#00E676", "#8E8E93"),
    # ordinal ramps: dim -> bright (brightest = most salient on the dark canvas)
    ramp=("#6B2A0A", "#A33A08", "#D94A04", "#FF5500", "#FF8F57"),
    vol_ramp=("#6B4D00", "#A37600", "#D99C00", "#FFB800", "#FFD25C"),
    heat_scale=("#161619", "#3D1A0B", "#8A330B", "#FF5500", "#FFB38A"),
    vol_scale=("#161619", "#3A2C08", "#8A6400", "#FFB800", "#FFE08A"),
)

DASHES = ("solid", "dash", "dot", "dashdot")
MARKERS = ("square", "diamond", "circle", "triangle-up")


def is_dark() -> bool:
    """The app is locked to dark mode."""
    return True


def palette() -> Palette:
    return PALETTE


def style_figure(
    fig: go.Figure,
    *,
    height: int = 360,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    legend: bool = True,
    hovermode: str = "x unified",
) -> go.Figure:
    """Apply the shared instrument chart theme in place and return the figure."""
    p = PALETTE
    axis = dict(
        showgrid=True,
        gridcolor=p.grid,
        gridwidth=1,
        zeroline=False,
        showline=True,
        linecolor=p.rule,
        linewidth=1,
        mirror=True,
        ticks="outside",
        tickcolor=p.rule,
        ticklen=3,
        tickfont=dict(family=MONO, size=10, color=p.label),
        title=dict(font=dict(family=MONO, size=10, color=p.label), standoff=8),
        showspikes=True,
        spikecolor=p.muted,
        spikethickness=1,
        spikedash="solid",
        spikemode="across",
        automargin=True,
    )
    fig.update_layout(
        height=height,
        font=dict(family=MONO, size=11, color=p.label),
        margin=dict(l=8, r=10, t=30 if legend else 10, b=8),
        colorway=list(p.series),
        hovermode=hovermode,
        hoverlabel=dict(bgcolor=p.canvas, bordercolor=p.rule, font=dict(family=MONO, size=11, color=p.ink)),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0.0,
            bgcolor="rgba(0,0,0,0)", font=dict(family=MONO, size=10, color=p.label), itemclick="toggleothers",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=p.panel,
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    if x_title is not None:
        fig.update_xaxes(title_text=x_title.upper())
    if y_title is not None:
        fig.update_yaxes(title_text=y_title.upper())
    return fig


def style_scene(fig: go.Figure, *, x_title: str, y_title: str, z_title: str, height: int = 520) -> go.Figure:
    """Shared styling for 3D surface charts."""
    p = PALETTE
    axis = dict(
        backgroundcolor=p.panel,
        gridcolor=p.rule,
        showbackground=True,
        zeroline=False,
        tickfont=dict(family=MONO, size=10, color=p.label),
        title=dict(font=dict(family=MONO, size=10, color=p.label)),
    )
    fig.update_layout(
        height=height,
        font=dict(family=MONO, size=10, color=p.label),
        margin=dict(l=0, r=0, t=6, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis=dict(axis, title_text=x_title.upper()),
            yaxis=dict(axis, title_text=y_title.upper()),
            zaxis=dict(axis, title_text=z_title.upper()),
            camera=dict(eye=dict(x=1.3, y=-1.45, z=0.5), center=dict(x=0, y=0, z=-0.15)),
            aspectmode="manual",
            aspectratio=dict(x=1.25, y=1.0, z=0.7),
        ),
        hoverlabel=dict(bgcolor=p.canvas, bordercolor=p.rule, font=dict(family=MONO, size=11, color=p.ink)),
    )
    return fig


def colorscale(kind: Literal["heat", "vol"] = "heat") -> list[list]:
    """Restrained single-hue colour scale: orange for sensitivities, amber for volatility."""
    steps = PALETTE.vol_scale if kind == "vol" else PALETTE.heat_scale
    return [[i / (len(steps) - 1), c] for i, c in enumerate(steps)]


def diverging_scale() -> list[list]:
    """Crimson (negative) -> well (zero) -> emerald (positive)."""
    return [[0.0, PALETTE.negative], [0.5, PALETTE.well], [1.0, PALETTE.positive]]


PLOTLY_CONFIG = {
    "displayModeBar": "hover",
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def show(fig: go.Figure, key: Optional[str] = None) -> None:
    """Render a styled figure. The theme is fully explicit, so Streamlit's own chart theme is disabled."""
    st.plotly_chart(fig, theme=None, config=PLOTLY_CONFIG, key=key)
