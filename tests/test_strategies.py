"""Multi-leg strategy payoffs, P&L and risk metrics."""

import numpy as np
import pytest

from pricing.greeks import black_scholes_greeks
from pricing.models.black_scholes import black_scholes_price
from pricing.strategies import (
    PRESETS,
    Leg,
    Strategy,
    bull_call_spread,
    covered_call,
    from_legs,
    risk_summary,
    straddle,
    strangle,
)

MKT = dict(r=0.05, sigma=0.2, q=0.0)
GRID = np.linspace(1, 200, 2000)


def test_straddle_payoff_is_absolute_distance_from_strike() -> None:
    s = straddle(100)
    np.testing.assert_allclose(s.payoff(GRID), np.abs(GRID - 100))


def test_straddle_breakevens_are_strike_plus_minus_cost() -> None:
    s = straddle(100)
    cost = s.cost(100, 0.5, **MKT)
    summary = risk_summary(s, cost, GRID)
    assert summary.breakevens == pytest.approx([100 - cost, 100 + cost], abs=1e-6)
    assert summary.max_profit is None  # unbounded upside
    assert summary.max_loss == pytest.approx(-cost)


def test_bull_call_spread_bounded_profit_and_loss() -> None:
    s = bull_call_spread(100, 10)  # long 90 call, short 110 call
    cost = s.cost(100, 0.5, **MKT)
    summary = risk_summary(s, cost, GRID)
    assert summary.max_profit == pytest.approx(20 - cost)
    assert summary.max_loss == pytest.approx(-cost)
    assert 0 < cost < 20


def test_covered_call_equals_short_put_plus_bond_by_parity() -> None:
    """S - C(K) = K e^{-rT} - P(K): a covered call is a synthetic short put plus cash."""
    T = 0.75
    cost = covered_call(105).cost(100, T, **MKT)
    put = black_scholes_price(100, 105, T, MKT["r"], MKT["sigma"], 0.0, "put")
    assert cost == pytest.approx(105 * np.exp(-MKT["r"] * T) - put)


def test_covered_call_max_profit_and_bounded_downside() -> None:
    s = covered_call(110)
    cost = s.cost(100, 0.5, **MKT)
    summary = risk_summary(s, cost, GRID)
    assert summary.max_profit == pytest.approx(110 - cost)
    assert summary.max_loss == pytest.approx(-cost)  # asset goes to zero


def test_value_before_expiry_converges_to_payoff() -> None:
    s = strangle(100, 10)
    np.testing.assert_allclose(s.value(GRID, 1e-14, **MKT), s.payoff(GRID), atol=1e-6)


def test_pnl_today_is_zero_at_entry_spot() -> None:
    s = straddle(100)
    cost = s.cost(100, 0.5, **MKT)
    assert float(s.pnl_before_expiry(np.array(100.0), 0.5, MKT["r"], MKT["sigma"], cost)) == pytest.approx(0.0)


def test_position_greeks_sum_legs() -> None:
    s = straddle(100)
    g = s.greeks(100, 0.5, **MKT)
    c = black_scholes_greeks(100, 100, 0.5, MKT["r"], MKT["sigma"], 0.0, "call")
    p = black_scholes_greeks(100, 100, 0.5, MKT["r"], MKT["sigma"], 0.0, "put")
    assert g.delta == pytest.approx(c.delta + p.delta)
    assert g.gamma == pytest.approx(2 * c.gamma)


def test_short_call_has_unbounded_loss() -> None:
    s = Strategy("Naked call", (Leg("call", -1, 100),))
    summary = risk_summary(s, s.cost(100, 0.5, **MKT), GRID)
    assert summary.max_loss is None and summary.max_profit is not None


def test_all_presets_build_and_price() -> None:
    for name, build in PRESETS.items():
        s = build(100, 10)
        assert s.legs, name
        assert np.isfinite(s.cost(100, 0.5, **MKT)), name


def test_from_legs_drops_zero_quantities() -> None:
    s = from_legs("custom", [Leg("call", 1, 100), Leg("put", 0, 90)])
    assert len(s.legs) == 1
