"""Implied volatility: invert Black-Scholes for sigma, and build an implied volatility surface.

Solver
------
Find :math:`\\sigma` with :math:`BS(\\sigma) = V_{mkt}`. Newton-Raphson uses
vega as the derivative,

.. math::

    \\sigma_{k+1} = \\sigma_k - \\frac{BS(\\sigma_k) - V_{mkt}}{\\mathcal{V}(\\sigma_k)},

which converges quadratically near the root. It can overshoot when vega is
small (deep in/out of the money, or very short expiries), so the solver keeps
a bracket :math:`[\\sigma_{lo}, \\sigma_{hi}]` known to contain the root and
falls back to a bisection step whenever a Newton step would leave the bracket
or vega is too small. Black-Scholes prices are strictly increasing in
:math:`\\sigma`, so the root is unique and the safeguarded method always
converges (Press et al., *Numerical Recipes*, 3rd ed., sec. 9.4, ``rtsafe``).

The initial guess is the Brenner-Subrahmanyam (1988) approximation
:math:`\\sigma_0 \\approx \\sqrt{2\\pi/T}\\, V / (S e^{-qT})`, clipped to a sane range.

No-arbitrage bounds
-------------------
A price has an implied volatility only if it lies strictly between the
:math:`\\sigma \\to 0` and :math:`\\sigma \\to \\infty` limits:
:math:`\\max(\\phi(Se^{-qT} - Ke^{-rT}), 0) < V < Se^{-qT}` (call) or
:math:`< Ke^{-rT}` (put).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Union

import numpy as np
from scipy.stats import norm

from pricing.models.black_scholes import black_scholes_price
from pricing.utils import OptionType, to_option_type

SIGMA_MIN = 1e-6
SIGMA_MAX = 10.0


@dataclass(frozen=True)
class ImpliedVolResult:
    """Outcome of an implied volatility solve.

    Attributes
    ----------
    sigma
        Implied volatility.
    iterations
        Total iterations taken.
    newton_steps, bisection_steps
        How many iterations used each update rule.
    converged
        Whether the price error fell below the tolerance.
    """

    sigma: float
    iterations: int
    newton_steps: int
    bisection_steps: int
    converged: bool


def price_bounds(
    S: float, K: float, T: float, r: float, q: float, option_type: Union[str, OptionType]
) -> tuple[float, float]:
    """Return the (lower, upper) no-arbitrage bounds of a European option price (Hull, ch. 11)."""
    disc_s, disc_k = S * math.exp(-q * T), K * math.exp(-r * T)
    if to_option_type(option_type) is OptionType.CALL:
        return max(disc_s - disc_k, 0.0), disc_s
    return max(disc_k - disc_s, 0.0), disc_k


def implied_volatility_solve(
    price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
    tol: float = 1e-12,
    sigma_tol: float = 1e-12,
    max_iter: int = 100,
    initial_guess: Optional[float] = None,
) -> ImpliedVolResult:
    """Solve for Black-Scholes implied volatility with safeguarded Newton-Raphson.

    Parameters
    ----------
    price
        Observed option price.
    S, K, T, r, q
        Spot, strike, years to expiry, risk-free rate, continuous yield.
    option_type
        ``"call"`` or ``"put"``.
    tol
        Stop when the price error ``|BS(sigma) - price|`` is below this.
    sigma_tol
        Also stop when an update moves sigma by less than this. Needed for
        far out-of-the-money options whose prices are so small that an
        absolute price tolerance does not pin down sigma.
    max_iter
        Maximum iterations.
    initial_guess
        Starting volatility; defaults to the Brenner-Subrahmanyam approximation.

    Raises
    ------
    ValueError
        If ``T <= 0`` or the price violates the no-arbitrage bounds.
    """
    opt = to_option_type(option_type)
    if T <= 0.0:
        raise ValueError("Implied volatility needs T > 0.")
    lower, upper = price_bounds(S, K, T, r, q, opt)
    if not lower < price < upper:
        raise ValueError(f"Price {price:.6g} is outside the no-arbitrage bounds ({lower:.6g}, {upper:.6g}).")

    def objective(sig: float) -> float:
        return float(black_scholes_price(S, K, T, r, sig, q, opt)) - price

    lo, hi = SIGMA_MIN, SIGMA_MAX
    if initial_guess is None:
        initial_guess = math.sqrt(2 * math.pi / T) * price / (S * math.exp(-q * T))
    sigma = min(max(initial_guess, 0.01), 3.0)

    newton = bisect = 0
    for it in range(1, max_iter + 1):
        f = objective(sigma)
        if abs(f) < tol:
            return ImpliedVolResult(sigma, it, newton, bisect, True)
        # Price is increasing in sigma: a positive error means sigma is too high.
        if f > 0:
            hi = sigma
        else:
            lo = sigma

        d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        vega = S * math.exp(-q * T) * norm.pdf(d1) * math.sqrt(T)
        candidate = sigma - f / vega if vega > 1e-300 else float("nan")
        if lo < candidate < hi:
            new_sigma, newton = candidate, newton + 1
        else:
            new_sigma, bisect = 0.5 * (lo + hi), bisect + 1
        step, sigma = abs(new_sigma - sigma), new_sigma
        if step < sigma_tol:
            return ImpliedVolResult(sigma, it, newton, bisect, True)

    return ImpliedVolResult(sigma, max_iter, newton, bisect, False)


def implied_volatility(
    price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
    **kwargs: float,
) -> float:
    """Implied volatility as a float. See :func:`implied_volatility_solve` for details."""
    return implied_volatility_solve(price, S, K, T, r, q, option_type, **kwargs).sigma


# ---------------------------------------------------------------------------
# Volatility surface
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SmileParameters:
    """Parameters of the synthetic "market" smile used to generate test prices.

    Volatility as a function of standardised log-moneyness
    :math:`m = \\ln(K/F) / \\sqrt{T}`:

    .. math::

        \\sigma(K, T) = \\sigma_{ATM}(T) + \\text{skew}\\cdot m + \\text{curvature}\\cdot m^2,
        \\qquad \\sigma_{ATM}(T) = \\text{atm\\_vol} + \\text{term\\_slope}\\cdot(\\sqrt{T} - \\sqrt{0.5})

    Dividing by :math:`\\sqrt T` makes short-dated smiles steeper, as observed
    in equity and FX markets. A negative ``skew`` gives the equity-style
    "smirk". This is a convenient illustration, not an arbitrage-free model
    such as SVI (Gatheral, 2004).
    """

    atm_vol: float = 0.20
    skew: float = -0.10
    curvature: float = 0.08
    term_slope: float = 0.03
    floor: float = 0.03


def synthetic_vol(
    strikes: np.ndarray, expiries: np.ndarray, S: float, r: float, q: float, params: SmileParameters
) -> np.ndarray:
    """Evaluate the synthetic smile on a grid; returns shape ``(len(expiries), len(strikes))``."""
    T = np.asarray(expiries, dtype=float)[:, None]
    K = np.asarray(strikes, dtype=float)[None, :]
    forward = S * np.exp((r - q) * T)
    m = np.log(K / forward) / np.sqrt(T)
    atm = params.atm_vol + params.term_slope * (np.sqrt(T) - math.sqrt(0.5))
    return np.maximum(atm + params.skew * m + params.curvature * m**2, params.floor)


@dataclass(frozen=True)
class VolSurface:
    """An implied volatility surface on a strike x expiry grid.

    ``vols[i, j]`` is the implied volatility at ``expiries[i]`` and
    ``strikes[j]``; ``nan`` where no volatility could be implied.
    """

    strikes: np.ndarray
    expiries: np.ndarray
    vols: np.ndarray
    prices: np.ndarray
    option_types: np.ndarray


def otm_option_types(strikes: np.ndarray, expiries: np.ndarray, S: float, r: float, q: float) -> np.ndarray:
    """Pick the out-of-the-money option at each grid point: puts below the forward, calls above.

    Market practice: OTM options are more liquid, and their prices are
    pure time value, so the implied volatility is better conditioned.
    """
    forward = S * np.exp((r - q) * np.asarray(expiries, dtype=float)[:, None])
    return np.where(np.asarray(strikes, dtype=float)[None, :] < forward, "put", "call")


def implied_vol_surface(
    prices: np.ndarray,
    strikes: Sequence[float],
    expiries: Sequence[float],
    S: float,
    r: float,
    q: float = 0.0,
    option_types: Union[np.ndarray, Literal["call", "put", "otm"]] = "otm",
) -> VolSurface:
    """Invert a grid of option prices into an implied volatility surface.

    Parameters
    ----------
    prices
        Array of shape ``(len(expiries), len(strikes))``.
    option_types
        ``"call"``, ``"put"``, ``"otm"`` (OTM puts below the forward, calls
        above) or an array of ``"call"``/``"put"`` with the same shape as ``prices``.
    """
    strikes_a, expiries_a = np.asarray(strikes, dtype=float), np.asarray(expiries, dtype=float)
    prices = np.asarray(prices, dtype=float)
    if isinstance(option_types, str):
        types = (
            otm_option_types(strikes_a, expiries_a, S, r, q)
            if option_types == "otm"
            else np.full(prices.shape, option_types)
        )
    else:
        types = np.asarray(option_types)

    vols = np.full(prices.shape, np.nan)
    for i, T in enumerate(expiries_a):
        for j, K in enumerate(strikes_a):
            try:
                vols[i, j] = implied_volatility(prices[i, j], S, K, T, r, q, types[i, j])
            except ValueError:
                pass  # price outside arbitrage bounds or unusable -> leave as nan
    return VolSurface(strikes_a, expiries_a, vols, prices, types)


def synthetic_surface(
    S: float,
    r: float,
    q: float,
    params: SmileParameters = SmileParameters(),
    strikes: Optional[Sequence[float]] = None,
    expiries: Optional[Sequence[float]] = None,
) -> VolSurface:
    """Generate OTM option prices from :class:`SmileParameters` and recover the surface by inversion.

    The round trip (vol -> price -> implied vol) exercises the solver on every
    grid point; the recovered vols match the inputs to solver tolerance.
    """
    strikes_a = np.asarray(strikes if strikes is not None else S * np.linspace(0.7, 1.3, 25), dtype=float)
    expiries_a = np.asarray(
        expiries if expiries is not None else [1 / 12, 2 / 12, 3 / 12, 6 / 12, 9 / 12, 1.0, 1.5, 2.0], dtype=float
    )
    true_vols = synthetic_vol(strikes_a, expiries_a, S, r, q, params)
    types = otm_option_types(strikes_a, expiries_a, S, r, q)
    prices = np.empty_like(true_vols)
    for i, T in enumerate(expiries_a):
        for kind in ("call", "put"):
            mask = types[i] == kind
            prices[i, mask] = black_scholes_price(S, strikes_a[mask], T, r, true_vols[i, mask], q, kind)
    return implied_vol_surface(prices, strikes_a, expiries_a, S, r, q, types)
