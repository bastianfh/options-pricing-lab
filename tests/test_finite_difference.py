"""Crank-Nicolson finite-difference solver."""

import math

import numpy as np
import pytest
from scipy.stats import norm

from pricing.models.binomial import binomial_price
from pricing.models.black_scholes import black_scholes_price
from pricing.models.finite_difference import finite_difference_price, finite_difference_solve

BASE = dict(S=100.0, T=1.0, r=0.05, sigma=0.2, q=0.01)


@pytest.mark.parametrize("option_type", ["call", "put"])
@pytest.mark.parametrize("K", [80.0, 100.0, 120.0])
def test_converges_to_black_scholes(option_type: str, K: float) -> None:
    bs = black_scholes_price(**BASE, K=K, option_type=option_type)
    assert finite_difference_price(**BASE, K=K, option_type=option_type) == pytest.approx(bs, abs=1e-3)


@pytest.mark.parametrize("K", [80.0, 100.0, 120.0])
def test_second_order_convergence(K: float) -> None:
    """Doubling M and N together should cut the error by about 4 (empirical order ~2)."""
    bs = black_scholes_price(**BASE, K=K)
    grids = [50, 100, 200, 400]
    errors = [abs(finite_difference_price(**BASE, K=K, n_space=n, n_time=n) - bs) for n in grids]
    order = -np.polyfit(np.log(grids), np.log(errors), 1)[0]
    assert 1.7 < order < 2.3


def test_grid_greeks_match_black_scholes() -> None:
    S, K, T, r, sigma, q = 100.0, 105.0, 0.75, 0.04, 0.25, 0.0
    res = finite_difference_solve(S, K, T, r, sigma, q, "call", n_space=800, n_time=400)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    assert res.delta == pytest.approx(norm.cdf(d1), abs=1e-4)
    assert res.gamma == pytest.approx(norm.pdf(d1) / (S * sigma * math.sqrt(T)), abs=1e-4)


def test_grid_is_centred_on_spot() -> None:
    res = finite_difference_solve(**BASE, K=100.0, n_space=101)
    assert res.n_space == 102  # rounded up to even
    assert res.spots[res.n_space // 2] == pytest.approx(BASE["S"])


class TestAmerican:
    @pytest.mark.parametrize("S", [80.0, 100.0, 120.0])
    def test_american_put_agrees_with_binomial(self, S: float) -> None:
        pde = finite_difference_price(S, 100.0, 1.0, 0.05, 0.2, 0.0, "put", "american", n_space=800, n_time=800)
        tree = binomial_price(S, 100.0, 1.0, 0.05, 0.2, 0.0, "put", "american", n_steps=4000)
        assert pde == pytest.approx(tree, abs=5e-3)

    def test_american_put_at_least_european_and_intrinsic(self) -> None:
        res = finite_difference_solve(100.0, 100.0, 1.0, 0.05, 0.2, 0.0, "put", "american")
        euro = finite_difference_solve(100.0, 100.0, 1.0, 0.05, 0.2, 0.0, "put", "european")
        assert np.all(res.values >= euro.values - 1e-10)
        assert np.all(res.values >= np.maximum(100.0 - res.spots, 0.0) - 1e-12)


def test_pure_crank_nicolson_still_converges_for_price() -> None:
    bs = black_scholes_price(**BASE, K=100.0)
    res = finite_difference_solve(**BASE, K=100.0, rannacher_steps=0)
    assert res.price == pytest.approx(bs, abs=1e-3)


def test_zero_time_returns_payoff() -> None:
    assert finite_difference_price(110.0, 100.0, 0.0, 0.05, 0.2) == pytest.approx(10.0)
