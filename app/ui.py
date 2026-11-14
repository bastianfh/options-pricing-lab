"""Shared UI building blocks: mode toggle, sidebar, page headers, input panel, cards, number formatting.

Pages import from here so layout and behaviour are identical everywhere.
All wording comes from :mod:`app.content`.
"""

from __future__ import annotations

import ast
import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import streamlit as st

from app.content import CURRENCY_SYMBOLS, FX_PAIRS, PLAIN, PRO, t
from pricing.engine import NumericalSettings, OptionSpec

REPO_URL = "https://github.com/bastianfh/options-pricing-lab"
DAYS_PER_YEAR = 365.0

# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------

def mode() -> str:
    """Current explanation mode: ``PLAIN`` or ``PRO``."""
    return PRO if st.session_state.get("mode") == PRO else PLAIN


def is_pro() -> bool:
    return mode() == PRO


def tx(key: str, **fmt: object) -> str:
    """Wording for ``key`` in the current mode."""
    return t(key, mode(), **fmt)


# ---------------------------------------------------------------------------
# Global styling and sidebar
# ---------------------------------------------------------------------------

def inject_css() -> None:
    """Load ``style.css`` (all tokens are static: the app is locked to one dark palette)."""
    css = (Path(__file__).parent / "style.css").read_text()
    st.html(f"<style>{css}</style>")


GREEK_LOWER = set("αβγδεζηθικλμνξοπρσςτυφχψω")


def upper(text: str) -> str:
    """Upper-case ``text`` for micro-labels, keeping Greek letters and anything in [brackets] as written.

    CSS ``text-transform`` would turn σ into Σ and r_d into R_D, so labels are cased here instead.
    """
    out, depth = [], 0
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(depth - 1, 0)
        out.append(ch if depth or ch in GREEK_LOWER else ch.upper())
    return "".join(out)


def lbl(key: str, **fmt: object) -> str:
    """Wording for ``key`` in the current mode, styled as an uppercase hardware label."""
    return upper(tx(key, **fmt))


def _next_index() -> int:
    st.session_state["_mod_idx"] = st.session_state.get("_mod_idx", 0) + 1
    return st.session_state["_mod_idx"]


def reset_module_index() -> None:
    """Restart module numbering (01, 02, ...) at the top of every page run."""
    st.session_state["_mod_idx"] = 0


NAV_ORDER = ["pricer", "greeks", "payoff", "surface", "validation", "methods"]


def _on_nav() -> None:
    target = st.session_state.get("nav_tool")
    if target:
        st.session_state["_goto"] = target


def init_mode() -> None:
    """Set the explanation mode once per session, honouring a shared ``?mode=Pro`` link.

    The toggle is deliberately *not* bound to the URL with ``bind="query-params"``:
    ``st.switch_page`` clears query parameters on every page change, and Streamlit
    refuses to clear a bound parameter, which crashed page switches in Pro mode.
    Instead the mode lives in session state and the URL is updated by hand.
    """
    if "mode" not in st.session_state:
        requested = str(st.query_params.get("mode", "")).strip().lower()
        st.session_state["mode"] = PRO if requested == "pro" else PLAIN


def _mode_query_params() -> dict[str, str]:
    return {"mode": PRO} if st.session_state.get("mode") == PRO else {}


def _sync_mode_param() -> None:
    """Keep ``?mode=Pro`` in the address bar so the current view can be shared."""
    if st.session_state.get("mode") == PRO:
        st.query_params["mode"] = PRO
    elif "mode" in st.query_params:
        del st.query_params["mode"]


def render_topbar(current: str) -> None:
    """Telemetry bar: wordmark, mechanical tool tabs, live parameter readout, status LED, Plain/Pro switch."""
    s = st.session_state
    st.session_state["nav_tool"] = current
    american = s.get("in_exercise") == "american"
    fx = s.get("in_asset") == "fx"
    model = "CRR/PDE" if american else ("GK" if fx else "BSM")
    with st.container(horizontal=True, key="topbar", vertical_alignment="center", gap="small"):
        st.html('<div class="opl-wordmark">OPL<b>/</b>LAB</div>')
        st.segmented_control(
            "Tool",
            options=NAV_ORDER,
            format_func=lambda k: f"[{NAV_ORDER.index(k) + 1:02d}] {upper(t(f'navshort.{k}'))}",
            key="nav_tool",
            required=True,
            on_change=_on_nav,
            label_visibility="collapsed",
        )
        st.html(
            '<div class="opl-telemetry">'
            f"<span>MODEL <b>{model}</b></span>"
            f"<span>r <b>{float(s.get('in_r', 0)):.2f}%</b></span>"
            f"<span>σ <b>{float(s.get('in_vol', 0)):.1f}%</b></span>"
            f"<span>T <b>{int(s.get('in_days', 0))}d</b></span>"
            '<span><i class="opl-led"></i><b>LIVE</b></span>'
            "</div>"
        )
        st.space("stretch")
        st.segmented_control(
            upper(t("mode.label")),
            options=[PLAIN, PRO],
            key="mode",
            required=True,
            on_change=_sync_mode_param,
            help=t("mode.help"),
            label_visibility="collapsed",
            persist_state="session",
        )


