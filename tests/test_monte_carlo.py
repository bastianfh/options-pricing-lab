"""Monte Carlo pricer: accuracy, error estimates and variance reduction."""

import numpy as np
import pytest

from pricing.models.black_scholes import black_scholes_price
from pricing.models.monte_carlo import monte_carlo_price, simulate_gbm_paths

BASE = dict(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.2, q=0.01)
VARIANTS = [(False, False), (True, False), (False, True), (True, True)]


@pytest.mark.parametrize("option_type", ["call", "put"])
@pytest.mark.parametrize("antithetic,control", VARIANTS)
def test_within_four_standard_errors_of_black_scholes(option_type: str, antithetic: bool, control: bool) -> None:
    bs = black_scholes_price(**BASE, option_type=option_type)
    res = monte_carlo_price(
        **BASE, option_type=option_type, n_paths=200_000, antithetic=antithetic, control_variate=control, seed=1
    )
    assert abs(res.price - bs) < 4 * res.std_error
    assert res.ci_low < res.price < res.ci_high


def test_confidence_interval_coverage_is_close_to_nominal() -> None:
    """Across 400 independent runs, the 95% interval should contain the true price ~95% of the time."""
    bs = black_scholes_price(**BASE)
    hits = 0
    for seed in range(400):
        res = monte_carlo_price(**BASE, n_paths=2_000, antithetic=False, control_variate=False, seed=seed)
        hits += res.ci_low <= bs <= res.ci_high
    assert 0.92 <= hits / 400 <= 0.98


def test_standard_error_scales_like_inverse_square_root_of_paths() -> None:
    small = monte_carlo_price(**BASE, n_paths=10_000, antithetic=False, control_variate=False, seed=3)
    large = monte_carlo_price(**BASE, n_paths=1_000_000, antithetic=False, control_variate=False, seed=3)
    assert small.std_error / large.std_error == pytest.approx(10.0, rel=0.1)


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_variance_reduction_lowers_standard_error(option_type: str) -> None:
    kwargs = dict(**BASE, option_type=option_type, n_paths=100_000, seed=5)
    plain = monte_carlo_price(**kwargs, antithetic=False, control_variate=False).std_error
    anti = monte_carlo_price(**kwargs, antithetic=True, control_variate=False).std_error
    cv = monte_carlo_price(**kwargs, antithetic=False, control_variate=True).std_error
    both = monte_carlo_price(**kwargs, antithetic=True, control_variate=True).std_error
    assert anti < plain and cv < plain and both < plain
    assert both < 0.5 * plain


def test_fixed_seed_is_reproducible() -> None:
    a = monte_carlo_price(**BASE, n_paths=10_000, seed=11)
    b = monte_carlo_price(**BASE, n_paths=10_000, seed=11)
    assert a == b


def test_antithetic_path_count_is_even() -> None:
    assert monte_carlo_price(**BASE, n_paths=1_001, antithetic=True).n_paths == 1_002


def test_simulated_paths_have_correct_risk_neutral_mean() -> None:
    times, paths = simulate_gbm_paths(100.0, 1.0, 0.05, 0.2, q=0.0, n_paths=200_000, n_steps=4, seed=0)
    assert paths.shape == (200_000, 5) and times[-1] == pytest.approx(1.0)
    assert np.all(paths[:, 0] == 100.0)
    assert paths[:, -1].mean() == pytest.approx(100.0 * np.exp(0.05), rel=3e-3)


def test_invalid_arguments_raise() -> None:
    with pytest.raises(ValueError):
        monte_carlo_price(**BASE, n_paths=1)
    with pytest.raises(ValueError):
        monte_carlo_price(**BASE, confidence=1.5)
