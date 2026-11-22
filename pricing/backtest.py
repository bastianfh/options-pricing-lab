"""Historical backtests of rolling option strategies on a real price series.

How a backtest works
--------------------
* Start with capital equal to one share at the first price. Strategies that hold the
  stock buy one share; the rest of the capital sits in cash earning the risk-free rate.
* On each roll date, open the strategy's option legs with strikes set relative to the
  current price (e.g. a call 5% out of the money) and an expiry ``tenor_days`` later.
  Hold them to expiry, settle at intrinsic value, and immediately open the next set.
* Every day, mark the options to model (Black-Scholes) and record the portfolio value.
  Dividends are paid in cash on the shares held.

Option prices are **model prices**, not historical quotes: free historical option data
does not exist, so each option is priced with Black-Scholes-Merton using the stock's
trailing realised volatility, optionally scaled up by a volatility premium (implied
volatility usually trades above realised). Transaction costs can be added as a bid-ask
spread (a fraction of the option price, half paid on entry) and a commission per option.
These are standard simplifications for teaching and should be stated in any write-up.

The benchmark is buying one share at the start and holding it, with dividends kept in
cash that also earns the risk-free rate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional, Sequence

import numpy as np
import pandas as pd

from pricing.historical import max_drawdown, rolling_volatility
from pricing.models.black_scholes import black_scholes_price

LegKind = Literal["call", "put", "stock"]


@dataclass(frozen=True)
class LegTemplate:
    """One leg of a strategy, with its strike as a multiple of the spot at each roll."""

    kind: LegKind
    quantity: float
    moneyness: float = 1.0


@dataclass(frozen=True)
class BacktestConfig:
    """Strategy and modelling assumptions.

    Attributes
    ----------
    legs
        Strategy legs; stock legs are held throughout, option legs are rolled.
    tenor_days
        Calendar days from opening to expiry (expiry falls on the first trading day on or after).
    vol_window
        Trading days of returns used for the trailing realised volatility.
    vol_premium
        Proportional uplift applied to realised vol when pricing (0.1 prices at 110% of realised).
    vol_floor
        Lowest volatility used, so a calm spell never prices options at almost zero.
    rate
        Continuously compounded risk-free rate (cash interest and option pricing).
    dividend_yield
        Continuous yield used in option pricing (actual dividends are paid separately).
    spread
        Bid-ask spread as a fraction of the option price; half is paid on each opening trade.
    commission
        Commission per option per share (0.0065 is $0.65 per 100-share contract).
    strike_step
        Round strikes to a multiple of this (0 keeps exact strikes).
    """

    legs: tuple[LegTemplate, ...]
    tenor_days: int = 30
    vol_window: int = 21
    vol_premium: float = 0.0
    vol_floor: float = 0.05
    rate: float = 0.04
    dividend_yield: float = 0.0
    spread: float = 0.0
    commission: float = 0.0
    strike_step: float = 0.0

    def __post_init__(self) -> None:
        if not self.legs:
            raise ValueError("A strategy needs at least one leg.")
        if self.tenor_days < 1:
            raise ValueError("tenor_days must be at least 1.")
        if self.vol_window < 2:
            raise ValueError("vol_window must be at least 2.")
        if self.spread < 0 or self.commission < 0:
            raise ValueError("Costs cannot be negative.")


@dataclass(frozen=True)
class Cycle:
    """One roll: options opened on ``open_date`` and settled on ``expiry_date``."""

    open_date: pd.Timestamp
    expiry_date: pd.Timestamp
    spot_open: float
    spot_expiry: float
    sigma: float
    strikes: tuple[float, ...]
    premium: float  # net premium received (+) or paid (-), before costs
    costs: float
    payoff: float  # net option payoff at expiry
    pnl: float  # change in total portfolio value over the cycle


@dataclass(frozen=True)
class BacktestResult:
    """Daily values of the strategy and the buy-and-hold benchmark, plus the roll log."""

    dates: pd.DatetimeIndex
    value: np.ndarray
    benchmark: np.ndarray
    cycles: list[Cycle] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        """Share of cycles in which the portfolio gained value."""
        if not self.cycles:
            return float("nan")
        return float(np.mean([c.pnl > 0 for c in self.cycles]))

    @property
    def total_costs(self) -> float:
        return float(sum(c.costs for c in self.cycles))

    @property
    def total_premium(self) -> float:
        return float(sum(c.premium for c in self.cycles))

    def cycles_frame(self) -> pd.DataFrame:
        """The roll log as a table."""
        return pd.DataFrame([
            {
                "open": c.open_date.date(), "expiry": c.expiry_date.date(), "spot_open": c.spot_open,
                "spot_expiry": c.spot_expiry, "sigma": c.sigma, "strikes": " / ".join(f"{k:g}" for k in c.strikes),
                "premium": c.premium, "costs": c.costs, "payoff": c.payoff, "pnl": c.pnl,
            }
            for c in self.cycles
        ])


def performance(values: np.ndarray, dates: pd.DatetimeIndex, rate: float = 0.0) -> dict[str, float]:
    """Total and annualised return, volatility, Sharpe ratio and max drawdown of a value series.

    Annualisation uses the actual calendar span (``365.25`` days a year). Returns ``nan``
    for ratios that need a positive value series when the series touches zero.
    """
    v = np.asarray(values, dtype=float)
    years = max((dates[-1] - dates[0]).days / 365.25, 1e-9)
    out = {"total_return": float(v[-1] / v[0] - 1.0)}
    if np.all(v > 0):
        r = np.diff(np.log(v))
        per_year = len(r) / years
        sd = float(np.std(r, ddof=1)) if len(r) > 1 else float("nan")
        out["annual_return"] = float((v[-1] / v[0]) ** (1 / years) - 1.0)
        out["annual_volatility"] = sd * math.sqrt(per_year)
        out["sharpe"] = (float(np.mean(r)) * per_year - rate) / (sd * math.sqrt(per_year)) if sd > 0 else float("nan")
        out["max_drawdown"] = max_drawdown(v)
    else:
        out.update(annual_return=float("nan"), annual_volatility=float("nan"), sharpe=float("nan"),
                   max_drawdown=float("nan"))
    return out


def _round_strike(k: float, step: float) -> float:
    return round(k / step) * step if step > 0 else k


def run_backtest(
    dates: Sequence,
    prices: Sequence[float],
    config: BacktestConfig,
    dividends: Optional[Sequence[float]] = None,
    start: Optional[pd.Timestamp] = None,
    end: Optional[pd.Timestamp] = None,
) -> BacktestResult:
    """Run ``config`` over a daily price series.

    Parameters
    ----------
    dates, prices
        Trading dates and closing prices (split-adjusted, not dividend-adjusted), oldest first.
    dividends
        Cash dividend per share on each date (zeros if omitted).
    start, end
        Optional date range. The first ``vol_window`` days are always used to warm up the
        volatility estimate, so the backtest starts no earlier than that.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    p = np.asarray(prices, dtype=float)
    d = np.zeros_like(p) if dividends is None else np.asarray(dividends, dtype=float)
    if not (len(idx) == len(p) == len(d)):
        raise ValueError("dates, prices and dividends must have the same length.")
    hv = rolling_volatility(p, config.vol_window)

    first = config.vol_window
    if start is not None:
        first = max(first, int(idx.searchsorted(pd.Timestamp(start))))
    last = len(p) - 1 if end is None else min(len(p) - 1, int(idx.searchsorted(pd.Timestamp(end), side="right")) - 1)
    if last - first < 2:
        raise ValueError("Not enough data in the chosen range (the first days warm up the volatility estimate).")

    r, q = config.rate, config.dividend_yield
    stock_qty = sum(leg.quantity for leg in config.legs if leg.kind == "stock")
    option_legs = [leg for leg in config.legs if leg.kind != "stock"]

    s0 = p[first]
    cash = s0 - stock_qty * s0
    bench_cash = 0.0
    open_legs: list[tuple[str, float, float]] = []  # (kind, quantity, strike)
    expiry_i: Optional[int] = None
    sigma = float("nan")
    cycle_open: dict = {}

    values = np.empty(last - first + 1)
    bench = np.empty(last - first + 1)
    cycles: list[Cycle] = []

    # Mark-to-model values of the open options for every day of the current cycle,
    # computed in one vectorised call per leg when the cycle opens.
    path_value = np.empty(0)
    open_i = 0

    for j, i in enumerate(range(first, last + 1)):
        spot = p[i]
        if j > 0:
            growth = math.exp(r * (idx[i] - idx[i - 1]).days / 365.0)
            cash *= growth
            bench_cash *= growth
        cash += stock_qty * d[i]
        bench_cash += d[i]

        # Settle options expiring today.
        if open_legs and i >= expiry_i:
            payoff = float(sum(qty * max((spot - k) if kind == "call" else (k - spot), 0.0)
                               for kind, qty, k in open_legs))
            cash += payoff
            value_now = cash + stock_qty * spot
            cycles.append(Cycle(
                open_date=idx[cycle_open["i"]], expiry_date=idx[i], spot_open=cycle_open["spot"], spot_expiry=spot,
                sigma=cycle_open["sigma"], strikes=tuple(k for _, _, k in open_legs),
                premium=cycle_open["premium"], costs=cycle_open["costs"], payoff=payoff,
                pnl=value_now - cycle_open["value_before"],
            ))
            open_legs, expiry_i = [], None

        # Open the next cycle, if its expiry falls inside the data.
        if option_legs and not open_legs and i < last:
            target = idx[i] + pd.Timedelta(days=config.tenor_days)
            e = int(idx.searchsorted(target))
            if e <= last:
                value_before = cash + stock_qty * spot
                sigma = max(hv[i] * (1.0 + config.vol_premium), config.vol_floor)
                tau = (idx[e] - idx[i]).days / 365.0
                premium = costs = 0.0
                for leg in option_legs:
                    k = _round_strike(leg.moneyness * spot, config.strike_step)
                    price = float(black_scholes_price(spot, k, tau, r, sigma, q, leg.kind))
                    premium -= leg.quantity * price
                    costs += abs(leg.quantity) * (0.5 * config.spread * price + config.commission)
                    open_legs.append((leg.kind, leg.quantity, k))
                cash += premium - costs
                expiry_i, open_i = e, i
                taus = (idx[e] - idx[i:e + 1]).days.to_numpy(dtype=float) / 365.0
                path_value = np.zeros(e - i + 1)
                for kind, qty, k in open_legs:
                    path_value += qty * np.asarray(black_scholes_price(p[i:e + 1], k, taus, r, sigma, q, kind))
                cycle_open = dict(i=i, spot=spot, sigma=sigma, premium=premium, costs=costs, value_before=value_before)

        values[j] = cash + stock_qty * spot + (path_value[i - open_i] if open_legs else 0.0)
        bench[j] = spot + bench_cash

    return BacktestResult(idx[first:last + 1], values, bench, cycles)