def page_header(title_key: str, lede_key: str) -> None:
    """Compact context line: page code and a one-line description (no hero)."""
    st.html(
        '<div class="opl-context">'
        f"<b>{html.escape(upper(tx(title_key)))}</b>"
        f'<span class="lede">{html.escape(tx(lede_key))}</span></div>'
    )


def section(title: str, lede: Optional[str] = None) -> None:
    """Numbered module header (``02 // TITLE``) on a hairline rule, with an optional short note."""
    lede_html = f'<p class="opl-section-lede">{html.escape(lede)}</p>' if lede else ""
    st.html(
        f'<div class="opl-section"><div class="opl-module-title"><i>{_next_index():02d}</i> // '
        f"{html.escape(upper(title))}</div>{lede_html}</div>"
    )


def explain(text: str) -> None:
    """A one-line plain-language explanation under a result."""
    st.html(f'<p class="opl-explain">{html.escape(text)}</p>')


def stat(label: str, value: str, sub: str = "", tone: str = "", size: str = "md") -> str:
    """HTML for a labelled number. ``tone`` in {"", "gain", "loss", "muted"}; ``size`` in {"xl", "lg", "md"}."""
    sub_html = f'<div class="opl-stat-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="opl-stat opl-stat-{size}">'
        f'<div class="opl-stat-label">{html.escape(upper(label))}</div>'
        f'<div class="opl-stat-value {tone}">{html.escape(value)}</div>{sub_html}</div>'
    )


def cells(items: list[tuple[str, str, str, str]], columns: Optional[int] = None, extra_class: str = "") -> str:
    """HTML for an exposed hairline grid of readout cells.

    Each item is ``(label, value, sub, tone)`` with ``tone`` in {"", "pos", "neg", "acc", "vol"}.
    Adjacent cells share a single 1px rule, like modules on a hardware panel.
    """
    n = columns or len(items)
    body = "".join(
        f'<div class="opl-cell"><div class="k">{html.escape(upper(k))}</div>'
        f'<div class="v {tone}">{html.escape(v)}</div>'
        + (f'<div class="s">{html.escape(sub)}</div>' if sub else "")
        + "</div>"
        for k, v, sub, tone in items
    )
    return (f'<div class="opl-grid {extra_class}" style="grid-template-columns:repeat({n}, minmax(0, 1fr))">'
            f"{body}</div>")


def card(key: str) -> st.delta_generator.DeltaGenerator:
    """An outlined group for a single result (styled via the ``card_`` key prefix in style.css). Use sparingly."""
    return st.container(border=True, key=f"card_{key}")


def panel(key: str) -> st.delta_generator.DeltaGenerator:
    """A tinted surface for a group of inputs (styled via the ``panel_`` key prefix in style.css)."""
    return st.container(key=f"panel_{key}")


def panel_title(text: str) -> None:
    """Numbered header for a control bay, e.g. ``01 // PARAMETERS``."""
    st.html(f'<div class="opl-panel-title"><i>{_next_index():02d}</i> // {html.escape(upper(text))}</div>')


def agreement_html(value: str, reference: str) -> tuple[str, int]:
    """Split ``value`` into the characters that match ``reference`` and the rest.

    Returns HTML with the diverging tail wrapped in ``.diverge`` (shown faded), and
    the number of decimal places on which the two agree. Both strings must be
    formatted with the same number of decimals.
    """
    n = 0
    while n < min(len(value), len(reference)) and value[n] == reference[n]:
        n += 1
    decimals_agreed = max(0, n - (reference.find(".") + 1)) if "." in reference else 0
    head, tail = html.escape(value[:n]), html.escape(value[n:])
    return (head + (f'<span class="diverge">{tail}</span>' if tail else "")), decimals_agreed


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

STOCK_DEFAULTS = dict(S=100.0, K=100.0, vol=20.0, r=4.0, q=0.0)
FX_DEFAULTS = dict(S=1.0850, K=1.1000, vol=7.5, r=4.3, q=2.5)

