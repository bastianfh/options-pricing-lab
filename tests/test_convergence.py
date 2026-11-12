"""Empirical convergence orders match theory: binomial ~1, Crank-Nicolson ~2, Monte Carlo SE ~1/2."""

import numpy as np
import pytest

from pricing.convergence import (
    binomial_study,
    empirical_order,
    monte_carlo_study,
    pde_study,
    standard_error_order,
)
from pricing.engine import OptionSpec

SPEC = OptionSpec(S=100.0, K=105.0, T=1.0, r=0.05, sigma=0.2, q=0.01, option_type="call")


def test_empirical_order_of_exact_power_law() -> None:
    n = np.array([10, 20, 40, 80])
    assert empirical_order(n, 3.0 / n**2) == pytest.approx(2.0)


def test_binomial_is_first_order() -> None:
    """Off-the-money, CRR error oscillates with N, so fit on a dense sweep and check N*|error| stays bounded."""
    steps = np.unique(np.geomspace(50, 1600, 40).astype(int))
    study = binomial_study(SPEC, steps)
    assert 0.85 < study.order < 1.3
    assert np.max(steps * np.abs(study.errors)) < 3.0
    assert abs(study.errors[-1]) < 2e-3


def test_binomial_at_the_money_is_clean_first_order() -> None:
    study = binomial_study(SPEC.with_(K=100.0), [50, 100, 200, 400, 800, 1600])
    assert study.order == pytest.approx(1.0, abs=0.05)


def test_crank_nicolson_is_second_order() -> None:
    study = pde_study(SPEC, [25, 50, 100, 200, 400])
    assert 1.8 < study.order < 2.2
    assert abs(study.errors[-1]) < 1e-4


def test_monte_carlo_standard_error_is_half_order_and_variance_reduction_helps() -> None:
    mc = monte_carlo_study(SPEC, [1_000, 10_000, 100_000])
    for name, study in mc.studies.items():
        assert 0.4 < standard_error_order(study) < 0.6, name
        # Each estimate within 4 standard errors of Black-Scholes.
        assert np.all(np.abs(study.errors) < 4 * study.std_errors), name
    assert np.all(mc.variance_reduction_factor("antithetic_control_variate") > 5)
