"""Downloadable reports: a self-contained HTML document a student can attach to a paper.

The report embeds plotly.js once (about 4.5 MB), so its charts work offline and keep working
years later, without depending on a CDN being reachable.

Pages create a :class:`Report` at the top, add parameters, results, charts and tables as
they draw them, and the "Generate report" button builds the HTML only when clicked. The
report is styled for print (white background, charts restyled light), so "Print -> Save
as PDF" in any browser gives a clean PDF.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go

from pricing import __version__

APP_URL = "https://options-pricing-lab-bastianfh.streamlit.app/"
REPO_URL = "https://github.com/bastianfh/options-pricing-lab"
_LIGHT = dict(ink="#16181d", muted="#5c6370", grid="#e6e8ec", rule="#c9ccd3")


@dataclass
class Report:
    """Content collected while a page renders."""

    title: str
    subtitle: str = ""
    items: list[tuple[str, Any]] = field(default_factory=list)
    share_link: Optional[str] = None
    data_source: Optional[str] = None

    def params(self, heading: str, values: dict[str, Any]) -> None:
        self.items.append(("params", (heading, dict(values))))

    def metrics(self, heading: str, values: list[tuple[str, str]]) -> None:
        self.items.append(("metrics", (heading, list(values))))

    def text(self, heading: str, body: str) -> None:
        self.items.append(("text", (heading, body)))

    def table(self, heading: str, frame: pd.DataFrame, max_rows: int = 500) -> None:
        self.items.append(("table", (heading, frame.head(max_rows).copy(), len(frame))))

    def figure(self, heading: str, fig: go.Figure) -> None:
        self.items.append(("figure", (heading, go.Figure(fig))))


def _light(fig: go.Figure) -> go.Figure:
    """Restyle an app chart for print: white background, dark text, light gridlines."""
    f = go.Figure(fig)
    axis = dict(gridcolor=_LIGHT["grid"], linecolor=_LIGHT["rule"], tickcolor=_LIGHT["rule"],
                tickfont=dict(color=_LIGHT["muted"]), title=dict(font=dict(color=_LIGHT["muted"])))
    f.update_layout(paper_bgcolor="white", plot_bgcolor="white", font=dict(color=_LIGHT["ink"]),
                    legend=dict(font=dict(color=_LIGHT["ink"])), height=360, hoverlabel=dict(bgcolor="white"))
    f.update_xaxes(**axis)
    f.update_yaxes(**axis)
    for trace in f.data:  # the app's off-white series would vanish on paper
        line = getattr(trace, "line", None)
        if line is not None and getattr(line, "color", None) in ("#F4F4F6", "#f4f4f6"):
            line.color = _LIGHT["ink"]
    return f


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.6g}"
    return str(value)


def build_html(report: Report) -> str:
    """Render ``report`` as a standalone HTML document (charts load plotly.js from its CDN)."""
    now = datetime.now(timezone.utc)
    parts: list[str] = []
    first_figure = True
    for kind, payload in report.items:
        if kind == "params":
            heading, values = payload
            rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(_fmt(v))}</td></tr>"
                           for k, v in values.items())
            parts.append(f"<section><h2>{html.escape(heading)}</h2><table class='kv'>{rows}</table></section>")
        elif kind == "metrics":
            heading, values = payload
            def tone(v: str) -> str:  # gains green, losses red, as in the app
                return " class='pos'" if v.startswith("+") else (" class='neg'" if v.startswith(("−", "-")) else "")

            cells = "".join(f"<div><span>{html.escape(k)}</span><b{tone(v)}>{html.escape(v)}</b></div>" for k, v in values)
            parts.append(f"<section><h2>{html.escape(heading)}</h2><div class='metrics'>{cells}</div></section>")
        elif kind == "text":
            heading, body = payload
            paras = "".join(f"<p>{html.escape(p)}</p>" for p in body.split("\n") if p.strip())
            parts.append(f"<section><h2>{html.escape(heading)}</h2>{paras}</section>")
        elif kind == "table":
            heading, frame, total = payload
            note = f"<p class='note'>First {len(frame)} of {total} rows.</p>" if total > len(frame) else ""
            table = frame.to_html(index=False, border=0, classes="data", float_format=lambda x: f"{x:,.4f}")
            parts.append(f"<section><h2>{html.escape(heading)}</h2>{table}{note}</section>")
        elif kind == "figure":
            heading, fig = payload
            div = _light(fig).to_html(full_html=False, include_plotlyjs=first_figure, config={"displaylogo": False})
            first_figure = False
            parts.append(f"<section class='fig'><h2>{html.escape(heading)}</h2>{div}</section>")

    share = (f"<p>Reproduce these results: <a href='{html.escape(report.share_link)}'>{html.escape(report.share_link)}</a></p>"
             if report.share_link else "")
    source = f"<p>Data: {html.escape(report.data_source)}</p>" if report.data_source else ""
    citation = (f"Options Pricing Lab (v{__version__}). {APP_URL} (source code: {REPO_URL}). "
                f"Accessed {now:%d %B %Y}.")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(report.title)} | Options Pricing Lab</title>
<style>
  :root {{ --ink:{_LIGHT['ink']}; --muted:{_LIGHT['muted']}; --rule:{_LIGHT['rule']}; --accent:#d94800; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', Inter, Helvetica, Arial, sans-serif; color: var(--ink);
         max-width: 980px; margin: 2.5rem auto; padding: 0 1.25rem; line-height: 1.5; font-size: 14px; }}
  header {{ border-bottom: 2px solid var(--ink); padding-bottom: .8rem; margin-bottom: 1.4rem; }}
  header .k {{ font: 600 11px ui-monospace, Menlo, monospace; letter-spacing: .08em; color: var(--accent); }}
  h1 {{ font-size: 1.6rem; margin: .25rem 0; }}
  h2 {{ font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
        border-top: 1px solid var(--rule); padding-top: .7rem; margin: 1.6rem 0 .6rem; }}
  .meta {{ color: var(--muted); font-size: 12.5px; }}
  table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
  table.kv th {{ text-align: left; font-weight: 500; color: var(--muted); width: 40%; }}
  th, td {{ padding: .3rem .5rem; border-bottom: 1px solid #eceef1; text-align: left; font-size: 12.5px; }}
  table.data td {{ text-align: right; font-family: ui-monospace, Menlo, monospace; font-size: 11.5px; }}
  table.data th {{ text-align: right; font-size: 11px; color: var(--muted); }}
  .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--rule); border: 1px solid var(--rule); }}
  .metrics div {{ background: white; padding: .55rem .65rem; }}
  .metrics span {{ display: block; font-size: 10.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
  .metrics b {{ font: 600 15px ui-monospace, Menlo, monospace; }}
  .metrics b.pos {{ color: #0a7f3f; }}
  .metrics b.neg {{ color: #c62828; }}
  .note {{ color: var(--muted); font-size: 12px; }}
  footer {{ margin-top: 2.2rem; border-top: 2px solid var(--ink); padding-top: .8rem; font-size: 12.5px; }}
  footer .cite {{ font-family: ui-monospace, Menlo, monospace; font-size: 12px; background: #f5f6f8; padding: .6rem; }}
  a {{ color: var(--accent); word-break: break-all; }}
  @page {{ margin: 16mm; }}
  @media print {{ body {{ margin: 0; max-width: none; }} section {{ break-inside: avoid; }} a {{ color: var(--ink); }} }}
</style></head>
<body>
<header>
  <div class="k">OPTIONS PRICING LAB // REPORT</div>
  <h1>{html.escape(report.title)}</h1>
  <div class="meta">{html.escape(report.subtitle)}{', ' if report.subtitle else ''}generated {now:%d %b %Y %H:%M} UTC, v{__version__}</div>
</header>
{''.join(parts)}
<footer>
  {source}{share}
  <p>How to cite:</p>
  <div class="cite">{html.escape(citation)}</div>
  <p class="note">Model outputs for education and research, not investment advice. To save as PDF, use your browser's Print command.</p>
</footer>
</body></html>"""
