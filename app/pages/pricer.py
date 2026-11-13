"""Pricer: inputs on the left; price, all four methods side by side, and Greeks on the right."""

from __future__ import annotations

import html
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.content import t
from app.theme import palette, show, style_figure
from app.ui import (
    Context,
    agreement_html,
    cached,
    explain,
    input_panel,
    is_pro,
    page_header,
    panel,
    panel_title,
    preset_pills,
    section,
    signed,
    tx,
    upper,
)
from pricing.engine import Method, NumericalSettings, OptionSpec, greeks, price_all
from pricing.greeks import GREEK_NAMES
from pricing.models.black_scholes import black_scholes_price, d1_d2
from pricing.utils import ExerciseStyle, OptionType

page_header("pricer.title", "pricer.lede")

if not is_pro():
    preset_pills()

left, right = st.columns([1, 3.1], gap="small")
with left, panel("pricer_inputs"):
    panel_title(tx("inputs.contract"))
    spec, settings, ctx = input_panel()


@cached
def compute(spec: OptionSpec, settings: NumericalSettings):
    results = price_all(spec, settings)
    gks = {m: greeks(spec, m, settings) for m in Method}
    return results, gks


results, gks = compute(spec, settings)
american = spec.exercise is ExerciseStyle.AMERICAN
model_key = "method.black_scholes_fx" if ctx.is_fx else "method.black_scholes"


def method_label(m: Method) -> str:
    return tx(model_key) if m is Method.BLACK_SCHOLES else tx(f"method.{m.value}")


def greek_display(name: str, value: float) -> float:
    """Convert raw Greeks to market units: vega per vol pt, theta per day, rho per 1%."""
    if value is None or not math.isfinite(value):
        return float("nan")
    return {"vega": value / 100, "theta": value / 365, "rho": value / 100}.get(name, value)


def moneyness_text(spec: OptionSpec, ctx: Context) -> str:
    phi = 1 if spec.option_type is OptionType.CALL else -1
    intrinsic = max(phi * (spec.S - spec.K), 0.0)
    if abs(spec.K / spec.S - 1) < 0.005:
        return t("moneyness.atm")
    if intrinsic > 0:
        return t("moneyness.itm", intrinsic=ctx.money(intrinsic))
    return t("moneyness.otm")


