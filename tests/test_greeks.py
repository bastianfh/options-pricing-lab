"""Analytical Black-Scholes Greeks and numerical (bump-and-reprice) Greeks."""

import math

import numpy as np
import pytest

from pricing.engine import Method, NumericalSettings, OptionSpec, greeks
from pricing.greeks import BumpSizes, black_scholes_greeks, black_scholes_pricer, numerical_greeks

CASES = [
    dict(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.2, q=0.0),
    dict(S=90.0, K=100.0, T=0.5, r=0.03, sigma=0.35, q=0.02),
    dict(S=1.10, K=1.12, T=0.25, r=0.045, sigma=0.08, q=0.03),  # EUR/USD-like
]
NAMES = ["delta", "gamma", "vega", "theta", "rho"]


def test_hull_example_19_1_delta() -> None:
    """Hull (11th ed.) Example 19.1 / Section 19.4: S=49, K=50, r=5%, sigma=20%, T=20/52 -> call delta 0.522."""
    g = black_scholes_greeks(49, 50, 20 / 52, 0.05, 0.20, option_type="call")
    assert g.delta == pytest.approx(0.522, abs=1e-3)
    assert g.gamma == pytest.approx(0.066, abs=1e-3)
    assert g.vega == pytest.approx(12.1, abs=0.05)
    assert g.theta == pytest.approx(-4.31, abs=0.01)
    assert g.rho == pytest.approx(8.91, abs=0.01)


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("option_type", ["call", "put"])
def test_bump_and_reprice_matches_analytical_on_black_scholes(case: dict, option_type: str) -> None:
    analytical = black_scholes_greeks(**case, option_type=option_type).as_dict()
    numerical = numerical_greeks(black_scholes_pricer(option_type), **case).as_dict()
    for name in NAMES:
        scale = max(abs(analytical[name]), 1e-2)
        assert numerical[name] == pytest.approx(analytical[name], abs=2e-3 * scale + 1e-6), name


@pytest.mark.parametrize("case", CASES)
def test_put_call_relationships(case: dict) -> None:
    """Parity implies: delta_c - delta_p = e^{-qT}; gammas and vegas are equal."""
    c = black_scholes_greeks(**case, option_type="call")
    p = black_scholes_greeks(**case, option_type="put")
    assert c.delta - p.delta == pytest.approx(math.exp(-case["q"] * case["T"]))
    assert c.gamma == pytest.approx(p.gamma)
    assert c.vega == pytest.approx(p.vega)
    assert c.rho - p.rho == pytest.approx(case["K"] * case["T"] * math.exp(-case["r"] * case["T"]))


def test_black_scholes_pde_identity() -> None:
    """Theta + (r-q) S Delta + 0.5 sigma^2 S^2 Gamma = r V (the PDE itself)."""
    from pricing.models.black_scholes import black_scholes_price

    S, K, T, r, sigma, q = 105.0, 100.0, 0.8, 0.04, 0.3, 0.015
    g = black_scholes_greeks(S, K, T, r, sigma, q, "call")
    v = black_scholes_price(S, K, T, r, sigma, q, "call")
    lhs = g.theta + (r - q) * S * g.delta + 0.5 * sigma**2 * S**2 * g.gamma
    assert lhs == pytest.approx(r * v, abs=1e-10)


def test_vectorised_greeks() -> None:
    g = black_scholes_greeks(np.array([80.0, 100.0, 120.0]), 100.0, 1.0, 0.05, 0.2)
    assert g.delta.shape == (3,)
    assert np.all(np.diff(g.delta) > 0)


def test_analytical_greeks_reject_zero_time() -> None:
    with pytest.raises(ValueError):
        black_scholes_greeks(100, 100, 0.0, 0.05, 0.2)


@pytest.mark.parametrize("method", [Method.BINOMIAL, Method.MONTE_CARLO, Method.FINITE_DIFFERENCE])
@pytest.mark.parametrize("option_type", ["call", "put"])
def test_numerical_methods_greeks_match_black_scholes(method: Method, option_type: str) -> None:
    """Bump-and-reprice Greeks from each numerical model are close to the closed form."""
    spec = OptionSpec(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.2, q=0.01, option_type=option_type)
    settings = NumericalSettings(binomial_steps=1000, mc_paths=400_000, pde_space_steps=400, pde_time_steps=200)
    exact = greeks(spec, Method.BLACK_SCHOLES).as_dict()
    approx = greeks(spec, method, settings).as_dict()
    # Absolute tolerances in raw units; Monte Carlo gamma is the noisiest.
    tol = dict(delta=5e-3, gamma=2e-3 if method is Method.MONTE_CARLO else 5e-4, vega=0.15, theta=0.05, rho=0.15)
    for name in NAMES:
        assert approx[name] == pytest.approx(exact[name], abs=tol[name]), f"{method.value} {name}"


def test_custom_bump_sizes() -> None:
    g = numerical_greeks(black_scholes_pricer("call"), 100, 100, 1, 0.05, 0.2, bumps=BumpSizes(spot=0.001))
    exact = black_scholes_greeks(100, 100, 1, 0.05, 0.2)
    assert g.delta == pytest.approx(exact.delta, abs=1e-6)