# ---------------------------------------------------------------------------
# Strategy templates
# ---------------------------------------------------------------------------

TEMPLATE_NAMES = (
    "buy_and_hold", "covered_call", "protective_put", "collar", "cash_secured_put",
    "long_straddle", "long_strangle", "bull_call_spread", "bear_put_spread", "iron_condor",
)


def template_legs(name: str, otm_call: float = 0.05, otm_put: float = 0.05, wing: float = 0.05) -> tuple[LegTemplate, ...]:
    """Legs of a named strategy. ``otm_*`` and ``wing`` are fractions of spot (0.05 = 5%)."""
    up, down = 1.0 + otm_call, 1.0 - otm_put
    legs = {
        "buy_and_hold": [LegTemplate("stock", 1)],
        "covered_call": [LegTemplate("stock", 1), LegTemplate("call", -1, up)],
        "protective_put": [LegTemplate("stock", 1), LegTemplate("put", 1, down)],
        "collar": [LegTemplate("stock", 1), LegTemplate("put", 1, down), LegTemplate("call", -1, up)],
        "cash_secured_put": [LegTemplate("put", -1, down)],
        "long_straddle": [LegTemplate("call", 1, 1.0), LegTemplate("put", 1, 1.0)],
        "long_strangle": [LegTemplate("call", 1, up), LegTemplate("put", 1, down)],
        "bull_call_spread": [LegTemplate("call", 1, 1.0), LegTemplate("call", -1, up)],
        "bear_put_spread": [LegTemplate("put", 1, 1.0), LegTemplate("put", -1, down)],
        "iron_condor": [LegTemplate("put", 1, down - wing), LegTemplate("put", -1, down),
                        LegTemplate("call", -1, up), LegTemplate("call", 1, up + wing)],
    }
    if name not in legs:
        raise ValueError(f"Unknown strategy '{name}'.")
    return tuple(legs[name])