with right:
    # ---------------------------------------------------------------- hero
    bs = results[Method.BLACK_SCHOLES]
    headline = results[Method.BINOMIAL].price if american and not bs.available else bs.price
    if american and bs.available:
        headline = results[Method.BINOMIAL].price  # American call, no dividends: same as European
    pct = 100 * headline / spec.S

    section(tx("pricer.readout.title"))
    if american:
        label = tx("pricer.hero.label_american")
    else:
        label = tx("pricer.hero.label", model=t(model_key, "Pro"))
    phi = 1 if spec.option_type is OptionType.CALL else -1
    intrinsic = max(phi * (spec.S - spec.K), 0.0)
    fwd = spec.S * math.exp((spec.r - spec.q) * spec.T)
    is_call = spec.option_type is OptionType.CALL
    badge = (f'<span class="opl-badge {"pos" if is_call else "neg"}">{"CALL" if is_call else "PUT"}</span>'
             f'<span class="opl-badge acc">{"AMERICAN" if american else "EUROPEAN"}</span>')
    side_cells = [
        (tx("pricer.facts.intrinsic"), ctx.money(intrinsic)),
        (tx("pricer.facts.time_value"), ctx.money(headline - intrinsic)),
        (tx("pricer.facts.forward"), f"{fwd:,.{5 if ctx.is_fx else 2}f}"),
        (tx("pricer.facts.expires"), f"{st.session_state['in_days']} D"),
    ]
    st.html(
        '<div class="opl-grid" style="grid-template-columns:2.2fr repeat(4, minmax(0, 1fr))">'
        f'<div class="opl-cell opl-readout"><div class="k">{html.escape(upper(label))}{badge}</div>'
        f'<div class="v">{html.escape(ctx.money(headline, ctx.price_decimals + (2 if is_pro() else 0)))}</div>'
        f'<div class="s">{pct:.2f}% OF SPOT</div></div>'
        + "".join(f'<div class="opl-cell"><div class="k">{html.escape(upper(k))}</div>'
                  f'<div class="v">{html.escape(v)}</div></div>' for k, v in side_cells)
        + "</div>"
    )

    euro = float(black_scholes_price(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type))
    if american:
        text = tx("pricer.hero.explain_american", price=ctx.money(headline),
                  premium=ctx.money(headline - euro), pde=ctx.money(results[Method.FINITE_DIFFERENCE].price))
    else:
        d1, d2 = (float(x) for x in d1_d2(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q))
        key = "pricer.hero.explain_fx" if ctx.is_fx else "pricer.hero.explain_stock"
        text = tx(
            key, price=ctx.money(headline), pct=pct, moneyness=moneyness_text(spec, ctx),
            d1=d1, d2=d2, forward=ctx.money(fwd, 4) if not ctx.is_fx else f"{fwd:.5f}",
            base=ctx.base, quote=ctx.quote, notional=ctx.notional_million(headline),
            pips=f"{headline / ctx.pip:,.1f}",
        )
    explain(text)

    # ------------------------------------------------------------- methods
    section(tx("pricer.methods.title"))
    reference = headline
    ref_method = Method.BINOMIAL if american else Method.BLACK_SCHOLES
    decimals = ctx.price_decimals + 2
    ref_str = ctx.money(reference, decimals)
    vr = tx("mc.vr." + {(True, True): "both", (True, False): "anti", (False, True): "cv",
                        (False, False): "none"}[(settings.mc_antithetic, settings.mc_control_variate)])
    desc_fmt = dict(steps=settings.binomial_steps, paths=settings.mc_paths, grid=settings.pde_space_steps, vr=vr)
    rows_html = []
    for m in Method:
        res = results[m]
        desc = tx(f"method.{m.value}.desc", **desc_fmt)
        name_cell = (f'<td><div class="name">{html.escape(upper(method_label(m)))}</div>'
                     f'<div class="desc">{html.escape(desc)}</div></td>')
        if not res.available:
            rows_html.append(f'<tr class="na">{name_cell}<td class="num price">–</td>'
                             f'<td class="num detail" colspan="2">{html.escape(tx("pricer.unavailable"))}</td></tr>')
            continue
        price_html, _ = agreement_html(ctx.money(res.price, decimals), ref_str)
        if m is ref_method:
            diff_html = f'<span class="opl-tag">{html.escape(tx("pricer.ledger.reference"))}</span>'
        else:
            diff = res.price - reference
            diff_html = html.escape(t("pips", x=signed(diff / ctx.pip, 2)) if ctx.is_fx else signed(diff, decimals))
        detail = []
        if m is Method.MONTE_CARLO:
            detail.append(tx("pricer.ci", lo=ctx.money(res.ci_low), hi=ctx.money(res.ci_high),
                             se=f"{res.std_error:.{decimals}f}"))
        if is_pro():
            detail.append(tx("pricer.runtime", ms=res.runtime_ms))
        rows_html.append(
            f'<tr class="{"ref" if m is ref_method else ""}">{name_cell}'
            f'<td class="num price">{price_html}</td><td class="num">{diff_html}</td>'
            f'<td class="detail">{"<br>".join(html.escape(d) for d in detail)}</td></tr>'
        )
    st.html(
        '<table class="opl-ledger"><thead><tr>'
        f'<th>{html.escape(upper(t("pricer.ledger.method")))}</th>'
        f'<th class="num">{html.escape(upper(t("pricer.ledger.price")))}</th>'
        f'<th class="num">{html.escape(upper(tx("pricer.ledger.diff")))}</th>'
        f'<th class="detail">{html.escape(upper(tx("pricer.ledger.detail")))}</th>'
        f'</tr></thead><tbody>{"".join(rows_html)}</tbody></table>'
        f'<p class="opl-note">{html.escape(tx("pricer.ledger.key"))}</p>'
    )

    available = [r.price for r in results.values() if r.available]
    spread = max(abs(p - reference) for p in available)
    mc = results[Method.MONTE_CARLO]
    if american:
        msg = tx("pricer.methods.agree_american", spread=ctx.money(spread, ctx.price_decimals + 2))
    else:
        msg = tx("pricer.methods.agree", spread=ctx.money(spread, ctx.price_decimals + 2),
                 model=t(model_key, "Pro"),
                 ci=f"[{ctx.money(mc.ci_low, ctx.price_decimals + 2)}, {ctx.money(mc.ci_high, ctx.price_decimals + 2)}]")
    explain(msg)

    # -------------------------------------------------------------- greeks
    section(tx("pricer.greeks.title"), tx("pricer.greeks.lede"))
    primary = gks[Method.BLACK_SCHOLES] or gks[Method.BINOMIAL]
    symbols = {"delta": "Δ", "gamma": "Γ", "vega": "ν", "theta": "Θ", "rho": "ρ"}
    # Display-only scales for the micro-bars: |Δ| is in [0, 1]; Γ and ν are shown relative to
    # their at-the-money maximum. Θ and ρ get a sign indicator only.
    sq_t = math.sqrt(max(spec.T, 1e-9))
    disc_q = math.exp(-spec.q * spec.T)
    gamma_atm = disc_q * 0.3989422804 / (spec.S * spec.sigma * sq_t)
    vega_atm = spec.S * disc_q * 0.3989422804 * sq_t / 100
    one = "$1" if not ctx.is_fx else "0.01"
    strip = []
    for name in GREEK_NAMES:
        v = greek_display(name, getattr(primary, name))
        if name == "delta":
            value_txt, bar = f"{v:+.4f}", min(abs(v), 1.0)
            note = tx("greek.delta.explain", one=one, value=ctx.money(v * (0.01 if ctx.is_fx else 1), ctx.price_decimals))
        elif name == "gamma":
            value_txt, bar = f"{v:.5f}" if not ctx.is_fx else f"{v:.3f}", min(abs(v) / gamma_atm, 1.0) if gamma_atm else 0
            note = tx("greek.gamma.explain")
        elif name == "vega":
            value_txt = f"{v:+.4f}" if not ctx.is_fx else f"{v:+.6f}"
            bar = min(abs(v) / vega_atm, 1.0) if vega_atm else 0
            note = tx("greek.vega.explain", value=ctx.money(v, ctx.price_decimals + (1 if ctx.is_fx else 0)))
        else:
            value_txt, bar = (f"{v:+.4f}" if not ctx.is_fx else f"{v:+.6f}"), None
            note = tx(f"greek.{name}.explain", value=ctx.money(v, ctx.price_decimals + (1 if ctx.is_fx else 0)))
        value_txt = value_txt.replace("-", "−")
        sign = "" if v == 0 or not math.isfinite(v) else (
            '<span class="opl-sign pos">+</span>' if v > 0 else '<span class="opl-sign neg">−</span>')
        bar_html = (f'<div class="bar"><i style="left:0;width:{100 * bar:.1f}%"></i></div>'
                    if bar is not None else '<div class="bar"></div>')
        title = t(f"greek.{name}.short") if is_pro() else tx(f"greek.{name}.name")
        strip.append(
            '<div class="opl-cell opl-greek">'
            f'<div><span class="sym">{symbols[name]}</span><span class="name">{html.escape(upper(title))}</span>{sign}</div>'
            f'<div class="v">{html.escape(value_txt)}</div>'
            f'<div class="s">{html.escape(upper(t(f"greek.{name}.unit")))}</div>{bar_html}'
            + ("" if is_pro() else f'<div class="note">{html.escape(note)}</div>')
            + "</div>"
        )
    st.html(f'<div class="opl-grid" style="grid-template-columns:repeat(5, minmax(0, 1fr))">{"".join(strip)}</div>')

    if is_pro():
        rows = []
        for name in GREEK_NAMES:
            row = {t("pricer.greeks.col.greek"): t(f"greek.{name}.name", "Pro")}
            vals = {}
            for m in Method:
                g = gks[m]
                v = greek_display(name, getattr(g, name)) if g is not None else float("nan")
                vals[m] = v
                row[t(f"method.short.{m.value}")] = v
            ref = vals[Method.BLACK_SCHOLES] if math.isfinite(vals[Method.BLACK_SCHOLES]) else vals[Method.BINOMIAL]
            diffs = [abs(v - ref) for m, v in vals.items() if math.isfinite(v)]
            row[t("pricer.greeks.col.maxdiff")] = max(diffs) if diffs else float("nan")
            rows.append(row)
        df = pd.DataFrame(rows).dropna(axis=1, how="all")  # drop methods that cannot price this contract
        num_cols = [c for c in df.columns if c != t("pricer.greeks.col.greek")]
        config = {c: st.column_config.NumberColumn(c, format="%.5f") for c in num_cols}
        if t("method.short.black_scholes") in df.columns:
            config[t("method.short.black_scholes")] = st.column_config.NumberColumn(
                t("pricer.greeks.col.analytical"), format="%.5f")
        config[t("pricer.greeks.col.maxdiff")] = st.column_config.NumberColumn(
            t("pricer.greeks.col.maxdiff"), format="%.2e", help=t("pricer.greeks.col.maxdiff_help"))
        st.html('<div style="height:0.6rem"></div>')
        st.dataframe(df, hide_index=True, width="stretch", column_config=config)

    # --------------------------------------------------------------- chart
    section(tx("pricer.chart.title"))
    p = palette()
    lo, hi = spec.S * math.exp(-3.2 * spec.sigma * math.sqrt(max(spec.T, 1 / 365))), spec.S * math.exp(
        3.2 * spec.sigma * math.sqrt(max(spec.T, 1 / 365))
    )
    lo, hi = min(lo, spec.K * 0.85), max(hi, spec.K * 1.15)
    grid = np.linspace(lo, hi, 300)
    today = black_scholes_price(grid, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type)
    phi = 1 if spec.option_type is OptionType.CALL else -1
    expiry = np.maximum(phi * (grid - spec.K), 0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grid, y=expiry, name=tx("pricer.chart.expiry"),
                             line=dict(color=p.label, width=1.5, dash="dash"), hovertemplate="%{y:.4f}"))
    fig.add_trace(go.Scatter(x=grid, y=today, name=tx("pricer.chart.today") + (" (European)" if american and is_pro() else ""),
                             line=dict(color=p.accent, width=2), hovertemplate="%{y:.4f}"))
    fig.add_trace(go.Scatter(x=[spec.S], y=[headline], mode="markers", name=tx("pricer.chart.spot"),
                             marker=dict(color=p.accent, size=9, symbol="square", line=dict(color=p.canvas, width=2)),
                             hovertemplate="%{y:.4f}"))
    fig.add_vline(x=spec.K, line=dict(color=p.muted, width=1, dash="dash"),
                  annotation_text="K" if is_pro() else upper(t("in.K.label")), annotation_position="top left",
                  annotation_font=dict(size=10, color=p.label))
    style_figure(fig, height=330, x_title=tx("pricer.chart.x"), y_title=tx("pricer.chart.y"))
    show(fig, key="pricer_value_chart")
