"""Statistics of a historical price series: returns, volatility, drawdown and risk-adjusted return.

All functions take a 1-D array of prices ordered oldest to newest and assume one
observation per trading day (``periods_per_year=252``) unless told otherwise.

Formulas
--------
* Log return: :math:`r_t = \\ln(P_t / P_{t-1})`
* Historical (realised) volatility, annualised (Hull, sec. 15.4):

  .. math:: \\hat\\sigma = \\sqrt{252}\\; \\mathrm{stdev}(r_t), \\quad \\text{sample stdev with } n-1

* Annualised return (geometric): :math:`(P_n / P_0)^{252/n} - 1`
* Sharpe ratio (Sharpe, 1966), annualised from daily excess log returns:
  :math:`\\sqrt{252}\\, \\overline{(r_t - r_f/252)} / \\mathrm{stdev}(r_t)`
* Maximum drawdown: :math:`\\max_t \\left(1 - P_t / \\max_{s \\le t} P_s\\right)`
* Trailing dividend yield: dividends paid over the last year divided by the latest price,
  the usual estimate of the continuous yield ``q`` used in Black-Scholes-Merton.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import ArrayLike
from scipy import stats

TRADING_DAYS = 252


def _prices(prices: ArrayLike) -> np.ndarray:
    p = np.asarray(prices, dtype=float)
    if p.ndim != 1:
        raise ValueError("prices must be one-dimensional.")
    if p.size < 2:
        raise ValueError("Need at least two prices.")
    if not np.all(np.isfinite(p)) or np.any(p <= 0):
        raise ValueError("Prices must be positive and finite.")
    return p


def log_returns(prices: ArrayLike) -> np.ndarray:
    """Daily log returns :math:`\\ln(P_t / P_{t-1})`; one fewer element than ``prices``."""
    p = _prices(prices)
    return np.diff(np.log(p))


def historical_volatility(
    prices: ArrayLike, window: Optional[int] = None, periods_per_year: int = TRADING_DAYS
) -> float:
    """Annualised volatility of log returns over the last ``window`` returns (all of them if ``None``)."""
    r = log_returns(prices)
    if window is not None:
        if window < 2:
            raise ValueError("window must be at least 2.")
        r = r[-window:]
    if r.size < 2:
        raise ValueError("Need at least two returns.")
    return float(np.std(r, ddof=1) * math.sqrt(periods_per_year))


def rolling_volatility(prices: ArrayLike, window: int, periods_per_year: int = TRADING_DAYS) -> np.ndarray:
    """Annualised rolling volatility, aligned with ``prices`` (``nan`` until ``window`` returns exist).

    Uses a cumulative-sum formulation of the sample variance, so it is O(n).
    """
    r = log_returns(prices)
    if window < 2:
        raise ValueError("window must be at least 2.")
    out = np.full(r.size + 1, np.nan)
    if r.size < window:
        return out
    c1 = np.concatenate([[0.0], np.cumsum(r)])
    c2 = np.concatenate([[0.0], np.cumsum(r * r)])
    s1 = c1[window:] - c1[:-window]
    s2 = c2[window:] - c2[:-window]
    var = np.maximum((s2 - s1 * s1 / window) / (window - 1), 0.0)
    out[window:] = np.sqrt(var * periods_per_year)
    return out


def annualized_return(prices: ArrayLike, periods_per_year: int = TRADING_DAYS) -> float:
    """Geometric annualised return :math:`(P_n/P_0)^{252/n} - 1` with ``n`` the number of returns."""
    p = _prices(prices)
    n = p.size - 1
    return float((p[-1] / p[0]) ** (periods_per_year / n) - 1.0)


def max_drawdown(prices: ArrayLike) -> float:
    """Largest peak-to-trough fall, as a positive fraction (0.25 means a 25% drawdown)."""
    p = _prices(prices)
    peaks = np.maximum.accumulate(p)
    return float(np.max(1.0 - p / peaks))


def sharpe_ratio(prices: ArrayLike, risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    """Annualised Sharpe ratio of daily log returns in excess of ``risk_free`` (annual, continuous)."""
    r = log_returns(prices)
    sd = np.std(r, ddof=1)
    if sd == 0:
        return float("nan")
    excess = r - risk_free / periods_per_year
    return float(np.mean(excess) / sd * math.sqrt(periods_per_year))


def trailing_dividend_yield(
    dividend_amounts: ArrayLike, dividend_ages_days: ArrayLike, last_price: float, lookback_days: float = 365.0
) -> float:
    """Dividends paid within ``lookback_days`` of the last observation, divided by ``last_price``.

    Parameters
    ----------
    dividend_amounts
        Cash dividend per share for each payment.
    dividend_ages_days
        How many calendar days before the last observation each payment was made.
    """
    amounts = np.asarray(dividend_amounts, dtype=float)
    ages = np.asarray(dividend_ages_days, dtype=float)
    if amounts.shape != ages.shape:
        raise ValueError("dividend_amounts and dividend_ages_days must have the same shape.")
    if last_price <= 0:
        raise ValueError("last_price must be positive.")
    recent = (ages >= 0) & (ages <= lookback_days) & np.isfinite(amounts)
    return float(amounts[recent].sum() / last_price)


@dataclass(frozen=True)
class ReturnSummary:
    """Headline statistics of a price history."""

    n_days: int
    annual_return: float
    annual_volatility: float
    sharpe: float
    max_drawdown: float
    skewness: float
    excess_kurtosis: float
    worst_day: float
    best_day: float


def summarize(prices: ArrayLike, risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> ReturnSummary:
    """All headline statistics at once. Skewness and excess kurtosis are of daily log returns
    (a normal distribution has 0 for both; equities typically show negative skew and fat tails)."""
    p = _prices(prices)
    r = log_returns(p)
    return ReturnSummary(
        n_days=int(r.size),
        annual_return=annualized_return(p, periods_per_year),
        annual_volatility=historical_volatility(p, periods_per_year=periods_per_year),
        sharpe=sharpe_ratio(p, risk_free, periods_per_year),
        max_drawdown=max_drawdown(p),
        skewness=float(stats.skew(r, bias=False)) if r.size > 2 else float("nan"),
        excess_kurtosis=float(stats.kurtosis(r, fisher=True, bias=False)) if r.size > 3 else float("nan"),
        worst_day=float(np.expm1(r.min())),
        best_day=float(np.expm1(r.max())),
    )
