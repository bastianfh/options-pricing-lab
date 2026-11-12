"""Black-Scholes-Merton and Garman-Kohlhagen against published textbook values."""

import numpy as np
import pytest

from pricing.models.black_scholes import (
    black_scholes_price,
    garman_kohlhagen_price,
    put_call_parity_gap,
)


class TestTextbookValues:
    def test_hull_example_15_6(self) -> None:
        """Hull (11th ed.) Example 15.6: S=42, K=40, r=10%, sigma=20%, T=0.5 -> c=4.76, p=0.81."""
        call = black_scholes_price(42, 40, 0.5, 0.10, 0.20, option_type="call")
        put = black_scholes_price(42, 40, 0.5, 0.10, 0.20, option_type="put")
        assert call == pytest.approx(4.7594, abs=1e-4)
        assert put == pytest.approx(0.8086, abs=1e-4)

    def test_haug_merton_dividend_yield(self) -> None:
        """Haug (2007), sec. 1.1.4: index put, S=100, K=95, T=0.5, r=10%, q=5%, sigma=20% -> 2.4648."""
        put = black_scholes_price(100, 95, 0.5, 0.10, 0.20, q=0.05, option_type="put")
        assert put == pytest.approx(2.4648, abs=1e-4)

    def test_haug_garman_kohlhagen(self) -> None:
        """Haug (2007), sec. 1.1.6: FX call, S=1.56, K=1.60, T=0.5, r_d=6%, r_f=8%, sigma=12% -> 0.0291."""
        call = garman_kohlhagen_price(1.56, 1.60, 0.5, 0.06, 0.08, 0.12, option_type="call")
        assert call == pytest.approx(0.0291, abs=1e-4)

    def test_garman_kohlhagen_equals_bsm_with_foreign_rate_as_yield(self) -> None:
        gk = garman_kohlhagen_price(1.10, 1.12, 0.25, 0.045, 0.03, 0.08, "call")
        bsm = black_scholes_price(1.10, 1.12, 0.25, 0.045, 0.08, q=0.03, option_type="call")
        assert gk == pytest.approx(bsm, rel=1e-14)


class TestNoArbitrageProperties:
    @pytest.mark.parametrize("S", [60.0, 90.0, 100.0, 110.0, 150.0])
    @pytest.mark.parametrize("T", [0.05, 0.5, 2.0])
    @pytest.mark.parametrize("q", [0.0, 0.03])
    def test_put_call_parity(self, S: float, T: float, q: float) -> None:
        K, r, sigma = 100.0, 0.05, 0.25
        call = black_scholes_price(S, K, T, r, sigma, q, "call")
        put = black_scholes_price(S, K, T, r, sigma, q, "put")
        assert put_call_parity_gap(call, put, S, K, T, r, q) == pytest.approx(0.0, abs=1e-10)

    def test_price_bounds(self) -> None:
        S, K, T, r, q = 100.0, 100.0, 1.0, 0.05, 0.02
        for sigma in [0.01, 0.2, 1.0, 3.0]:
            call = black_scholes_price(S, K, T, r, sigma, q, "call")
            assert max(S * np.exp(-q * T) - K * np.exp(-r * T), 0) <= call <= S * np.exp(-q * T)

    def test_call_increasing_in_volatility(self) -> None:
        prices = black_scholes_price(100, 100, 1.0, 0.05, np.linspace(0.05, 1.0, 20))
        assert np.all(np.diff(prices) > 0)


class TestLimitsAndVectorisation:
    def test_zero_time_is_intrinsic(self) -> None:
        assert black_scholes_price(110, 100, 0.0, 0.05, 0.2, option_type="call") == pytest.approx(10.0)
        assert black_scholes_price(110, 100, 0.0, 0.05, 0.2, option_type="put") == pytest.approx(0.0)

    def test_zero_vol_is_discounted_forward_intrinsic(self) -> None:
        S, K, T, r = 100.0, 100.0, 1.0, 0.05
        expected = S - K * np.exp(-r * T)
        assert black_scholes_price(S, K, T, r, 0.0) == pytest.approx(expected)

    def test_vectorised_matches_scalar(self) -> None:
        spots = np.array([80.0, 100.0, 120.0])
        vec = black_scholes_price(spots, 100, 1.0, 0.05, 0.2)
        scalar = [black_scholes_price(s, 100, 1.0, 0.05, 0.2) for s in spots]
        np.testing.assert_allclose(vec, scalar, rtol=1e-14)

    def test_scalar_input_returns_float(self) -> None:
        assert isinstance(black_scholes_price(100, 100, 1.0, 0.05, 0.2), float)

    @pytest.mark.parametrize("bad", [dict(S=-1.0), dict(K=0.0), dict(T=-0.1), dict(sigma=-0.2)])
    def test_invalid_inputs_raise(self, bad: dict) -> None:
        args = dict(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.2) | bad
        with pytest.raises(ValueError):
            black_scholes_price(**args)

    def test_bad_option_type_raises(self) -> None:
        with pytest.raises(ValueError):
            black_scholes_price(100, 100, 1, 0.05, 0.2, option_type="straddle")