DEFAULTS: dict[str, object] = dict(
    asset="stock",
    pair="EUR/USD",
    option_type="call",
    exercise="european",
    days=182,
    **STOCK_DEFAULTS,
    steps=500,
    paths=100_000,
    antithetic=True,
    cv=True,
    seed=42,
    grid=400,
)


def init_state() -> None:
    """Seed every persistent input with its default (only on first run)."""
    for name, value in DEFAULTS.items():
        st.session_state.setdefault(f"in_{name}", value)


def apply_values(**values: object) -> None:
    """Set input values, e.g. from a preset. Call from a widget callback."""
    for name, value in values.items():
        st.session_state[f"in_{name}"] = value


def _reset_strategy_strikes() -> None:
    """Keep the Payoff page's strikes sensible after the spot changes scale (stock <-> FX)."""
    spot = float(st.session_state["in_S"])
    fx = st.session_state.get("in_asset") == "fx"
    st.session_state["pay_center"] = round(spot, 4 if fx else 0)
    st.session_state["pay_width"] = round(spot * 0.05, 4 if fx else 0)
    st.session_state.pop("pay_custom_df", None)


def _on_asset_change() -> None:
    defaults = FX_DEFAULTS if st.session_state["in_asset"] == "fx" else STOCK_DEFAULTS
    apply_values(**defaults)
    _reset_strategy_strikes()


def _on_pair_change() -> None:
    pair = st.session_state["in_pair"]
    if pair.endswith("JPY"):
        apply_values(S=155.00, K=155.00, vol=10.0, r=0.5, q=4.3)
    elif pair == "EUR/USD":
        apply_values(**FX_DEFAULTS)
    else:
        spot = {"GBP/USD": 1.2700, "AUD/USD": 0.6600, "USD/CHF": 0.8800, "USD/CAD": 1.3700}[pair]
        apply_values(S=spot, K=spot, vol=8.0)
    _reset_strategy_strikes()


@dataclass(frozen=True)
class Context:
    """Display context for formatting numbers: asset class and currencies."""

    asset: str
    pair: str
    base: str
    quote: str
    pip: float

    @property
    def is_fx(self) -> bool:
        return self.asset == "fx"

    @property
    def symbol(self) -> str:
        return "$" if not self.is_fx else CURRENCY_SYMBOLS.get(self.quote, "")

    @property
    def price_decimals(self) -> int:
        if not self.is_fx:
            return 2
        return 3 if self.pip >= 0.01 else 5

    @property
    def spot_step(self) -> float:
        return 1.0 if not self.is_fx else self.pip * 10

    def money(self, x: float, decimals: Optional[int] = None) -> str:
        """Price in the quote currency, e.g. ``$4.12`` or ``0.01234``."""
        if x is None or not math.isfinite(x):
            return "–"
        d = self.price_decimals if decimals is None else decimals
        if self.is_fx:
            return f"{x:,.{d}f}".replace("-", "−")
        sign = "−" if x < 0 else ""
        return f"{sign}${abs(x):,.{d}f}"

    def spot(self, x: float) -> str:
        return f"{x:,.{4 if self.is_fx and self.pip < 0.01 else 2}f}" if self.is_fx else f"${x:,.2f}"

    def notional_million(self, x: float) -> str:
        """Premium on a 1m base-currency notional, in quote currency."""
        value = x * 1_000_000
        return f"{self.symbol}{value:,.0f}" if self.symbol else f"{value:,.0f} {self.quote}"


def context() -> Context:
    asset = st.session_state.get("in_asset", "stock")
    pair = st.session_state.get("in_pair", "EUR/USD")
    base, quote, pip = FX_PAIRS.get(pair, ("EUR", "USD", 1e-4))
    return Context(asset, pair, base, quote, pip)


def signed(x: float, decimals: int = 4) -> str:
    """Signed number with a proper minus sign."""
    if x is None or not math.isfinite(x):
        return "–"
    s = f"{abs(x):,.{decimals}f}"
    return ("−" if x < 0 else "+") + s


