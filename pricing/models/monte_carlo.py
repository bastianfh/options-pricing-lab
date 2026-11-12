"""Monte Carlo pricing of European options under geometric Brownian motion.

Under the risk-neutral measure the terminal asset price is sampled exactly
(no time-discretisation error):

.. math::

    S_T = S_0 \\exp\\left[(r - q - \\tfrac12\\sigma^2)T + \\sigma\\sqrt{T}\\,Z\\right],
    \\qquad Z \\sim N(0, 1)

and the price is the discounted sample mean of the payoff,
:math:`\\hat V = e^{-rT}\\frac1n\\sum_i f(S_T^{(i)})`, with standard error
:math:`s/\\sqrt{n}`.

Variance reduction (Glasserman, *Monte Carlo Methods in Financial
Engineering*, 2003, sec. 4.1-4.2):

* **Antithetic variates**: each draw ``Z`` is paired with ``-Z`` and the two
  payoffs are averaged. The pair averages are i.i.d., so the standard error is
  computed from them, not from the individual paths.
* **Control variate**: the discounted terminal price
  :math:`X = e^{-rT} S_T` has known mean :math:`E[X] = S_0 e^{-qT}`. The
  estimator :math:`Y - \\hat\\beta (X - E[X])` with
  :math:`\\hat\\beta = \\widehat{\\mathrm{Cov}}(Y, X) / \\widehat{\\mathrm{Var}}(X)`
  has variance :math:`(1 - \\rho_{XY}^2)\\,\\mathrm{Var}(Y)`.

Estimating :math:`\\beta` from the same sample adds a bias of order
:math:`1/n`, negligible next to the :math:`1/\\sqrt n` standard error.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
from scipy.stats import norm

from pricing.utils import OptionType, payoff, to_option_type, validate_inputs


@dataclass(frozen=True)
class MonteCarloResult:
    """Outcome of a Monte Carlo pricing run.

    Attributes
    ----------
    price
        Point estimate of the option value.
    std_error
        Standard error of the estimate.
    ci_low, ci_high
        Two-sided confidence interval ``price -/+ z * std_error``.
    confidence
        Confidence level of the interval (e.g. 0.95).
    n_paths
        Number of simulated terminal prices (an antithetic pair counts as two).
    antithetic, control_variate
        Which variance-reduction techniques were used.
    beta
        Estimated control-variate coefficient (``None`` if not used).
    """

    price: float
    std_error: float
    ci_low: float
    ci_high: float
    confidence: float
    n_paths: int
    antithetic: bool
    control_variate: bool
    beta: Optional[float] = None


def monte_carlo_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
    n_paths: int = 100_000,
    antithetic: bool = True,
    control_variate: bool = True,
    seed: Optional[int] = 42,
    confidence: float = 0.95,
) -> MonteCarloResult:
    """Price a European option by Monte Carlo simulation.

    Parameters
    ----------
    S, K, T, r, sigma, q
        Spot, strike, years to expiry, risk-free rate, volatility, continuous yield.
    option_type
        ``"call"`` or ``"put"``.
    n_paths
        Number of terminal prices to simulate. With antithetic variates this is
        rounded up to an even number.
    antithetic
        Pair each normal draw ``Z`` with ``-Z``.
    control_variate
        Use the discounted terminal price as a control variate.
    seed
        Seed for :func:`numpy.random.default_rng`. A fixed seed gives
        reproducible prices and lets bump-and-reprice Greeks use common random
        numbers. ``None`` draws fresh entropy.
    confidence
        Confidence level for the reported interval.

    Returns
    -------
    MonteCarloResult
    """
    validate_inputs(S, K, T, sigma)
    opt = to_option_type(option_type)
    if n_paths < 2:
        raise ValueError("n_paths must be at least 2.")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1).")

    rng = np.random.default_rng(seed)
    n_samples = math.ceil(n_paths / 2) if antithetic else n_paths
    z = rng.standard_normal(n_samples)

    drift = (r - q - 0.5 * sigma**2) * T
    diffusion = sigma * math.sqrt(T)
    discount = math.exp(-r * T)

    def discounted(z_draws: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        s_t = S * np.exp(drift + diffusion * z_draws)
        return discount * payoff(s_t, K, opt), discount * s_t

    y, x = discounted(z)
    if antithetic:
        y_anti, x_anti = discounted(-z)
        y, x = 0.5 * (y + y_anti), 0.5 * (x + x_anti)

    beta: Optional[float] = None
    if control_variate:
        x_mean_exact = S * math.exp(-q * T)
        var_x = float(np.var(x, ddof=1))
        if var_x > 0.0:
            beta = float(np.cov(y, x, ddof=1)[0, 1] / var_x)
            y = y - beta * (x - x_mean_exact)

    price = float(np.mean(y))
    std_error = float(np.std(y, ddof=1) / math.sqrt(n_samples))
    z_crit = float(norm.ppf(0.5 + confidence / 2.0))
    return MonteCarloResult(
        price=price,
        std_error=std_error,
        ci_low=price - z_crit * std_error,
        ci_high=price + z_crit * std_error,
        confidence=confidence,
        n_paths=n_samples * (2 if antithetic else 1),
        antithetic=antithetic,
        control_variate=control_variate,
        beta=beta,
    )


def simulate_gbm_paths(
    S: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    n_paths: int = 50,
    n_steps: int = 252,
    seed: Optional[int] = 7,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate full risk-neutral GBM paths for visualisation.

    Uses the exact log-normal transition over each step (Glasserman, eq. 3.3).

    Returns
    -------
    times : ndarray, shape (n_steps + 1,)
    paths : ndarray, shape (n_paths, n_steps + 1)
    """
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    increments = (r - q - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * rng.standard_normal((n_paths, n_steps))
    log_paths = np.concatenate([np.zeros((n_paths, 1)), np.cumsum(increments, axis=1)], axis=1)
    return np.linspace(0.0, T, n_steps + 1), S * np.exp(log_paths)
