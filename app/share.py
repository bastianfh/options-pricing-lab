"""Shareable links: encode the current settings in a URL, and apply them when someone opens it.

A link such as ``/backtest?bt=covered_call&bt_tenor=30&ticker=KO&guide=off`` reproduces the
exact view for anyone who opens it. Every parameter is validated and cast on the way in;
anything unrecognised or out of range is ignored rather than trusted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional
from urllib.parse import urlencode, urlsplit

import streamlit as st

from app.content import PLAIN, PRO


def _num(lo: float, hi: float, integer: bool = False) -> Callable[[str], Any]:
    def cast(v: str) -> Any:
        x = float(v)
        if not lo <= x <= hi:
            raise ValueError
        return int(round(x)) if integer else x

    return cast


def _choice(*options: str) -> Callable[[str], str]:
    def cast(v: str) -> str:
        if v not in options:
            raise ValueError
        return v

    return cast


def _bool(v: str) -> bool:
    if v not in ("0", "1"):
        raise ValueError
    return v == "1"


def _iso_date(v: str) -> str:
    return date.fromisoformat(v).isoformat()


def _legs(v: str) -> str:
    from pricing.backtest import legs_from_code, legs_to_code

    return legs_to_code(legs_from_code(v))


def _sizes(v: str) -> str:
    from pricing.backtest import sizes_from_code, sizes_to_code

    return sizes_to_code(sizes_from_code(v))


MAX_COMPARE = 4


def clean_name(v: str) -> str:
    """A strategy name safe to show and to put in a link (no separators, at most 40 characters)."""
    return " ".join(str(v).replace("~", " ").replace("|", " ").split())[:40]


def encode_compare(entries: list[dict]) -> str:
    """Comparison list -> link text: ``legs~tenor~take_profit~stop_loss~name`` joined by ``|``."""
    return "|".join(
        f"{e['legs']}~{int(e['tenor'])}~{float(e.get('tp') or 0):g}~{float(e.get('sl') or 0):g}~{clean_name(e['name'])}"
        for e in entries
    )


def decode_compare(text: str) -> list[dict]:
    """Inverse of :func:`encode_compare`; raises ``ValueError`` on anything malformed."""
    from pricing.backtest import legs_from_code, legs_to_code

    entries = []
    for part in [x for x in str(text).split("|") if x]:
        legs, tenor, tp, sl, name = part.split("~", 4)
        tenor_i, tp_f, sl_f = int(tenor), float(tp), float(sl)
        if not (1 <= tenor_i <= 365) or not (0 <= tp_f <= 10) or not (0 <= sl_f <= 10):
            raise ValueError
        entries.append(dict(legs=legs_to_code(legs_from_code(legs)), tenor=tenor_i, tp=tp_f or None,
                            sl=sl_f or None, name=clean_name(name) or "Strategy"))
    if len(entries) > MAX_COMPARE:
        raise ValueError
    return entries


def _compare(v: str) -> str:
    return encode_compare(decode_compare(v))


def _name(v: str) -> str:
    v = " ".join(v.split())
    if not v or len(v) > 40 or not v.isprintable():
        raise ValueError
    return v


def _ticker(v: str) -> str:
    from marketdata.fetch import normalize_ticker

    return normalize_ticker(v)


@dataclass(frozen=True)
class Param:
    """One shareable setting: URL name, session-state key, and a validating cast."""

    name: str
    key: str
    cast: Callable[[str], Any]


STRATEGIES = ("long_call", "long_put", "straddle", "strangle", "bull_call_spread", "bear_put_spread",
              "covered_call", "protective_put", "custom")
BT_STRATEGIES = ("buy_and_hold", "covered_call", "protective_put", "collar", "cash_secured_put",
                 "long_straddle", "long_strangle", "bull_call_spread", "bear_put_spread", "iron_condor", "custom")

# Settings used by every tool (the contract and market data), then per-tool settings.
COMMON = (
    Param("a", "in_asset", _choice("stock", "fx")),
    Param("pair", "in_pair", _choice("EUR/USD", "GBP/USD", "AUD/USD", "USD/CHF", "USD/CAD", "USD/JPY")),
    Param("type", "in_option_type", _choice("call", "put")),
    Param("ex", "in_exercise", _choice("european", "american")),
    Param("S", "in_S", _num(1e-4, 1e7)),
    Param("K", "in_K", _num(1e-4, 1e7)),
    Param("days", "in_days", _num(1, 3650, integer=True)),
    Param("vol", "in_vol", _num(0.5, 300)),
    Param("r", "in_r", _num(-5, 50)),
    Param("q", "in_q", _num(-5, 50)),
)
PAGE_PARAMS: dict[str, tuple[Param, ...]] = {
    "pricer": (
        Param("N", "in_steps", _num(10, 5000, integer=True)),
        Param("paths", "in_paths", _num(1000, 1_000_000, integer=True)),
        Param("anti", "in_antithetic", _bool),
        Param("cv", "in_cv", _bool),
        Param("seed", "in_seed", _num(0, 2**31 - 1, integer=True)),
        Param("grid", "in_grid", _num(20, 2000, integer=True)),
    ),
    "market": (
        Param("ticker", "mk_ticker", _ticker),
        Param("period", "mk_period", _choice("6mo", "1y", "2y", "5y")),
    ),
    "backtest": (
        Param("ticker", "bt_ticker", _ticker),
        Param("period", "bt_period", _choice("1y", "2y", "5y", "10y")),
        Param("bt", "bt_strategy", _choice(*BT_STRATEGIES)),
        Param("legs", "bt_legs", _legs),
        Param("qty", "bt_qty", _sizes),
        Param("name", "bt_name", _name),
        Param("tenor", "bt_tenor", _num(7, 180, integer=True)),
        Param("exits", "bt_exits", _bool),
        Param("tp", "bt_tp", _num(0, 1000)),
        Param("sl", "bt_sl", _num(0, 1000)),
        Param("view", "bt_view", _choice("single", "compare")),
        Param("cmp", "bt_cmp", _compare),
        Param("otm_c", "bt_otm_call", _num(0, 50)),
        Param("otm_p", "bt_otm_put", _num(0, 50)),
        Param("wing", "bt_wing", _num(0, 50)),
        Param("vwin", "bt_window", _num(5, 252, integer=True)),
        Param("vprem", "bt_vol_premium", _num(-50, 200)),
        Param("rate", "bt_rate", _num(-5, 50)),
        Param("spread", "bt_spread", _num(0, 100)),
        Param("comm", "bt_commission", _num(0, 50)),
        Param("step", "bt_strike_step", _num(0, 100)),
        Param("from", "bt_start", _iso_date),
        Param("to", "bt_end", _iso_date),
    ),
    "payoff": (
        Param("strat", "pay_strategy", _choice(*STRATEGIES)),
        Param("center", "pay_center", _num(1e-4, 1e7)),
        Param("width", "pay_width", _num(1e-4, 1e7)),
        Param("h", "pay_horizon", _num(0, 3650, integer=True)),
        Param("live", "pay_live", _bool),
        Param("ticker", "mk_ticker", _ticker),
        Param("pexp", "pay_expiry", _iso_date),
    ),
    "greeks": (Param("greek", "gx_greek", _choice("delta", "gamma", "vega", "theta", "rho")),),
    "surface": (
        Param("atm", "vs_atm", _num(3, 80)),
        Param("skew", "vs_skew", _num(-0.3, 0.3)),
        Param("curv", "vs_curv", _num(0, 0.3)),
        Param("term", "vs_term", _num(-0.15, 0.15)),
    ),
    "validation": (
        Param("case", "val_case", _choice("atm", "otm", "itm")),
        Param("vtype", "val_type", _choice("call", "put")),
    ),
}
ALL_PARAMS: tuple[Param, ...] = COMMON + tuple(p for group in PAGE_PARAMS.values() for p in group)


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def apply_shared_settings() -> None:
    """Apply settings from a shared link (once per session, before any widget is drawn)."""
    if st.session_state.get("_shared_applied"):
        return
    st.session_state["_shared_applied"] = True
    applied = False
    for p in ALL_PARAMS:
        raw = st.query_params.get(p.name)
        if raw is None:
            continue
        try:
            st.session_state[p.key] = p.cast(str(raw))
            applied = True
        except (ValueError, TypeError):
            continue  # ignore anything malformed or out of range
    if applied:
        # A shared market ticker should load straight away on the Market tool.
        if "mk_ticker" in st.session_state and st.query_params.get("ticker"):
            st.session_state["mk_applied"] = (st.session_state["mk_ticker"], st.session_state.get("mk_period", "2y"))
        if st.query_params.get("ticker") and st.query_params.get("bt"):
            st.session_state["bt_applied"] = (st.session_state.get("bt_ticker"), st.session_state.get("bt_period", "5y"))


def share_url(page: str, base_url: Optional[str] = None) -> str:
    """A link that reopens ``page`` with the current settings."""
    params: dict[str, str] = {}
    for p in COMMON + PAGE_PARAMS.get(page, ()):
        if p.key in st.session_state and st.session_state[p.key] is not None:
            params[p.name] = _encode(st.session_state[p.key])
    if page == "backtest" and st.session_state.get("bt_strategy") != "custom":
        params.pop("legs", None)  # only custom strategies need their legs spelled out
        params.pop("name", None)
    if page == "backtest" and not st.session_state.get("bt_exits"):
        params.pop("tp", None)
        params.pop("sl", None)
    if page == "backtest" and not st.session_state.get("bt_cmp"):
        params.pop("cmp", None)
    if page == "backtest" and st.session_state.get("bt_strategy") == "custom":
        params.pop("qty", None)  # custom legs already carry their quantities
    current = st.session_state.get("mode")
    if current in (PRO, PLAIN):  # Simple is the default and needs no parameter
        params["mode"] = "Pro" if current == PRO else "Plain"
    params["guide"] = "off"
    base = base_url if base_url is not None else str(st.context.url or "")
    parts = urlsplit(base)
    root = f"{parts.scheme}://{parts.netloc}" if parts.scheme else ""
    path = "/" if page == "pricer" else f"/{page}"
    return f"{root}{path}?{urlencode(params)}"
