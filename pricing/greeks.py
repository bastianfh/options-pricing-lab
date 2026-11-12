"""Option sensitivities ("Greeks"): analytical for Black-Scholes, finite differences for any pricer.

Units (raw mathematical derivatives, no market scaling):

* ``delta = dV/dS``
* ``gamma = d2V/dS2``
* ``vega  = dV/dsigma``   per 1.00 (100 vol points) of volatility
* ``theta = dV/dt = -dV/dT``  per year of calendar time
* ``rho   = dV/dr``       per 1.00 (10,000 bp) of the domestic rate

The UI converts to the usual quoting conventions (vega per vol point, theta
per day, rho per 1%).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Union

import numpy as np
from scipy.stats import norm

from pricing.models.black_scholes import black_scholes_price, d1_d2
from pricing.utils import FloatOrArray, OptionType, to_option_type, validate_inputs

GREEK_NAMES: tuple[str, ...] = ("delta", "gamma", "vega", "theta", "rho")

PricerFn = Callable[[float, float, float, float, float, float], float]
"""A pricer with signature ``f(S, K, T, r, sigma, q) -> price``; option type etc. are bound in advance."""


@dataclass(frozen=True)
class Greeks:
    """First- and second-order sensitivities of an option value (raw units, see module docstring)."""

    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float

    def as_dict(self) -> dict[str, float]:
        """Return the Greeks as a plain ``{name: value}`` dictionary."""
        return asdict(self)


def black_scholes_greeks(
    S: FloatOrArray,
    K: FloatOrArray,
    T: FloatOrArray,
    r: float,
    sigma: FloatOrArray,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
) -> Greeks:
    """Closed-form Black-Scholes-Merton Greeks (Hull, ch. 19; Haug, 2007, sec. 2.1).

    With :math:`\\phi = +1` for a call and :math:`-1` for a put:

    .. math::

        \\Delta = \\phi e^{-qT} N(\\phi d_1), \\qquad
        \\Gamma = \\frac{e^{-qT} n(d_1)}{S\\sigma\\sqrt{T}}, \\qquad
        \\mathcal{V} = S e^{-qT} n(d_1)\\sqrt{T}

        \\Theta = -\\frac{S e^{-qT} n(d_1)\\sigma}{2\\sqrt{T}}
                  - \\phi r K e^{-rT} N(\\phi d_2) + \\phi q S e^{-qT} N(\\phi d_1), \\qquad
        \\rho = \\phi K T e^{-rT} N(\\phi d_2)

    Arguments may be arrays (the fields of the result are then arrays). Requires
    ``T > 0`` and ``sigma > 0``.
    """
    validate_inputs(S, K, T, sigma)
    if np.any(np.asarray(T) <= 0) or np.any(np.asarray(sigma) <= 0):
        raise ValueError("Analytical Greeks require T > 0 and sigma > 0.")
    phi = 1.0 if to_option_type(option_type) is OptionType.CALL else -1.0
    S, K, T, sigma = (np.asarray(x, dtype=float) for x in (S, K, T, sigma))

    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    sqrt_t = np.sqrt(T)
    disc_q, disc_r = np.exp(-q * T), np.exp(-r * T)
    pdf_d1 = norm.pdf(d1)

    delta = phi * disc_q * norm.cdf(phi * d1)
    gamma = disc_q * pdf_d1 / (S * sigma * sqrt_t)
    vega = S * disc_q * pdf_d1 * sqrt_t
    theta = (
        -S * disc_q * pdf_d1 * sigma / (2 * sqrt_t)
        - phi * r * K * disc_r * norm.cdf(phi * d2)
        + phi * q * S * disc_q * norm.cdf(phi * d1)
    )
    rho = phi * K * T * disc_r * norm.cdf(phi * d2)

    def out(x: np.ndarray) -> FloatOrArray:
        return float(x) if np.ndim(x) == 0 else x

    return Greeks(out(delta), out(gamma), out(vega), out(theta), out(rho))


@dataclass(frozen=True)
class BumpSizes:
    """Finite-difference step sizes.

    ``spot`` is relative (a fraction of S); the others are absolute.
    ``time`` is capped at ``T / 2`` so the backward point stays positive.
    """

    spot: float = 0.005
    vol: float = 0.01
    time: float = 1.0 / 365.0
    rate: float = 0.001


def numerical_greeks(
    pricer: PricerFn,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    bumps: BumpSizes = BumpSizes(),
    include: Iterable[str] = GREEK_NAMES,
) -> Greeks:
    """Greeks of an arbitrary pricer by central finite differences ("bump and reprice").

    .. math::

        \\Delta \\approx \\frac{V(S+h) - V(S-h)}{2h}, \\qquad
        \\Gamma \\approx \\frac{V(S+h) - 2V(S) + V(S-h)}{h^2},

    and likewise central differences in :math:`\\sigma`, :math:`T` and
    :math:`r`. All have truncation error :math:`O(h^2)` (Glasserman, 2003,
    sec. 7.1). For Monte Carlo pricers, pass a fixed seed so that all bumped
    prices share the same random numbers ("common random numbers"); otherwise
    the differences are dominated by simulation noise.

    Parameters
    ----------
    pricer
        Callable ``f(S, K, T, r, sigma, q) -> price``, e.g. a
        :func:`functools.partial` of a model with option type and settings bound.
    bumps
        Step sizes, see :class:`BumpSizes`.
    include
        Names of the Greeks to compute; the others are returned as ``nan``.
        Lets callers that have a better estimate of some Greeks (e.g. read off
        a tree or grid) skip unnecessary repricings.
    """
    wanted = set(include)
    out = dict.fromkeys(GREEK_NAMES, float("nan"))

    if wanted & {"delta", "gamma"}:
        h = bumps.spot * S
        v_up = pricer(S + h, K, T, r, sigma, q)
        v_dn = pricer(S - h, K, T, r, sigma, q)
        out["delta"] = (v_up - v_dn) / (2 * h)
        if "gamma" in wanted:
            out["gamma"] = (v_up - 2 * pricer(S, K, T, r, sigma, q) + v_dn) / h**2
    if "vega" in wanted:
        dv = min(bumps.vol, 0.5 * sigma)
        out["vega"] = (pricer(S, K, T, r, sigma + dv, q) - pricer(S, K, T, r, sigma - dv, q)) / (2 * dv)
    if "theta" in wanted:
        dt = min(bumps.time, 0.5 * T)
        out["theta"] = (pricer(S, K, T - dt, r, sigma, q) - pricer(S, K, T + dt, r, sigma, q)) / (2 * dt)
    if "rho" in wanted:
        dr = bumps.rate
        out["rho"] = (pricer(S, K, T, r + dr, sigma, q) - pricer(S, K, T, r - dr, sigma, q)) / (2 * dr)
    return Greeks(**{k: float(v) for k, v in out.items()})


def black_scholes_pricer(option_type: Union[str, OptionType]) -> PricerFn:
    """Return ``f(S, K, T, r, sigma, q)`` for Black-Scholes with the option type bound."""
    opt = to_option_type(option_type)

    def f(S: float, K: float, T: float, r: float, sigma: float, q: float) -> float:
        return float(black_scholes_price(S, K, T, r, sigma, q, opt))

    return f


def theta_per_day(theta: float, days_per_year: float = 365.0) -> float:
    """Convert theta per year to theta per calendar day."""
    return theta / days_per_year


def vega_per_vol_point(vega: float) -> float:
    """Convert vega per 1.00 of volatility to vega per 1 vol point (1%)."""
    return vega / 100.0


def rho_per_percent(rho: float) -> float:
    """Convert rho per 1.00 of rate to rho per 1 percentage point."""
    return rho / 100.0


__all__ = [
    "GREEK_NAMES",
    "BumpSizes",
    "Greeks",
    "PricerFn",
    "black_scholes_greeks",
    "black_scholes_pricer",
    "numerical_greeks",
    "rho_per_percent",
    "theta_per_day",
    "vega_per_vol_point",
]