def input_panel(
    *,
    contract: bool = True,
    exercise: bool = True,
    numerics: bool = True,
    option_type: bool = True,
    strike: bool = True,
) -> tuple[OptionSpec, NumericalSettings, Context]:
    """Render the shared input form and return the resulting contract, settings and display context.

    Values persist across pages (``persist_state="session"``), so a contract set
    up on one page carries over to the others.
    """
    init_state()
    ctx = context()
    pro = is_pro()

    st.segmented_control(
        lbl("in.asset.label"),
        options=["stock", "fx"],
        format_func=lambda v: upper(tx(f"in.asset.{v}")),
        key="in_asset",
        required=True,
        help=tx("in.asset.help"),
        on_change=_on_asset_change,
        persist_state="session",
        width="stretch",
    )
    ctx = context()
    if ctx.is_fx:
        st.selectbox(
            lbl("in.pair.label"), list(FX_PAIRS), key="in_pair", help=tx("in.pair.help"),
            on_change=_on_pair_change, persist_state="session",
        )
        ctx = context()

    if contract:
        if option_type:
            st.segmented_control(
                lbl("in.option_type.label"),
                options=["call", "put"],
                format_func=lambda v: upper(tx(f"in.option_type.{v}")),
                key="in_option_type",
                required=True,
                help=tx("in.option_type.help"),
                persist_state="session",
                width="stretch",
            )
        if exercise:
            st.segmented_control(
                lbl("in.exercise.label"),
                options=["european", "american"],
                format_func=lambda v: upper(tx(f"in.exercise.{v}")),
                key="in_exercise",
                required=True,
                help=tx("in.exercise.help"),
                persist_state="session",
                width="stretch",
            )

    fmt = f"%.{4 if ctx.is_fx and ctx.pip < 0.01 else 2}f"
    st.number_input(
        lbl("in.S.label"), min_value=1e-4, step=ctx.spot_step, format=fmt, key="in_S",
        help=tx("in.S.help"), persist_state="session",
    )
    if strike:
        st.number_input(
            lbl("in.K.label"), min_value=1e-4, step=ctx.spot_step, format=fmt, key="in_K",
            help=tx("in.K.help"), persist_state="session",
        )
    st.number_input(
        lbl("in.days.label"), min_value=1, max_value=3650, step=1, key="in_days",
        help=tx("in.days.help"), persist_state="session",
    )
    st.number_input(
        lbl("in.vol.label"), min_value=0.5, max_value=300.0, step=0.5, format="%.1f", key="in_vol",
        help=tx("in.vol.help"), persist_state="session",
    )

    rate_key, carry_key = ("in.r_fx", "in.q_fx") if ctx.is_fx else ("in.r", "in.q")
    names = dict(base=ctx.base, quote=ctx.quote)
    if ctx.is_fx or pro:
        st.number_input(
            lbl(f"{rate_key}.label", **names), min_value=-5.0, max_value=50.0, step=0.25, format="%.2f",
            key="in_r", help=tx(f"{rate_key}.help"), persist_state="session",
        )
        st.number_input(
            lbl(f"{carry_key}.label", **names), min_value=-5.0, max_value=50.0, step=0.25, format="%.2f",
            key="in_q", help=tx(f"{carry_key}.help"), persist_state="session",
        )
    else:
        with st.expander(tx("inputs.numerics")):
            st.number_input(
                lbl("in.r.label"), min_value=-5.0, max_value=50.0, step=0.25, format="%.2f",
                key="in_r", help=tx("in.r.help"), persist_state="session",
            )
            st.number_input(
                lbl("in.q.label"), min_value=0.0, max_value=50.0, step=0.25, format="%.2f",
                key="in_q", help=tx("in.q.help"), persist_state="session",
            )

    T = st.session_state["in_days"] / DAYS_PER_YEAR
    if pro:
        st.caption(tx("in.T_years", T=T))

    settings = NumericalSettings()
    if numerics and pro:
        with st.expander(tx("inputs.numerics"), expanded=False):
            st.caption(tx("inputs.numerics_hint"))
            n1, n2 = st.columns(2)
            n1.number_input(lbl("in.steps.label"), 10, 5000, step=50, key="in_steps",
                            help=tx("in.steps.help"), persist_state="session")
            n2.number_input(lbl("in.grid.label"), 20, 2000, step=50, key="in_grid",
                            help=tx("in.grid.help"), persist_state="session")
            st.select_slider(lbl("in.paths.label"), [1_000, 5_000, 10_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
                             key="in_paths", format_func=lambda v: f"{v:,}", help=tx("in.paths.help"),
                             persist_state="session")
            v1, v2 = st.columns(2)
            v1.toggle(lbl("in.antithetic.label"), key="in_antithetic", help=tx("in.antithetic.help"),
                      persist_state="session")
            v2.toggle(lbl("in.cv.label"), key="in_cv", help=tx("in.cv.help"), persist_state="session")
            st.number_input(lbl("in.seed.label"), 0, 2**31 - 1, step=1, key="in_seed",
                            help=tx("in.seed.help"), persist_state="session")
        s = st.session_state
        settings = NumericalSettings(
            binomial_steps=int(s["in_steps"]),
            mc_paths=int(s["in_paths"]),
            mc_antithetic=bool(s["in_antithetic"]),
            mc_control_variate=bool(s["in_cv"]),
            mc_seed=int(s["in_seed"]),
            pde_space_steps=int(s["in_grid"]),
            pde_time_steps=int(s["in_grid"]),
        )

    s = st.session_state
    spec = OptionSpec(
        S=float(s["in_S"]),
        K=float(s["in_K"]),
        T=T,
        r=float(s["in_r"]) / 100.0,
        sigma=float(s["in_vol"]) / 100.0,
        q=float(s["in_q"]) / 100.0,
        option_type=s["in_option_type"] if contract and option_type else "call",
        exercise=s["in_exercise"] if contract and exercise else "european",
    )
    return spec, settings, ctx


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict[str, object]] = {
    "protect": dict(
        values=dict(asset="stock", option_type="put", exercise="european", S=100.0, K=95.0, days=182,
                    vol=25.0, r=4.0, q=0.0),
        page="payoff", strategy="protective_put",
    ),
    "bigmove": dict(
        values=dict(asset="stock", option_type="call", exercise="european", S=100.0, K=100.0, days=60,
                    vol=30.0, r=4.0, q=0.0),
        page="payoff", strategy="straddle",
    ),
    "fx": dict(
        values=dict(asset="fx", pair="EUR/USD", option_type="call", exercise="european", S=1.0850, K=1.1000,
                    days=91, vol=7.5, r=4.3, q=2.5),
        page="pricer", strategy="long_call",
    ),
    "income": dict(
        values=dict(asset="stock", option_type="call", exercise="european", S=100.0, K=110.0, days=91,
                    vol=22.0, r=4.0, q=1.0),
        page="payoff", strategy="covered_call",
    ),
}


