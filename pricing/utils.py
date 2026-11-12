"""Shared types, input validation and payoff functions used by every pricing model.

Conventions used throughout the package
---------------------------------------
* ``S``      spot price of the underlying (for FX: domestic units per 1 foreign unit)
* ``K``      strike price
* ``T``      time to expiry in years
* ``r``      continuously compounded risk-free rate (for FX: the domestic rate)
* ``q``      continuous dividend yield (for FX: the foreign rate ``r_f``)
* ``sigma``  annualised volatility of log-returns

All rates and volatilities are decimals (0.05 means 5%).
"""

from __future__ import annotations

from enum import Enum
from typing import Union

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatOrArray = Union[float, NDArray[np.float64]]


class OptionType(str, Enum):
    """Right conveyed by the option."""

    CALL = "call"
    PUT = "put"


class ExerciseStyle(str, Enum):
    """When the holder may exercise."""

    EUROPEAN = "european"
    AMERICAN = "american"


def to_option_type(value: Union[str, OptionType]) -> OptionType:
    """Normalise ``"call"``/``"put"`` (any case) or an :class:`OptionType` to an :class:`OptionType`."""
    if isinstance(value, OptionType):
        return value
    try:
        return OptionType(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError(f"option_type must be 'call' or 'put', got {value!r}") from exc


def to_exercise_style(value: Union[str, ExerciseStyle]) -> ExerciseStyle:
    """Normalise ``"european"``/``"american"`` or an :class:`ExerciseStyle`."""
    if isinstance(value, ExerciseStyle):
        return value
    try:
        return ExerciseStyle(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError(f"exercise must be 'european' or 'american', got {value!r}") from exc


def validate_inputs(S: float, K: float, T: float, sigma: float) -> None:
    """Raise ``ValueError`` for economically meaningless scalar inputs.

    Spot and strike must be strictly positive; time and volatility must be
    non-negative. (Zero time or zero volatility are allowed: they are handled as
    limiting cases by the closed-form model.)
    """
    if not np.all(np.asarray(S) > 0):
        raise ValueError("Spot S must be positive.")
    if not np.all(np.asarray(K) > 0):
        raise ValueError("Strike K must be positive.")
    if not np.all(np.asarray(T) >= 0):
        raise ValueError("Time to expiry T must be non-negative.")
    if not np.all(np.asarray(sigma) >= 0):
        raise ValueError("Volatility sigma must be non-negative.")


def payoff(S_T: ArrayLike, K: float, option_type: Union[str, OptionType]) -> NDArray[np.float64]:
    """Vanilla payoff at expiry.

    Call: ``max(S_T - K, 0)``; put: ``max(K - S_T, 0)``.
    """
    S_T = np.asarray(S_T, dtype=float)
    if to_option_type(option_type) is OptionType.CALL:
        return np.maximum(S_T - K, 0.0)
    return np.maximum(K - S_T, 0.0)


def forward_price(S: FloatOrArray, T: FloatOrArray, r: float, q: float = 0.0) -> FloatOrArray:
    """Forward price under continuous carry: ``F = S * exp((r - q) * T)`` (Hull, ch. 5)."""
    return S * np.exp((r - q) * T)
