"""Cox-Ross-Rubinstein binomial tree."""

import numpy as np
import pytest

from pricing.models.binomial import binomial_price, crr_parameters
from pricing.models.black_scholes import black_scholes_price

BASE = dict(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.2, q=0.0)


class TestEuropeanConvergence:
    @pytest.mark.parametrize("option_type", ["call", "put"])
    @pytest.mark.parametrize("K", [80.0, 100.0, 120.0])
    def test_converges_to_black_scholes(self, option_type: str, K: float) -> None:
        params = BASE | dict(K=K)
        bs = black_scholes_price(**params, option_type=option_type)
        tree = binomial_price(**params, option_type=option_type, n_steps=2000)
        assert tree == pytest.approx(bs, abs=2e-3)

    def test_error_shrinks_roughly_like_one_over_n(self) -> None:
        bs = black_scholes_price(**BASE)
        # Even N only, to look past the odd/even oscillation.
        errors = [abs(binomial_price(**BASE, n_steps=n) - bs) for n in (50, 200, 800)]
        assert errors[0] > errors[1] > errors[2]
        assert errors[2] < errors[0] / 8  # 16x more steps -> at least 8x smaller error

    def test_with_dividend_yield(self) -> None:
        params = BASE | dict(q=0.03)
        bs = black_scholes_price(**params, option_type="put")
        assert binomial_price(**params, option_type="put", n_steps=2000) == pytest.approx(bs, abs=2e-3)


class TestAmerican:
    def test_hull_example_21_1_five_step_tree(self) -> None:
        """Hull (11th ed.) Fig. 21.3: American put, S=K=50, r=10%, sigma=40%, T=5/12, N=5 -> 4.49."""
        value = binomial_price(50, 50, 5 / 12, 0.10, 0.40, option_type="put", exercise="american", n_steps=5)
        assert value == pytest.approx(4.49, abs=5e-3)

    @pytest.mark.parametrize("S", [70.0, 90.0, 100.0, 110.0, 130.0])
    def test_american_put_at_least_european_put(self, S: float) -> None:
        params = BASE | dict(S=S)
        euro = binomial_price(**params, option_type="put", exercise="european", n_steps=400)
        amer = binomial_price(**params, option_type="put", exercise="american", n_steps=400)
        assert amer >= euro - 1e-12
        assert amer >= max(params["K"] - S, 0.0) - 1e-12

    def test_american_put_has_strictly_positive_premium_when_rates_positive(self) -> None:
        euro = binomial_price(**BASE | dict(S=90.0), option_type="put", n_steps=400)
        amer = binomial_price(**BASE | dict(S=90.0), option_type="put", exercise="american", n_steps=400)
        assert amer - euro > 0.1

    def test_american_call_without_dividends_equals_european(self) -> None:
        """Merton (1973): never optimal to exercise a call early on a non-dividend-paying asset."""
        euro = binomial_price(**BASE, option_type="call", n_steps=400)
        amer = binomial_price(**BASE, option_type="call", exercise="american", n_steps=400)
        assert amer == pytest.approx(euro, abs=1e-10)

    def test_american_call_with_dividends_worth_more(self) -> None:
        params = BASE | dict(S=120.0, q=0.08)
        euro = binomial_price(**params, option_type="call", n_steps=400)
        amer = binomial_price(**params, option_type="call", exercise="american", n_steps=400)
        assert amer > euro


class TestEdgeCases:
    def test_risk_neutral_probability_in_unit_interval(self) -> None:
        u, d, p = crr_parameters(1.0, 0.05, 0.2, 100)
        assert d < 1 < u and 0 < p < 1
        assert u * d == pytest.approx(1.0)

    def test_too_few_steps_for_carry_raises(self) -> None:
        with pytest.raises(ValueError):
            crr_parameters(T=10.0, r=0.5, sigma=0.05, n_steps=1)

    def test_zero_time_returns_intrinsic(self) -> None:
        assert binomial_price(**BASE | dict(S=110.0, T=0.0)) == pytest.approx(10.0)

    def test_single_step_closed_form(self) -> None:
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
        u, d, p = crr_parameters(T, r, sigma, 1)
        expected = np.exp(-r * T) * p * (S * u - K)
        assert binomial_price(S, K, T, r, sigma, n_steps=1) == pytest.approx(expected)


def test_tree_greeks_match_black_scholes() -> None:
    from pricing.greeks import black_scholes_greeks
    from pricing.models.binomial import binomial_tree_greeks

    price, delta, gamma, theta = binomial_tree_greeks(100, 100, 1.0, 0.05, 0.2, 0.01, "put", n_steps=1000)
    exact = black_scholes_greeks(100, 100, 1.0, 0.05, 0.2, 0.01, "put")
    assert delta == pytest.approx(exact.delta, abs=1e-3)
    assert gamma == pytest.approx(exact.gamma, abs=1e-4)
    assert theta == pytest.approx(exact.theta, abs=0.02)
    assert price == pytest.approx(binomial_price(100, 100, 1.0, 0.05, 0.2, 0.01, "put", n_steps=1000))


def test_returns_python_float() -> None:
    assert type(binomial_price(**BASE, n_steps=10)) is float