# ---------------------------------------------------------------------------
# Custom strategies
# ---------------------------------------------------------------------------

MAX_LEGS = 8
MAX_QUANTITY = 10.0
_KIND_CODE = {"stock": "s", "call": "c", "put": "p"}
_CODE_KIND = {v: k for k, v in _KIND_CODE.items()}


def legs_to_code(legs: Sequence[LegTemplate]) -> str:
    """A short text form of ``legs`` for links, e.g. ``"s+1,c-1@105"`` (strike as % of spot)."""
    parts = []
    for leg in legs:
        code = f"{_KIND_CODE[leg.kind]}{leg.quantity:+g}"
        if leg.kind != "stock":
            code += f"@{round(100 * leg.moneyness, 4):g}"
        parts.append(code)
    return ",".join(parts)


def legs_from_code(code: str) -> tuple[LegTemplate, ...]:
    """Parse :func:`legs_to_code` output, rejecting anything malformed or out of range."""
    legs = []
    for part in str(code).replace(" ", "").split(","):
        if not part:
            continue
        kind = _CODE_KIND.get(part[0])
        if kind is None:
            raise ValueError(f"Unknown leg type in '{part}'.")
        body, _, strike = part[1:].partition("@")
        qty = float(body)
        if not (0 < abs(qty) <= MAX_QUANTITY) or not math.isfinite(qty):
            raise ValueError(f"Quantity out of range in '{part}'.")
        if kind == "stock":
            if strike:
                raise ValueError("Share legs have no strike.")
            legs.append(LegTemplate("stock", qty))
        else:
            m = float(strike) / 100
            if not (0.01 <= m <= 5.0):
                raise ValueError(f"Strike out of range in '{part}'.")
            legs.append(LegTemplate(kind, qty, m))
    if not legs:
        raise ValueError("A strategy needs at least one leg.")
    if len(legs) > MAX_LEGS:
        raise ValueError(f"At most {MAX_LEGS} legs.")
    return tuple(legs)