def _load_preset(name: str) -> None:
    preset = PRESETS[name]
    apply_values(**preset["values"])
    st.session_state["pay_strategy"] = preset["strategy"]
    st.session_state["pay_center"] = preset["values"]["K"]
    st.session_state["_goto"] = preset["page"]


def preset_buttons() -> None:
    """Example scenarios as a row of buttons; clicking one loads it and opens the relevant page."""
    with st.container(horizontal=True, gap="small"):
        for name in PRESETS:
            st.button(
                upper(tx(f"preset.{name}.title")),
                key=f"preset_{name}",
                on_click=_load_preset,
                args=(name,),
                help=tx(f"preset.{name}.desc"),
            )


def _on_preset_pill() -> None:
    choice = st.session_state.get("preset_pill")
    if choice:
        _load_preset(choice)
    st.session_state["preset_pill"] = None


def preset_pills() -> None:
    """Compact preset selector (one row of pills)."""
    st.pills(
        lbl("presets.title"),
        options=list(PRESETS),
        format_func=lambda n: upper(tx(f"preset.{n}.title")),
        key="preset_pill",
        on_change=_on_preset_pill,
        help=tx("presets.subtitle"),
    )


def handle_navigation(pages: dict[str, st.Page]) -> None:
    """Follow a pending page switch requested by a callback (callbacks cannot switch pages)."""
    target = st.session_state.pop("_goto", None)
    if target and target in pages:
        st.switch_page(pages[target], query_params=_mode_query_params() or None)


def cached(fn: Callable) -> Callable:
    """Shorthand for ``st.cache_data`` with a bounded cache."""
    return st.cache_data(show_spinner=False, max_entries=64)(fn)


@st.cache_resource(show_spinner=False)
def count_tests() -> int:
    """Number of test cases in ``tests/``, counting each parametrisation (static AST scan, no pytest needed).

    For every ``test_*`` function, multiplies the lengths of literal lists in its
    ``@pytest.mark.parametrize`` decorators. Matches ``pytest --collect-only``
    for this suite, which only uses literal parameter lists.
    """
    total = 0
    for path in (Path(__file__).resolve().parent.parent / "tests").glob("test_*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                cases = 1
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "parametrize":
                        values = dec.args[1] if len(dec.args) > 1 else None
                        if isinstance(values, (ast.List, ast.Tuple)):
                            cases *= len(values.elts)
                        elif isinstance(values, ast.Name):
                            cases *= _module_list_length(tree, values.id)
                total += cases
    return total


def _module_list_length(tree: "ast.Module", name: str) -> int:
    """Length of a module-level list/tuple literal ``name = [...]`` (1 if not found)."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t_, "id", None) == name for t_ in node.targets):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                return len(node.value.elts)
    return 1
