"""Closed-form European option prices.

* Black-Scholes-Merton with a continuous dividend yield ``q``
  (Black & Scholes, 1973; Merton, 1973; Hull, *Options, Futures and Other
  Derivatives*, 11th ed., ch. 15 and 17).
* Garman-Kohlhagen for FX options (Garman & Kohlhagen, 1983), which is
  Black-Scholes-Merton with the foreign interest rate playing the role of the
  dividend yield, ``q = r_f``.

Formulas
--------
.. math::

    d_1 = \\frac{\\ln(S/K) + (r - q + \\tfrac12\\sigma^2)T}{\\sigma\\sqrt{T}}, \\qquad
    d_2 = d_1 - \\sigma\\sqrt{T}

    C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2), \\qquad
    P = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1)

Every function here is vectorised: any argument may be a NumPy array and the
usual broadcasting rules apply. Scalars in, ``float`` out.
"""

from __future__ import annotations

from typing import Union

import numpy as np
from scipy.stats import norm

from pricing.utils import FloatOrArray, OptionType, to_option_type, validate_inputs

_TINY = 1e-14


def _as_output(x: np.ndarray) -> FloatOrArray:
    """Return a Python float for 0-d results, otherwise the array."""
    return float(x) if np.ndim(x) == 0 else x


def d1_d2(
    S: FloatOrArray, K: FloatOrArray, T: FloatOrArray, r: float, sigma: FloatOrArray, q: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Return the Black-Scholes ``d1`` and ``d2`` terms (Hull, eq. 15.20-15.21).

    Requires ``T > 0`` and ``sigma > 0``; callers handle the degenerate limits.
    """
    S, K, T, sigma = (np.asarray(x, dtype=float) for x in (S, K, T, sigma))
    vol_sqrt_t = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def black_scholes_price(
    S: FloatOrArray,
    K: FloatOrArray,
    T: FloatOrArray,
    r: float,
    sigma: FloatOrArray,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
) -> FloatOrArray:
    """Black-Scholes-Merton price of a European call or put.

    Parameters
    ----------
    S, K, T, r, sigma, q
        Spot, strike, years to expiry, risk-free rate, volatility and continuous
        dividend yield (see :mod:`pricing.utils` for conventions).
    option_type
        ``"call"`` or ``"put"``.

    Returns
    -------
    float or ndarray
        Present value of the option.

    Notes
    -----
    Implements Hull eq. 17.4-17.5. When ``sigma * sqrt(T) == 0`` the option is
    worth its discounted intrinsic value on the forward,
    ``max(phi * (S e^{-qT} - K e^{-rT}), 0)`` with ``phi = +1`` for calls and
    ``-1`` for puts, which is the limit of the formula.
    """
    validate_inputs(S, K, T, sigma)
    phi = 1.0 if to_option_type(option_type) is OptionType.CALL else -1.0

    S, K, T, sigma = np.broadcast_arrays(*(np.asarray(x, dtype=float) for x in (S, K, T, sigma)))
    disc_spot = S * np.exp(-q * T)
    disc_strike = K * np.exp(-r * T)

    degenerate = sigma * np.sqrt(T) < _TINY
    # Substitute harmless values where the formula is undefined; overwritten below.
    safe_T = np.where(degenerate, 1.0, T)
    safe_sigma = np.where(degenerate, 1.0, sigma)
    d1, d2 = d1_d2(S, K, safe_T, r, safe_sigma, q)

    value = phi * (disc_spot * norm.cdf(phi * d1) - disc_strike * norm.cdf(phi * d2))
    intrinsic = np.maximum(phi * (disc_spot - disc_strike), 0.0)
    return _as_output(np.where(degenerate, intrinsic, value))


def garman_kohlhagen_price(
    S: FloatOrArray,
    K: FloatOrArray,
    T: FloatOrArray,
    r_d: float,
    r_f: float,
    sigma: FloatOrArray,
    option_type: Union[str, OptionType] = "call",
) -> FloatOrArray:
    """Garman-Kohlhagen price of a European FX option.

    ``S`` is quoted in domestic currency per unit of foreign currency (e.g. USD
    per EUR for EUR/USD), and the result is in domestic currency per unit of
    foreign notional.

    .. math::

        C = S e^{-r_f T} N(d_1) - K e^{-r_d T} N(d_2)

    Reference: Garman, M. & Kohlhagen, S. (1983), "Foreign currency option
    values", *Journal of International Money and Finance* 2(3), 231-237.
    """
    return black_scholes_price(S, K, T, r_d, sigma, q=r_f, option_type=option_type)


def put_call_parity_gap(
    call: FloatOrArray, put: FloatOrArray, S: FloatOrArray, K: FloatOrArray, T: FloatOrArray, r: float, q: float = 0.0
) -> FloatOrArray:
    """Return ``C - P - (S e^{-qT} - K e^{-rT})``, which is zero for European options (Hull, eq. 11.6)."""
    return call - put - (S * np.exp(-q * np.asarray(T)) - K * np.exp(-r * np.asarray(T)))
