"""Multi-leg option strategies: payoff at expiry, value and P&L before expiry, and risk metrics.

A strategy is a list of :class:`Leg` objects that share one underlying and one
expiry. Before expiry each option leg is valued with Black-Scholes-Merton;
stock legs are worth the spot. P&L is measured against the cost of setting up
the position at today's model prices (ignoring financing and transaction
costs).

The presets follow the standard definitions in Hull, ch. 12.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Sequence

import numpy as np

from pricing.greeks import Greeks, black_scholes_greeks
from pricing.models.black_scholes import black_scholes_price

LegKind = Literal["call", "put", "stock"]


@dataclass(frozen=True)
class Leg:
    """One position in a strategy.

    Attributes
    ----------
    kind
        ``"call"``, ``"put"`` or ``"stock"``.
    quantity
        Signed number of units: positive for long, negative for short.
    strike
        Option strike (ignored for stock).
    """

    kind: LegKind
    quantity: float
    strike: float = 0.0

    def payoff(self, S_T: np.ndarray) -> np.ndarray:
        """Value of the leg at expiry for terminal prices ``S_T``."""
        S_T = np.asarray(S_T, dtype=float)
        if self.kind == "stock":
            return self.quantity * S_T
        if self.kind == "call":
            return self.quantity * np.maximum(S_T - self.strike, 0.0)
        return self.quantity * np.maximum(self.strike - S_T, 0.0)

    def value(self, S: np.ndarray, T: float, r: float, sigma: float, q: float = 0.0) -> np.ndarray:
        """Model value of the leg with ``T`` years to expiry (payoff if ``T == 0``)."""
        S = np.asarray(S, dtype=float)
        if self.kind == "stock":
            return self.quantity * S
        return self.quantity * np.asarray(black_scholes_price(S, self.strike, T, r, sigma, q, self.kind))

    def greeks(self, S: float, T: float, r: float, sigma: float, q: float = 0.0) -> Greeks:
        """Black-Scholes Greeks of the leg, scaled by quantity (stock: delta = quantity)."""
        if self.kind == "stock":
            return Greeks(self.quantity, 0.0, 0.0, 0.0, 0.0)
        g = black_scholes_greeks(S, self.strike, T, r, sigma, q, self.kind)
        return Greeks(*(self.quantity * v for v in (g.delta, g.gamma, g.vega, g.theta, g.rho)))


@dataclass(frozen=True)
class Strategy:
    """A named collection of legs with a common expiry."""

    name: str
    legs: tuple[Leg, ...]

    def payoff(self, S_T: np.ndarray) -> np.ndarray:
        """Total payoff at expiry."""
        return sum((leg.payoff(S_T) for leg in self.legs), start=np.zeros_like(np.asarray(S_T, dtype=float)))

    def value(self, S: np.ndarray, T: float, r: float, sigma: float, q: float = 0.0) -> np.ndarray:
        """Total model value with ``T`` years remaining."""
        S = np.asarray(S, dtype=float)
        return sum((leg.value(S, T, r, sigma, q) for leg in self.legs), start=np.zeros_like(S))

    def cost(self, S0: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Cost of entering the position today (negative means a net credit)."""
        return float(self.value(np.array(S0), T, r, sigma, q))

    def pnl_at_expiry(self, S_T: np.ndarray, entry_cost: float) -> np.ndarray:
        """P&L at expiry: payoff minus entry cost."""
        return self.payoff(S_T) - entry_cost

    def pnl_before_expiry(
        self, S: np.ndarray, T_remaining: float, r: float, sigma: float, entry_cost: float, q: float = 0.0
    ) -> np.ndarray:
        """Mark-to-model P&L with ``T_remaining`` years left, relative to ``entry_cost``."""
        return self.value(S, T_remaining, r, sigma, q) - entry_cost

    def greeks(self, S: float, T: float, r: float, sigma: float, q: float = 0.0) -> Greeks:
        """Position Greeks: the sum of each leg's Greeks."""
        totals = np.zeros(5)
        for leg in self.legs:
            g = leg.greeks(S, T, r, sigma, q)
            totals += [g.delta, g.gamma, g.vega, g.theta, g.rho]
        return Greeks(*(float(x) for x in totals))


