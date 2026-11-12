"""pricing: an options pricing library written from scratch with NumPy and SciPy.

The package has no UI dependencies.

* :mod:`pricing.models` - Black-Scholes / Garman-Kohlhagen, CRR binomial tree,
  Monte Carlo, Crank-Nicolson finite differences
* :mod:`pricing.greeks` - analytical and bump-and-reprice Greeks
* :mod:`pricing.implied_vol` - implied volatility solver and surfaces
* :mod:`pricing.strategies` - multi-leg payoffs and P&L
* :mod:`pricing.convergence` - convergence studies used for validation
* :mod:`pricing.engine` - one API across all methods

Quick start
-----------
>>> from pricing import OptionSpec, Method, price
>>> spec = OptionSpec(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="put")
>>> round(price(spec, Method.BINOMIAL).price, 2)
5.57
"""

from pricing.engine import Method, NumericalSettings, OptionSpec, PriceResult, greeks, price, price_all
from pricing.greeks import Greeks, black_scholes_greeks, numerical_greeks
from pricing.implied_vol import implied_volatility, implied_volatility_solve
from pricing.models.binomial import binomial_price
from pricing.models.black_scholes import black_scholes_price, garman_kohlhagen_price
from pricing.models.finite_difference import finite_difference_price, finite_difference_solve
from pricing.models.monte_carlo import MonteCarloResult, monte_carlo_price
from pricing.utils import ExerciseStyle, OptionType

__all__ = [
    "ExerciseStyle",
    "Greeks",
    "Method",
    "MonteCarloResult",
    "NumericalSettings",
    "OptionSpec",
    "OptionType",
    "PriceResult",
    "binomial_price",
    "black_scholes_greeks",
    "black_scholes_price",
    "finite_difference_price",
    "finite_difference_solve",
    "garman_kohlhagen_price",
    "greeks",
    "implied_volatility",
    "implied_volatility_solve",
    "monte_carlo_price",
    "numerical_greeks",
    "price",
    "price_all",
]

__version__ = "1.0.0"
