"""Crank-Nicolson finite-difference solver for the Black-Scholes PDE.

Working in log-spot :math:`x = \\ln S` and time-to-expiry :math:`\\tau = T - t`,
the Black-Scholes PDE has constant coefficients:

.. math::

    \\frac{\\partial V}{\\partial \\tau}
    = \\tfrac12\\sigma^2 \\frac{\\partial^2 V}{\\partial x^2}
    + \\left(r - q - \\tfrac12\\sigma^2\\right)\\frac{\\partial V}{\\partial x} - rV
    \\equiv \\mathcal{L}V,
    \\qquad V(x, 0) = \\text{payoff}(e^x).

Space is discretised with central differences on a uniform grid and time with
the θ-scheme

.. math::

    (I - \\theta\\,\\Delta\\tau\\,L)\\,V^{n+1} = (I + (1-\\theta)\\,\\Delta\\tau\\,L)\\,V^{n},

where θ = 1/2 is Crank-Nicolson (second order in both Δx and Δτ) and θ = 1
is fully implicit. Each step is a tridiagonal solve, done with
:func:`scipy.linalg.solve_banded` in O(M) operations.

Implementation choices
----------------------
* **Grid centred on the spot.** The node at index ``M/2`` is exactly
  :math:`\\ln S_0`, so no interpolation is needed to read off the price.
* **Rannacher start** (Rannacher, 1984; Giles & Carter, 2006). The payoff
  kink makes plain Crank-Nicolson produce spurious oscillations, especially
  in gamma. The first ``rannacher_steps`` time steps are each replaced by two
  fully implicit half-steps, which damps them without losing second-order
  convergence.
* **Payoff smoothing** (Pooley, Vetzal & Forsyth, 2003). The initial value
  at the one node whose cell contains the strike is replaced by the average
  of the payoff over that cell. Without it, the error depends on where the
  strike happens to fall between nodes and convergence looks erratic.
* **Boundaries.** Dirichlet conditions from the asymptotic value of the
  option far in or out of the money. The grid extends ``n_std`` standard
  deviations of :math:`\\ln S_T` either side of the spot (and always covers the
  strike), so the boundary error is negligible.
* **American exercise.** After each step the solution is projected onto the
  early-exercise constraint, :math:`V \\leftarrow \\max(V, \\text{payoff})`.
  This is simple and stable but only first-order in time near the exercise
  boundary; PSOR (Wilmott, Howison & Dewynne, 1995) would restore full order.

References: Crank, J. & Nicolson, P. (1947); Wilmott, *Paul Wilmott on
Quantitative Finance*, 2nd ed., ch. 78; Hull, ch. 21.8.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Union

import numpy as np
from scipy.linalg import solve_banded

from pricing.utils import (
    ExerciseStyle,
    OptionType,
    payoff,
    to_exercise_style,
    to_option_type,
    validate_inputs,
)


@dataclass(frozen=True)
class FiniteDifferenceResult:
    """Price plus grid-based sensitivities from a PDE solve.

    Attributes
    ----------
    price
        Option value at the spot.
    delta, gamma
        Sensitivities read directly from the final grid by central differences.
    spots, values
        The asset-price grid and option values at time 0 (useful for plotting).
    n_space, n_time
        Grid dimensions.
    """

    price: float
    delta: float
    gamma: float
    spots: np.ndarray
    values: np.ndarray
    n_space: int
    n_time: int


def finite_difference_solve(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
    exercise: Union[str, ExerciseStyle] = "european",
    n_space: int = 400,
    n_time: int = 400,
    n_std: float = 6.0,
    rannacher_steps: int = 2,
) -> FiniteDifferenceResult:
    """Solve the Black-Scholes PDE with Crank-Nicolson and return price and grid Greeks.

    Parameters
    ----------
    S, K, T, r, sigma, q
        Spot, strike, years to expiry, risk-free rate, volatility, continuous yield.
    option_type, exercise
        ``"call"``/``"put"`` and ``"european"``/``"american"``.
    n_space
        Number of space intervals ``M`` (rounded up to an even number so the
        spot sits on a node).
    n_time
        Number of time steps ``N``.
    n_std
        Half-width of the grid in standard deviations of ``ln S_T``.
    rannacher_steps
        Number of initial steps replaced by two implicit half-steps (0 gives
        pure Crank-Nicolson).
    """
    validate_inputs(S, K, T, sigma)
    opt = to_option_type(option_type)
    american = to_exercise_style(exercise) is ExerciseStyle.AMERICAN
    if T == 0.0:
        value = float(payoff(S, K, opt))
        return FiniteDifferenceResult(value, float("nan"), float("nan"), np.array([S]), np.array([value]), 0, 0)
    if sigma <= 0.0:
        raise ValueError("The finite-difference solver requires sigma > 0.")
    if n_space < 4 or n_time < 1:
        raise ValueError("Need n_space >= 4 and n_time >= 1.")

    n_space += n_space % 2
    half_width = n_std * sigma * math.sqrt(T) + abs(math.log(K / S))
    x = math.log(S) + np.linspace(-half_width, half_width, n_space + 1)
    dx = x[1] - x[0]
    spots = np.exp(x)
    exercise_value = payoff(spots, K, opt)

    # Interior stencil coefficients of L (constant in log-space).
    a = 0.5 * sigma**2
    b = r - q - 0.5 * sigma**2
    lower = a / dx**2 - b / (2 * dx)
    diag = -2 * a / dx**2 - r
    upper = a / dx**2 + b / (2 * dx)

    def boundaries(tau: float) -> tuple[float, float]:
        disc_k, disc_q = K * math.exp(-r * tau), math.exp(-q * tau)
        if opt is OptionType.CALL:
            lo, hi = 0.0, spots[-1] * disc_q - disc_k
            if american:
                hi = max(hi, spots[-1] - K)
        else:
            lo, hi = disc_k - spots[0] * disc_q, 0.0
            if american:
                lo = max(lo, K - spots[0])
        return lo, hi

    def step(v: np.ndarray, tau_new: float, dtau: float, theta: float) -> np.ndarray:
        """Advance one θ-scheme step from ``tau_new - dtau`` to ``tau_new``."""
        lv = lower * v[:-2] + diag * v[1:-1] + upper * v[2:]
        rhs = v[1:-1] + (1.0 - theta) * dtau * lv
        lo, hi = boundaries(tau_new)
        rhs[0] += theta * dtau * lower * lo
        rhs[-1] += theta * dtau * upper * hi

        m = n_space - 1
        banded = np.empty((3, m))
        banded[0, 1:] = -theta * dtau * upper
        banded[1, :] = 1.0 - theta * dtau * diag
        banded[2, :-1] = -theta * dtau * lower
        banded[0, 0] = banded[2, -1] = 0.0

        new = np.empty_like(v)
        new[1:-1] = solve_banded((1, 1), banded, rhs)
        new[0], new[-1] = lo, hi
        if american:
            np.maximum(new, exercise_value, out=new)
        return new

    dtau = T / n_time
    v = _smoothed_payoff(x, dx, K, opt, exercise_value)
    for n in range(n_time):
        tau = (n + 1) * dtau
        if n < rannacher_steps:
            v = step(v, tau - 0.5 * dtau, 0.5 * dtau, theta=1.0)
            v = step(v, tau, 0.5 * dtau, theta=1.0)
        else:
            v = step(v, tau, dtau, theta=0.5)

    i = n_space // 2
    v_x = (v[i + 1] - v[i - 1]) / (2 * dx)
    v_xx = (v[i + 1] - 2 * v[i] + v[i - 1]) / dx**2
    delta = v_x / S
    gamma = (v_xx - v_x) / S**2
    return FiniteDifferenceResult(float(v[i]), float(delta), float(gamma), spots, v, n_space, n_time)


def _smoothed_payoff(
    x: np.ndarray, dx: float, K: float, opt: OptionType, pointwise: np.ndarray
) -> np.ndarray:
    """Replace the payoff at the node whose cell contains ``ln K`` by its cell average.

    For a call, the average of ``max(e^y - K, 0)`` over ``[lo, hi]`` is
    ``((e^hi - e^c) - K (hi - c)) / dx`` with ``c = max(lo, ln K)``; the put is
    symmetric. Every other node keeps its pointwise payoff.
    """
    v = pointwise.copy()
    log_k = math.log(K)
    i = int(np.argmin(np.abs(x - log_k)))
    if 0 < i < len(x) - 1:
        lo, hi = x[i] - 0.5 * dx, x[i] + 0.5 * dx
        if opt is OptionType.CALL:
            c = max(lo, log_k)
            v[i] = max((math.exp(hi) - math.exp(c)) - K * (hi - c), 0.0) / dx
        else:
            c = min(hi, log_k)
            v[i] = max(K * (c - lo) - (math.exp(c) - math.exp(lo)), 0.0) / dx
    return v


def finite_difference_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
    exercise: Union[str, ExerciseStyle] = "european",
    n_space: int = 400,
    n_time: int = 400,
) -> float:
    """Convenience wrapper returning only the price from :func:`finite_difference_solve`."""
    return finite_difference_solve(S, K, T, r, sigma, q, option_type, exercise, n_space, n_time).price
