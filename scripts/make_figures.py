"""Build the README headline figure: convergence of each numerical method to Black-Scholes.

Writes a standalone Plotly HTML file; ``scripts/html_to_png.cjs`` turns it into
``docs/images/convergence.png``.

    python scripts/make_figures.py /tmp/convergence.html
    node scripts/html_to_png.cjs /tmp/convergence.html docs/images/convergence.png 1500 520
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricing.convergence import binomial_study, monte_carlo_study, pde_study, standard_error_order  # noqa: E402
from pricing.engine import OptionSpec  # noqa: E402

FONT = "'JetBrains Mono', ui-monospace, monospace"
INK, MUTED, GRID, RULE = "#F4F4F6", "#8E8E93", "#1C1C20", "#222226"
BLUE, ORANGE, AQUA, YELLOW = "#FF5500", "#8E8E93", "#00E676", "#FFB800"


def main(out: str) -> None:
    spec = OptionSpec(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20, q=0.02, option_type="call")
    steps = np.unique(np.geomspace(10, 2000, 30).astype(int))
    grids = np.array([25, 50, 100, 200, 400, 800])
    paths = np.array([1_000, 3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000])
    tree, pde, mc = binomial_study(spec, steps), pde_study(spec, grids), monte_carlo_study(spec, paths)
    plain, best = mc.studies["plain"], mc.studies["antithetic_control_variate"]

    fig = make_subplots(
        rows=1, cols=3, horizontal_spacing=0.07,
        subplot_titles=(
            f"Binomial tree: order {tree.order:.2f} (theory 1)",
            f"Monte Carlo std. error: order {standard_error_order(best):.2f} (theory ½)",
            f"Crank-Nicolson: order {pde.order:.2f} (theory 2)",
        ),
    )

    def ref(n: np.ndarray, start: float, p: float) -> np.ndarray:
        return start * (n / n[0]) ** (-p)

    err = np.abs(tree.errors)
    fig.add_trace(go.Scatter(x=steps, y=err, mode="lines+markers", name="|binomial − BS|",
                             line=dict(color=BLUE, width=2), marker=dict(size=5)), 1, 1)
    fig.add_trace(go.Scatter(x=steps, y=ref(steps, err[0] * 1.3, 1), name="O(1/N)", mode="lines",
                             line=dict(color=MUTED, dash="dot", width=1.5)), 1, 1)

    fig.add_trace(go.Scatter(x=paths, y=plain.std_errors, mode="lines+markers", name="MC plain",
                             line=dict(color=ORANGE, width=2), marker=dict(size=6, symbol="square")), 1, 2)
    fig.add_trace(go.Scatter(x=paths, y=best.std_errors, mode="lines+markers", name="MC antithetic + control variate",
                             line=dict(color=YELLOW, width=2, dash="dash"), marker=dict(size=6, symbol="triangle-up")),
                  1, 2)
    fig.add_trace(go.Scatter(x=paths, y=ref(paths, plain.std_errors[0] * 1.3, 0.5), name="O(1/√n)", mode="lines",
                             line=dict(color=MUTED, dash="dash", width=1.5)), 1, 2)

    pe = np.abs(pde.errors)
    fig.add_trace(go.Scatter(x=grids, y=pe, mode="lines+markers", name="|PDE − BS|",
                             line=dict(color=AQUA, width=2), marker=dict(size=7, symbol="diamond")), 1, 3)
    fig.add_trace(go.Scatter(x=grids, y=ref(grids, pe[0] * 1.3, 2), name="O(1/M²)", mode="lines",
                             line=dict(color=MUTED, dash="dashdot", width=1.5)), 1, 3)

    axis = dict(type="log", gridcolor=GRID, linecolor=RULE, mirror=True, showline=True, ticks="outside",
                tickcolor=RULE, zeroline=False, exponentformat="power", dtick=1, tickfont=dict(size=11, color=MUTED))
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    fig.update_xaxes(title_text="time steps N", row=1, col=1)
    fig.update_xaxes(title_text="paths n", row=1, col=2)
    fig.update_xaxes(title_text="grid size M = N", row=1, col=3)
    fig.update_yaxes(title_text="absolute error vs Black-Scholes", row=1, col=1)
    fig.update_annotations(font=dict(size=12, family=FONT, color=INK))
    fig.update_layout(
        width=1500, height=520, font=dict(family=FONT, size=11, color=MUTED),
        paper_bgcolor="#0A0A0B", plot_bgcolor="#111113", margin=dict(l=70, r=30, t=50, b=90),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", font=dict(size=12)),
    )
    fig.write_html(out, include_plotlyjs="inline", full_html=True, config={"displayModeBar": False})
    # Load the same monospace face the app uses, on the same carbon canvas.
    page = Path(out).read_text()
    head = ('<head><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500'
            '&display=swap"><style>body{margin:0;background:#0A0A0B}</style>')
    Path(out).write_text(page.replace("<head>", head, 1))
    print(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "convergence.html")