def breakevens(S_grid: np.ndarray, pnl: np.ndarray) -> list[float]:
    """Prices where P&L crosses zero, by linear interpolation between grid points."""
    S_grid, pnl = np.asarray(S_grid, dtype=float), np.asarray(pnl, dtype=float)
    out: list[float] = []
    sign = np.sign(pnl)
    for i in np.nonzero(sign[:-1] * sign[1:] < 0)[0]:
        x0, x1, y0, y1 = S_grid[i], S_grid[i + 1], pnl[i], pnl[i + 1]
        out.append(float(x0 - y0 * (x1 - x0) / (y1 - y0)))
    out.extend(float(S_grid[i]) for i in np.nonzero(pnl == 0)[0] if 0 < i < len(pnl) - 1)
    return sorted(out)


@dataclass(frozen=True)
class RiskSummary:
    """Max profit / loss at expiry. ``None`` means unbounded as the price rises."""

    max_profit: float | None
    max_loss: float | None
    breakevens: list[float]


def risk_summary(strategy: Strategy, entry_cost: float, S_grid: np.ndarray) -> RiskSummary:
    """Max profit, max loss and breakevens of the expiry P&L.

    Option payoffs are piecewise linear, so beyond the largest strike the P&L
    grows without bound exactly when the total slope (net long calls + stock)
    is positive (profit) or negative (loss). Below the smallest strike the
    payoff is bounded because prices cannot go below zero, so we evaluate
    ``S_T = 0`` explicitly.
    """
    grid = np.unique(np.concatenate([[0.0], np.asarray(S_grid, dtype=float), [leg.strike for leg in strategy.legs]]))
    pnl = strategy.pnl_at_expiry(grid, entry_cost)
    upside_slope = sum(leg.quantity for leg in strategy.legs if leg.kind in ("call", "stock"))
    max_profit = None if upside_slope > 1e-12 else float(pnl.max())
    max_loss = None if upside_slope < -1e-12 else float(pnl.min())
    return RiskSummary(max_profit, max_loss, breakevens(grid, pnl))


# ---------------------------------------------------------------------------
# Presets (Hull, ch. 12). K is the central strike; width sets the wings.
# ---------------------------------------------------------------------------

def long_call(K: float, width: float = 0.0) -> Strategy:
    return Strategy("Long call", (Leg("call", 1, K),))


def long_put(K: float, width: float = 0.0) -> Strategy:
    return Strategy("Long put", (Leg("put", 1, K),))


def straddle(K: float, width: float = 0.0) -> Strategy:
    """Long a call and a put at the same strike: profits from a large move either way."""
    return Strategy("Long straddle", (Leg("call", 1, K), Leg("put", 1, K)))


def strangle(K: float, width: float) -> Strategy:
    """Long an OTM put at ``K - width`` and an OTM call at ``K + width``: a cheaper straddle."""
    return Strategy("Long strangle", (Leg("put", 1, K - width), Leg("call", 1, K + width)))


def bull_call_spread(K: float, width: float) -> Strategy:
    """Long a call at ``K - width``, short a call at ``K + width``: capped upside, capped cost."""
    return Strategy("Bull call spread", (Leg("call", 1, K - width), Leg("call", -1, K + width)))


def bear_put_spread(K: float, width: float) -> Strategy:
    """Long a put at ``K + width``, short a put at ``K - width``."""
    return Strategy("Bear put spread", (Leg("put", 1, K + width), Leg("put", -1, K - width)))


def covered_call(K: float, width: float = 0.0) -> Strategy:
    """Long the asset, short a call at ``K``: earn premium, give up upside."""
    return Strategy("Covered call", (Leg("stock", 1), Leg("call", -1, K)))


def protective_put(K: float, width: float = 0.0) -> Strategy:
    """Long the asset and a put at ``K``: insurance against a fall."""
    return Strategy("Protective put", (Leg("stock", 1), Leg("put", 1, K)))


PRESETS: dict[str, Callable[[float, float], Strategy]] = {
    "long_call": long_call,
    "long_put": long_put,
    "straddle": straddle,
    "strangle": strangle,
    "bull_call_spread": bull_call_spread,
    "bear_put_spread": bear_put_spread,
    "covered_call": covered_call,
    "protective_put": protective_put,
}
"""Preset builders keyed by identifier; each takes ``(K, width)``."""


def from_legs(name: str, legs: Sequence[Leg]) -> Strategy:
    """Build a custom strategy, dropping zero-quantity legs."""
    return Strategy(name, tuple(leg for leg in legs if leg.quantity != 0))
