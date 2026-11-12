"""Convergence studies: how fast each numerical method approaches the Black-Scholes price.

For a method with error :math:`\\varepsilon(n) \\approx C n^{-p}`, the slope of
:math:`\\log\\varepsilon` against :math:`\\log n` is :math:`-p`, the empirical
order of convergence. Theory predicts:

==================  =====================  ======================
Method              resolution ``n``       expected order ``p``
==================  =====================  ======================
CRR binomial        time steps             1   (error ~ 1/N)
Crank-Nicolson      grid points per axis   2   (error ~ 1/M^2)
Monte Carlo         simulated paths        1/2 (std. error ~ 1/sqrt(n))
==================  =====================  ======================

These functions run the studies and return plain NumPy arrays so the results
can be tested, plotted, or tabulated.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from pricing.engine import OptionSpec
from pricing.models.binomial import binomial_price
from pricing.models.black_scholes import black_scholes_price
from pricing.models.finite_difference import finite_difference_price
from pricing.models.monte_carlo import monte_carlo_price


def empirical_order(resolution: Sequence[float], errors: Sequence[float]) -> float:
    """Least-squares slope ``p`` of ``log(error) = c - p log(n)``, ignoring zero errors."""
    n, e = np.asarray(resolution, dtype=float), np.abs(np.asarray(errors, dtype=float))
    mask = e > 0
    if mask.sum() < 2:
        return float("nan")
    return float(-np.polyfit(np.log(n[mask]), np.log(e[mask]), 1)[0])


@dataclass(frozen=True)
class ConvergenceStudy:
    """Prices of one method at increasing resolution, compared with a reference price."""

    method: str
    resolution: np.ndarray
    prices: np.ndarray
    reference: float
    runtime_ms: np.ndarray
    std_errors: Optional[np.ndarray] = None

    @property
    def errors(self) -> np.ndarray:
        """Signed error ``price - reference``."""
        return self.prices - self.reference

    @property
    def order(self) -> float:
        """Empirical order of convergence of the absolute error."""
        return empirical_order(self.resolution, self.errors)


def _european(spec: OptionSpec) -> float:
    return float(black_scholes_price(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type))


def binomial_study(spec: OptionSpec, steps: Sequence[int]) -> ConvergenceStudy:
    """Run the CRR tree at each number of steps (European exercise, reference = Black-Scholes)."""
    prices, times = [], []
    for n in steps:
        t0 = time.perf_counter()
        prices.append(binomial_price(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type, "european", int(n)))
        times.append((time.perf_counter() - t0) * 1e3)
    return ConvergenceStudy("binomial", np.asarray(steps), np.asarray(prices), _european(spec), np.asarray(times))


def pde_study(spec: OptionSpec, grid_sizes: Sequence[int]) -> ConvergenceStudy:
    """Run Crank-Nicolson with ``M = N = n`` for each ``n`` (reference = Black-Scholes)."""
    prices, times = [], []
    for n in grid_sizes:
        t0 = time.perf_counter()
        prices.append(
            finite_difference_price(
                spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type, "european", int(n), int(n)
            )
        )
        times.append((time.perf_counter() - t0) * 1e3)
    return ConvergenceStudy("finite_difference", np.asarray(grid_sizes), np.asarray(prices), _european(spec), np.asarray(times))


@dataclass(frozen=True)
class MonteCarloStudy:
    """Monte Carlo convergence for each variance-reduction variant, keyed by variant name."""

    studies: dict[str, ConvergenceStudy] = field(default_factory=dict)

    def variance_reduction_factor(self, variant: str, baseline: str = "plain") -> np.ndarray:
        """``(SE_baseline / SE_variant)^2``: how many times more plain paths you'd need for the same accuracy."""
        base, var = self.studies[baseline].std_errors, self.studies[variant].std_errors
        return (base / var) ** 2


MC_VARIANTS: dict[str, tuple[bool, bool]] = {
    "plain": (False, False),
    "antithetic": (True, False),
    "control_variate": (False, True),
    "antithetic_control_variate": (True, True),
}
"""Variant name -> (antithetic, control_variate)."""


def monte_carlo_study(spec: OptionSpec, path_counts: Sequence[int], seed: int = 2024) -> MonteCarloStudy:
    """Run Monte Carlo at each path count for every variance-reduction variant.

    Every run at a given path count uses the same seed, so the variants differ
    only in the estimator, not in luck.
    """
    reference = _european(spec)
    studies: dict[str, ConvergenceStudy] = {}
    for name, (anti, cv) in MC_VARIANTS.items():
        prices, ses, times = [], [], []
        for n in path_counts:
            t0 = time.perf_counter()
            res = monte_carlo_price(
                spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type,
                n_paths=int(n), antithetic=anti, control_variate=cv, seed=seed,
            )
            times.append((time.perf_counter() - t0) * 1e3)
            prices.append(res.price)
            ses.append(res.std_error)
        studies[name] = ConvergenceStudy(
            name, np.asarray(path_counts), np.asarray(prices), reference, np.asarray(times), np.asarray(ses)
        )
    return MonteCarloStudy(studies)


def standard_error_order(study: ConvergenceStudy) -> float:
    """Empirical order of the Monte Carlo standard error (theory: 0.5)."""
    if study.std_errors is None:
        raise ValueError("Study has no standard errors.")
    return empirical_order(study.resolution, study.std_errors)
