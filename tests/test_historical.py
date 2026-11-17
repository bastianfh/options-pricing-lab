"""Historical price statistics."""

import math

import numpy as np
import pytest

from pricing.historical import (
    annualized_return,
    historical_volatility,
    log_returns,
    max_drawdown,
    rolling_volatility,
    sharpe_ratio,
    summarize,
    trailing_dividend_yield,
)


def gbm_path(sigma: float, mu: float = 0.05, n: int = 252 * 20, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dt = 1 / 252
    r = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * rng.standard_normal(n)
    return 100 * np.exp(np.concatenate([[0.0], np.cumsum(r)]))


@pytest.mark.parametrize("sigma", [0.1, 0.25, 0.6])
def test_historical_volatility_recovers_the_simulated_sigma(sigma: float) -> None:
    # 20 years of daily data: the estimator's standard error is about sigma / sqrt(2n) ~ 1%.
    assert historical_volatility(gbm_path(sigma)) == pytest.approx(sigma, rel=0.03)


def test_log_returns_and_window() -> None:
    prices = np.array([100.0, 110.0, 99.0])
    np.testing.assert_allclose(log_returns(prices), [math.log(1.1), math.log(0.9)])
    with pytest.raises(ValueError):
        historical_volatility(prices, window=1)


def test_rolling_volatility_matches_direct_computation() -> None:
    prices = gbm_path(0.3, n=600, seed=3)
    roll = rolling_volatility(prices, 63)
    assert roll.shape == prices.shape and np.isnan(roll[:63]).all()
    for i in (63, 200, 600):
        direct = historical_volatility(prices[: i + 1], window=63)
        assert roll[i] == pytest.approx(direct, rel=1e-9)


def test_annualized_return_of_exact_growth() -> None:
    prices = 100 * 1.1 ** (np.arange(253) / 252)  # exactly 10% a year
    assert annualized_return(prices) == pytest.approx(0.10, rel=1e-9)


def test_max_drawdown_known_series() -> None:
    assert max_drawdown([100, 120, 90, 130, 104]) == pytest.approx(0.25)  # 120 -> 90
    assert max_drawdown([1, 2, 3, 4]) == 0.0


def test_sharpe_sign_and_scale() -> None:
    up = gbm_path(0.2, mu=0.30, seed=1)
    flat = gbm_path(0.2, mu=0.0, seed=1)
    assert sharpe_ratio(up) > 1.0 > sharpe_ratio(flat)
    assert sharpe_ratio(up, risk_free=0.05) < sharpe_ratio(up)


def test_trailing_dividend_yield_uses_last_year_only() -> None:
    # Four quarterly 0.25 payments in the last year, one older payment that must be ignored.
    q = trailing_dividend_yield([0.25, 0.25, 0.25, 0.25, 0.25], [10, 100, 190, 280, 400], last_price=50.0)
    assert q == pytest.approx(1.0 / 50.0)
    assert trailing_dividend_yield([], [], 50.0) == 0.0


def test_summary_of_normal_returns_has_small_skew_and_kurtosis() -> None:
    s = summarize(gbm_path(0.2, seed=7), risk_free=0.02)
    assert s.n_days == 252 * 20
    assert abs(s.skewness) < 0.15 and abs(s.excess_kurtosis) < 0.3
    assert s.worst_day < 0 < s.best_day and 0 <= s.max_drawdown < 1


@pytest.mark.parametrize("bad", [[100.0], [100.0, -1.0], [100.0, float("nan")], [[1.0, 2.0]]])
def test_invalid_prices_raise(bad: list) -> None:
    with pytest.raises(ValueError):
        log_returns(bad)
