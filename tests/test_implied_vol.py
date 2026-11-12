"""Implied volatility solver and surface."""

import numpy as np
import pytest

from pricing.models.black_scholes import black_scholes_price
from pricing.implied_vol import (
    SmileParameters,
    implied_vol_surface,
    implied_volatility,
    implied_volatility_solve,
    price_bounds,
    synthetic_surface,
    synthetic_vol,
)


@pytest.mark.parametrize("option_type", ["call", "put"])
@pytest.mark.parametrize("K", [60.0, 85.0, 100.0, 115.0, 150.0])
@pytest.mark.parametrize("T", [0.02, 0.25, 1.0, 5.0])
@pytest.mark.parametrize("sigma", [0.05, 0.2, 0.6, 1.5])
def test_round_trip_price_to_vol_to_price(option_type: str, K: float, T: float, sigma: float) -> None:
    S, r, q = 100.0, 0.03, 0.01
    price = black_scholes_price(S, K, T, r, sigma, q, option_type)
    lower, _ = price_bounds(S, K, T, r, q, option_type)
    if price - lower < 1e-9:
        pytest.skip("No time value left: volatility is not identifiable at double precision.")
    iv = implied_volatility(price, S, K, T, r, q, option_type)
    assert black_scholes_price(S, K, T, r, iv, q, option_type) == pytest.approx(price, abs=1e-8)
    if price - lower > 1e-4:  # enough time value for sigma itself to be well determined
        assert iv == pytest.approx(sigma, rel=1e-5)


def test_newton_converges_quickly_near_the_money() -> None:
    price = black_scholes_price(100, 100, 1.0, 0.05, 0.25)
    res = implied_volatility_solve(price, 100, 100, 1.0, 0.05)
    assert res.converged and res.bisection_steps == 0 and res.iterations <= 6


def test_bisection_fallback_rescues_bad_initial_guess() -> None:
    """Start far from the root on a deep OTM option where a raw Newton step overshoots."""
    price = black_scholes_price(100, 160, 0.25, 0.05, 0.3)
    res = implied_volatility_solve(price, 100, 160, 0.25, 0.05, initial_guess=0.011)
    assert res.converged and res.bisection_steps > 0
    assert res.sigma == pytest.approx(0.3, rel=1e-6)


def test_garman_kohlhagen_fx_round_trip() -> None:
    S, K, T, r_d, r_f, sigma = 1.085, 1.10, 0.5, 0.043, 0.025, 0.075
    price = black_scholes_price(S, K, T, r_d, sigma, q=r_f, option_type="call")
    assert implied_volatility(price, S, K, T, r_d, r_f, "call") == pytest.approx(sigma, rel=1e-8)


@pytest.mark.parametrize("bad_price", [-1.0, 0.0, 200.0])
def test_prices_outside_bounds_raise(bad_price: float) -> None:
    with pytest.raises(ValueError):
        implied_volatility(bad_price, 100, 100, 1.0, 0.05)


def test_zero_expiry_raises() -> None:
    with pytest.raises(ValueError):
        implied_volatility(5.0, 100, 100, 0.0, 0.05)


def test_synthetic_surface_recovers_input_vols() -> None:
    S, r, q = 100.0, 0.04, 0.01
    params = SmileParameters(atm_vol=0.22, skew=-0.12, curvature=0.05, term_slope=0.02)
    surface = synthetic_surface(S, r, q, params)
    truth = synthetic_vol(surface.strikes, surface.expiries, S, r, q, params)
    assert surface.vols.shape == (len(surface.expiries), len(surface.strikes))
    assert np.all(np.isfinite(surface.vols))
    # Where the option has meaningful value, recovery is essentially exact ...
    priced = surface.prices > 1e-8
    np.testing.assert_allclose(surface.vols[priced], truth[priced], rtol=1e-7)
    # ... and even ~1e-10 prices (limited by floating-point cancellation) stay within 1e-4.
    assert np.max(np.abs(surface.vols - truth)) < 1e-4


def test_surface_marks_arbitrage_violations_as_nan() -> None:
    prices = np.array([[5.0, -1.0]])
    surface = implied_vol_surface(prices, [100.0, 110.0], [1.0], 100.0, 0.05, option_types="call")
    assert np.isfinite(surface.vols[0, 0]) and np.isnan(surface.vols[0, 1])


def test_otm_selection_uses_puts_below_forward() -> None:
    surface = synthetic_surface(100.0, 0.0, 0.0, strikes=[90.0, 110.0], expiries=[0.5])
    assert list(surface.option_types[0]) == ["put", "call"]