def upside_exposure(legs: Sequence[LegTemplate]) -> float:
    """Shares-equivalent exposure once every call is deep in the money; negative means losses
    grow without limit as the stock rallies."""
    return float(sum(leg.quantity for leg in legs if leg.kind in ("stock", "call")))


def cycle_payoff(
    legs: Sequence[LegTemplate],
    terminal: Sequence[float],
    tenor_days: int,
    rate: float,
    sigma: float,
    dividend_yield: float = 0.0,
    spot: float = 100.0,
) -> np.ndarray:
    """P&L per share of one cycle opened at ``spot`` and held to expiry, before costs and interest.

    Options are bought or sold at their Black-Scholes price on opening, exactly as the
    backtest prices them, and settle at intrinsic value at each terminal price.
    """
    s_t = np.asarray(terminal, dtype=float)
    tau = tenor_days / 365.0
    pnl = np.zeros_like(s_t)
    for leg in legs:
        if leg.kind == "stock":
            pnl += leg.quantity * (s_t - spot)
            continue
        k = leg.moneyness * spot
        price = float(black_scholes_price(spot, k, tau, rate, sigma, dividend_yield, leg.kind))
        intrinsic = np.maximum(s_t - k, 0.0) if leg.kind == "call" else np.maximum(k - s_t, 0.0)
        pnl += leg.quantity * (intrinsic - price)
    return pnl
