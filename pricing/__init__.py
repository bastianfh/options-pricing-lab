"""pricing: an options pricing library written from scratch with NumPy and SciPy.

The package has no UI dependencies. Models live in :mod:`pricing.models`;
Greeks, implied volatility and strategy analytics are top-level modules.
"""

from pricing.models.black_scholes import black_scholes_price, garman_kohlhagen_price
from pricing.utils import ExerciseStyle, OptionType

__all__ = [
    "ExerciseStyle",
    "OptionType",
    "black_scholes_price",
    "garman_kohlhagen_price",
]

__version__ = "1.0.0"
