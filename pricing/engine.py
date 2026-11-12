"""A single entry point that prices one option with any of the four methods.

The UI talks to the library through this module so that every page uses
identical settings and the four methods can be compared like for like.

Example
-------
>>> from pricing.engine import OptionSpec, Method, price
>>> spec = OptionSpec(S=100, K=100, T=1.0, r=0.05, sigma=0.2)
>>> round(price(spec, Method.BLACK_SCHOLES).price, 4)
10.4506
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from pricing.greeks import BumpSizes, Greeks, PricerFn, black_scholes_greeks, numerical_greeks
from pricing.models.binomial import binomial_price, binomial_tree_greeks
from pricing.models.black_scholes import black_scholes_price
from pricing.models.finite_difference import finite_difference_price, finite_difference_solve
from pricing.models.monte_carlo import monte_carlo_price
from pricing.utils import ExerciseStyle, OptionType, to_exercise_style, to_option_type


class Method(str, Enum):
    """Available pricing methods."""

    BLACK_SCHOLES = "black_scholes"
    BINOMIAL = "binomial"
    MONTE_CARLO = "monte_carlo"
    FINITE_DIFFERENCE = "finite_difference"


@dataclass(frozen=True)
class OptionSpec:
    """Contract and market data for a single vanilla option (conventions in :mod:`pricing.utils`)."""

    S: float
    K: float
    T: float
    r: float
    sigma: float
    q: float = 0.0
    option_type: OptionType = OptionType.CALL
    exercise: ExerciseStyle = ExerciseStyle.EUROPEAN

    def __post_init__(self) -> None:
        object.__setattr__(self, "option_type", to_option_type(self.option_type))
        object.__setattr__(self, "exercise", to_exercise_style(self.exercise))

    def with_(self, **changes: object) -> "OptionSpec":
        """Return a copy with some fields replaced."""
        return replace(self, **changes)


@dataclass(frozen=True)
class NumericalSettings:
    """Resolution of the numerical methods. Defaults give ~1e-3 accuracy in well under a second."""

    binomial_steps: int = 500
    mc_paths: int = 100_000
    mc_antithetic: bool = True
    mc_control_variate: bool = True
    mc_seed: Optional[int] = 42
    pde_space_steps: int = 400
    pde_time_steps: int = 400


@dataclass(frozen=True)
class PriceResult:
    """Price from one method, with Monte Carlo error bars where relevant.

    ``available`` is ``False`` when the method cannot price this contract
    (e.g. closed-form Black-Scholes for an American put); ``reason`` says why.
    """

    method: Method
    price: Optional[float]
    runtime_ms: float
    available: bool = True
    reason: str = ""
    std_error: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None


def supports(spec: OptionSpec, method: Method) -> tuple[bool, str]:
    """Whether ``method`` can price ``spec``, and if not, a short reason code.

    An American call with no dividend yield is identical to the European call
    (Merton, 1973), so Black-Scholes and Monte Carlo are allowed in that case.
    """
    if spec.exercise is ExerciseStyle.EUROPEAN:
        return True, ""
    if method in (Method.BINOMIAL, Method.FINITE_DIFFERENCE):
        return True, ""
    if spec.option_type is OptionType.CALL and spec.q <= 0.0:
        return True, ""
    return False, "european_only"


def pricer_for(spec: OptionSpec, method: Method, settings: NumericalSettings = NumericalSettings()) -> PricerFn:
    """Return ``f(S, K, T, r, sigma, q) -> price`` for ``method`` with type, exercise and settings bound.

    Used for bump-and-reprice Greeks and for convergence studies.
    """
    opt, ex = spec.option_type, spec.exercise

    if method is Method.BLACK_SCHOLES:
        return lambda S, K, T, r, sigma, q: float(black_scholes_price(S, K, T, r, sigma, q, opt))
    if method is Method.BINOMIAL:
        return lambda S, K, T, r, sigma, q: binomial_price(S, K, T, r, sigma, q, opt, ex, settings.binomial_steps)
    if method is Method.MONTE_CARLO:
        return lambda S, K, T, r, sigma, q: monte_carlo_price(
            S, K, T, r, sigma, q, opt,
            n_paths=settings.mc_paths,
            antithetic=settings.mc_antithetic,
            control_variate=settings.mc_control_variate,
            seed=settings.mc_seed,
        ).price
    if method is Method.FINITE_DIFFERENCE:
        return lambda S, K, T, r, sigma, q: finite_difference_price(
            S, K, T, r, sigma, q, opt, ex, settings.pde_space_steps, settings.pde_time_steps
        )
    raise ValueError(f"Unknown method {method!r}")


def price(spec: OptionSpec, method: Method, settings: NumericalSettings = NumericalSettings()) -> PriceResult:
    """Price ``spec`` with ``method``, timing the call."""
    ok, reason = supports(spec, method)
    if not ok:
        return PriceResult(method, None, 0.0, available=False, reason=reason)

    start = time.perf_counter()
    if method is Method.MONTE_CARLO:
        mc = monte_carlo_price(
            spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q, spec.option_type,
            n_paths=settings.mc_paths,
            antithetic=settings.mc_antithetic,
            control_variate=settings.mc_control_variate,
            seed=settings.mc_seed,
        )
        elapsed = (time.perf_counter() - start) * 1e3
        return PriceResult(method, mc.price, elapsed, std_error=mc.std_error, ci_low=mc.ci_low, ci_high=mc.ci_high)

    value = pricer_for(spec, method, settings)(spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q)
    return PriceResult(method, value, (time.perf_counter() - start) * 1e3)


def price_all(spec: OptionSpec, settings: NumericalSettings = NumericalSettings()) -> dict[Method, PriceResult]:
    """Price ``spec`` with every method."""
    return {m: price(spec, m, settings) for m in Method}


def greeks(spec: OptionSpec, method: Method, settings: NumericalSettings = NumericalSettings()) -> Optional[Greeks]:
    """Greeks of ``spec`` under ``method``.

    * Black-Scholes: closed form.
    * Binomial: delta, gamma and theta read off the first two tree steps
      (Hull, sec. 21.1); vega and rho by bump-and-reprice.
    * Finite difference: delta and gamma read off the final grid; vega, theta
      and rho by bump-and-reprice.
    * Monte Carlo: everything by bump-and-reprice with common random numbers
      (fixed seed) and a 1% spot bump, since smaller spot bumps amplify noise
      in gamma.

    Returns ``None`` if the method cannot price the contract, or if ``T`` or
    ``sigma`` is zero.
    """
    if not supports(spec, method)[0] or spec.T <= 0.0 or spec.sigma <= 0.0:
        return None
    args = (spec.S, spec.K, spec.T, spec.r, spec.sigma, spec.q)
    if method is Method.BLACK_SCHOLES:
        return black_scholes_greeks(*args, spec.option_type)

    pricer = pricer_for(spec, method, settings)
    if method is Method.BINOMIAL:
        _, delta, gamma, theta = binomial_tree_greeks(
            *args, spec.option_type, spec.exercise, max(settings.binomial_steps, 3)
        )
        bumped = numerical_greeks(pricer, *args, include=("vega", "rho"))
        return Greeks(delta, gamma, bumped.vega, theta, bumped.rho)
    if method is Method.FINITE_DIFFERENCE:
        grid = finite_difference_solve(
            *args, spec.option_type, spec.exercise, settings.pde_space_steps, settings.pde_time_steps
        )
        bumped = numerical_greeks(pricer, *args, include=("vega", "theta", "rho"))
        return Greeks(grid.delta, grid.gamma, bumped.vega, bumped.theta, bumped.rho)
    return numerical_greeks(pricer, *args, bumps=BumpSizes(spot=0.01))
