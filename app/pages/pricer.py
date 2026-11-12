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
    cached,
    card,
    chip,
    explain,
    input_panel,
    is_pro,
    page_header,
    preset_pills,
    section,
    signed,
    stat,
    tx,
)
from pricing.engine import Method, NumericalSettings, OptionSpec, greeks, price_all
from pricing.greeks import GREEK_NAMES
from pricing.models.black_scholes import black_scholes_price, d1_d2
from pricing.utils import ExerciseStyle, OptionType

page_header("pricer.title", "pricer.lede")

if not is_pro():
    preset_pills()

left, right = st.columns([1, 2.3], gap="large")
with left, card("pricer_inputs"):
    st.html(f'<div class="opl-card-title">{html.escape(tx("inputs.contract"))}</div>')
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

    with card("pricer_hero"):
        h1, h2 = st.columns([1.35, 1], gap="medium")
        with h1:
            if american:
                label = tx("pricer.hero.label_american")
            else:
                label = tx("pricer.hero.label", model=t(model_key, "Pro"))
            st.html(stat(label, ctx.money(headline, ctx.price_decimals + (2 if is_pro() else 0)), size="xl"))

            euro = float(black_scholes_price(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type))
            if american:
                text = tx("pricer.hero.explain_american", price=ctx.money(headline),
                          premium=ctx.money(headline - euro), pde=ctx.money(results[Method.FINITE_DIFFERENCE].price))
            else:
                d1, d2 = (float(x) for x in d1_d2(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q))
                forward = spec.S * math.exp((spec.r - spec.q) * spec.T)
                key = "pricer.hero.explain_fx" if ctx.is_fx else "pricer.hero.explain_stock"
                text = tx(
                    key, price=ctx.money(headline), pct=pct, moneyness=moneyness_text(spec, ctx),
                    d1=d1, d2=d2, forward=ctx.money(forward, 4) if not ctx.is_fx else f"{forward:.5f}",
                    base=ctx.base, quote=ctx.quote, notional=ctx.notional_million(headline),
                    pips=f"{headline / ctx.pip:,.1f}",
                )
            if is_pro():
                st.html(f'<p class="opl-note">{html.escape(text)}</p>')
            else:
                explain(text)
        with h2:
            phi = 1 if spec.option_type is OptionType.CALL else -1
            intrinsic = max(phi * (spec.S - spec.K), 0.0)
            if is_pro():
                fwd = spec.S * math.exp((spec.r - spec.q) * spec.T)
                pv_intr = max(phi * (spec.S * math.exp(-spec.q * spec.T) - spec.K * math.exp(-spec.r * spec.T)), 0)
                st.html(
                    stat("Intrinsic max(φ(S−K), 0)", ctx.money(intrinsic), size="sm")
                    + "<div style='height:.8rem'></div>"
                    + stat("Time value", ctx.money(headline - intrinsic), size="sm")
                    + "<div style='height:.8rem'></div>"
                    + stat("Forward F", f"{fwd:,.{5 if ctx.is_fx else 2}f}",
                           sub=f"PV intrinsic on forward {ctx.money(pv_intr)}", size="sm")
                )
            else:
                st.html(
                    stat("Worth if used right now", ctx.money(intrinsic), size="sm")
                    + "<div style='height:.8rem'></div>"
                    + stat("Extra for the time left", ctx.money(headline - intrinsic), size="sm")
                    + "<div style='height:.8rem'></div>"
                    + stat("Expires in", f"{st.session_state['in_days']} days", size="sm")
                )

    # ------------------------------------------------------------- methods
    section(tx("pricer.methods.title"))
    reference = headline
    cols = st.columns(4, gap="small")
    for col, m in zip(cols, Method):
        res = results[m]
        with col, card(f"method_{m.value}"):
            desc_fmt = dict(
                steps=settings.binomial_steps, paths=settings.mc_paths, grid=settings.pde_space_steps,
                vr=tx("mc.vr." + {(True, True): "both", (True, False): "anti", (False, True): "cv",
                                  (False, False): "none"}[(settings.mc_antithetic, settings.mc_control_variate)]),
            )
            desc = tx(f"method.{m.value}.desc", **desc_fmt)
            if res.available:
                diff = res.price - reference
                tone = ""  # a numerical difference is neither good nor bad: keep it neutral
                diff_txt = tx("pricer.vs_reference", diff=signed(diff, ctx.price_decimals + 2))
                meta = []
                if m is Method.MONTE_CARLO:
                    meta.append(tx("pricer.ci", lo=ctx.money(res.ci_low), hi=ctx.money(res.ci_high),
                                   se=f"{res.std_error:.{ctx.price_decimals + 2}f}"))
                if is_pro():
                    meta.append(tx("pricer.runtime", ms=res.runtime_ms))
                body = (
                    f'<div class="opl-method-price">{html.escape(ctx.money(res.price, ctx.price_decimals + (2 if is_pro() else 0)))}</div>'
                    + (chip(diff_txt, "accent" if m is Method.BLACK_SCHOLES and not american else tone)
                       if not (m is Method.BLACK_SCHOLES or (american and m is Method.BINOMIAL))
                       else chip("reference" if is_pro() else "exact answer", "accent"))
                    + "".join(f'<div class="opl-method-meta">{html.escape(x)}</div>' for x in meta)
                )
                cls = "opl-method"
            else:
                body = (
                    '<div class="opl-method-price">–</div>'
                    + chip(tx("pricer.unavailable"))
                )
                cls = "opl-method unavailable"
            st.html(
                f'<div class="{cls}"><div class="opl-method-name">{html.escape(method_label(m))}</div>'
                f'<div class="opl-method-desc">{html.escape(desc)}</div>{body}</div>'
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
    if is_pro():
        st.html(f'<p class="opl-note">{html.escape(msg)}</p>')
    else:
        explain(msg)

    # -------------------------------------------------------------- greeks
    section(tx("pricer.greeks.title"), tx("pricer.greeks.lede"))
    primary = gks[Method.BLACK_SCHOLES] or gks[Method.BINOMIAL]
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
        df = pd.DataFrame(rows)
        num_cols = [c for c in df.columns if c != t("pricer.greeks.col.greek")]
        config = {c: st.column_config.NumberColumn(c, format="%.5f") for c in num_cols}
        config[t("method.short.black_scholes")] = st.column_config.NumberColumn(
            t("pricer.greeks.col.analytical"), format="%.5f")
        config[t("pricer.greeks.col.maxdiff")] = st.column_config.NumberColumn(
            t("pricer.greeks.col.maxdiff"), format="%.2e", help=t("pricer.greeks.col.maxdiff_help"))
        st.dataframe(df, hide_index=True, width="stretch", column_config=config)
    else:
        one = "$1" if not ctx.is_fx else "0.01"
        rows_html = []
        for name in GREEK_NAMES:
            v = greek_display(name, getattr(primary, name))
            if name == "delta":
                explain_txt = tx("greek.delta.explain", one=one,
                                 value=ctx.money(v * (0.01 if ctx.is_fx else 1), ctx.price_decimals))
                big = f"{v:.3f}"
            elif name == "gamma":
                explain_txt = tx("greek.gamma.explain")
                big = f"{v:.4f}" if not ctx.is_fx else f"{v:.2f}"
            else:
                big = ctx.money(v, ctx.price_decimals + (1 if ctx.is_fx else 0))
                explain_txt = tx(f"greek.{name}.explain", value=big)
            rows_html.append(
                '<div class="opl-greek-row">'
                f'<div><div class="opl-greek-name">{html.escape(tx(f"greek.{name}.name"))}</div>'
                f'<div class="opl-greek-tag">{html.escape(t(f"greek.{name}.short"))}</div></div>'
                f'<div class="opl-greek-value">{html.escape(big)}</div>'
                f'<div class="opl-greek-explain">{html.escape(explain_txt)}</div></div>'
            )
        with card("greeks_plain"):
            st.html(f'<div class="opl-greek-list">{"".join(rows_html)}</div>')

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
                             line=dict(color=p.muted, width=2, dash="dash"), hovertemplate="%{y:.4f}"))
    fig.add_trace(go.Scatter(x=grid, y=today, name=tx("pricer.chart.today") + (" (European)" if american and is_pro() else ""),
                             line=dict(color=p.accent, width=2.5), hovertemplate="%{y:.4f}"))
    fig.add_trace(go.Scatter(x=[spec.S], y=[headline], mode="markers", name=tx("pricer.chart.spot"),
                             marker=dict(color=p.accent, size=10, line=dict(color="white", width=2)),
                             hovertemplate="%{y:.4f}"))
    fig.add_vline(x=spec.K, line=dict(color=p.axis, width=1, dash="dot"),
                  annotation_text="K" if is_pro() else "Agreed price", annotation_position="top left",
                  annotation_font_size=11)
    style_figure(fig, height=330, x_title=tx("pricer.chart.x"), y_title=tx("pricer.chart.y"))
    show(fig, key="pricer_value_chart")
