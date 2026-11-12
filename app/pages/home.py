"""Home: one-line pitch, a quick price card, examples and links to every section."""

from __future__ import annotations

import html

import streamlit as st

from app.content import t
from app.ui import (
    card,
    context,
    count_tests,
    explain,
    init_state,
    is_pro,
    preset_buttons,
    section,
    stat,
    tx,
)
from pricing.engine import Method, OptionSpec, price

init_state()
ctx = context()

hero, quick = st.columns([1.25, 1], gap="large", vertical_alignment="center")

with hero:
    st.html(
        '<div class="opl-header opl-hero">'
        f'<div class="opl-eyebrow">{html.escape(t("app.name"))}</div>'
        f"<h1>{html.escape(tx('home.title'))}</h1>"
        f'<p class="opl-lede">{html.escape(tx("home.lede"))}</p>'
        '<div class="opl-statstrip">'
        f'<div><div class="num">4</div><div class="lbl">{html.escape(tx("home.stat.methods"))}</div></div>'
        f'<div><div class="num">{count_tests()}</div><div class="lbl">{html.escape(tx("home.stat.tests"))}</div></div>'
        f'<div><div class="num">0</div><div class="lbl">{html.escape(tx("home.stat.libs"))}</div></div>'
        "</div></div>"
    )

with quick:
    with card("quick"):
        st.html(f'<div class="opl-card-title">{html.escape(tx("home.quick.title"))}</div>')
        st.segmented_control(
            tx("in.option_type.label"),
            options=["call", "put"],
            format_func=lambda v: tx(f"in.option_type.{v}"),
            key="in_option_type",
            required=True,
            persist_state="session",
            label_visibility="collapsed",
            width="stretch",
        )
        fmt = "%.4f" if ctx.is_fx else "%.2f"
        a, b = st.columns(2)
        a.number_input(tx("in.S.label"), min_value=1e-4, step=ctx.spot_step, format=fmt, key="in_S",
                       help=tx("in.S.help"), persist_state="session")
        b.number_input(tx("in.K.label"), min_value=1e-4, step=ctx.spot_step, format=fmt, key="in_K",
                       help=tx("in.K.help"), persist_state="session")
        c, d = st.columns(2)
        c.number_input(tx("in.days.label"), min_value=1, max_value=3650, key="in_days",
                       help=tx("in.days.help"), persist_state="session")
        d.number_input(tx("in.vol.label"), min_value=0.5, max_value=300.0, step=0.5, format="%.1f",
                       key="in_vol", help=tx("in.vol.help"), persist_state="session")

        s = st.session_state
        spec = OptionSpec(
            S=float(s["in_S"]), K=float(s["in_K"]), T=s["in_days"] / 365.0, r=float(s["in_r"]) / 100,
            sigma=float(s["in_vol"]) / 100, q=float(s["in_q"]) / 100, option_type=s["in_option_type"],
        )
        value = price(spec, Method.BLACK_SCHOLES).price
        pct = 100 * value / spec.S
        model = t("method.black_scholes_fx" if ctx.is_fx else "method.black_scholes", "Pro")
        label = tx("pricer.hero.label", model=model)
        st.html(stat(label, ctx.money(value), sub=f"{pct:.2f}% of spot" if is_pro() else "", size="xl"))
        if not is_pro():
            explain(t("pricer.hero.explain_stock", "Plain English", price=ctx.money(value), pct=pct, moneyness="").strip())
        st.page_link("app/pages/pricer.py", label=tx("home.quick.open") + " →")

section(tx("presets.title"), tx("presets.subtitle"))
preset_buttons()

section(tx("home.sections"))
LINKS = [
    ("pricer", "app/pages/pricer.py", ":material/calculate:"),
    ("greeks", "app/pages/greeks.py", ":material/ssid_chart:"),
    ("payoff", "app/pages/payoff.py", ":material/stacked_line_chart:"),
    ("surface", "app/pages/surface.py", ":material/3d_rotation:"),
    ("validation", "app/pages/validation.py", ":material/verified:"),
    ("methods", "app/pages/methods.py", ":material/menu_book:"),
]
for row in range(2):
    cols = st.columns(3)
    for col, (name, path, icon) in zip(cols, LINKS[row * 3:(row + 1) * 3]):
        with col, card(f"link_{name}"):
            st.page_link(path, label=t(f"nav.{name}"), icon=icon)
            st.html(f'<div class="opl-link-desc">{html.escape(tx(f"card.{name}"))}</div>')

st.caption(t("disclaimer"))
