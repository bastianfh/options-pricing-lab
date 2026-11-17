"""Download US stock data from Yahoo Finance via ``yfinance``.

Yahoo's endpoints are free but unofficial and rate-limited, so every function raises
:class:`~marketdata.parse.MarketDataError` with a plain message on failure, and the app
offers CSV upload as a fallback. Results are cached by the caller (``st.cache_data``).
Data is for personal research and education (Yahoo's terms).
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Optional

import pandas as pd

from marketdata.parse import MarketDataError, PriceHistory, history_from_frame

PERIODS = {"6mo": "6 months", "1y": "1 year", "2y": "2 years", "5y": "5 years", "10y": "10 years"}
_TICKER = re.compile(r"^\^?[A-Z][A-Z0-9.\-]{0,9}$")


def normalize_ticker(raw: str) -> str:
    """Upper-case and Yahoo-ise a ticker (``brk.b`` -> ``BRK-B``); raise for anything not ticker-like."""
    ticker = (raw or "").strip().upper().replace(" ", "")
    if not _TICKER.match(ticker):
        raise MarketDataError(f"'{raw}' doesn't look like a ticker. Try something like AAPL, MSFT or BRK-B.")
    if "." in ticker and not ticker.startswith("^"):
        ticker = ticker.replace(".", "-")
    return ticker


def _yf():
    try:
        import yfinance  # imported lazily so the rest of the app works without it
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise MarketDataError("Live data needs the 'yfinance' package (pip install yfinance).") from exc
    return yfinance


def fetch_history(ticker: str, period: str = "2y") -> PriceHistory:
    """Daily prices (unadjusted and adjusted) and dividends for ``ticker``."""
    ticker = normalize_ticker(ticker)
    if period not in PERIODS:
        raise MarketDataError(f"Unknown period '{period}'.")
    try:
        frame = _yf().Ticker(ticker).history(period=period, interval="1d", auto_adjust=False, actions=True)
    except Exception as exc:
        raise MarketDataError(
            f"Couldn't reach Yahoo Finance for {ticker} right now. Try again in a minute, or upload a CSV instead."
        ) from exc
    if frame is None or frame.empty:
        raise MarketDataError(f"No price data found for '{ticker}'. Check the ticker, or upload a CSV instead.")
    return history_from_frame(frame, label=ticker, source="Yahoo Finance")


def fetch_expiries(ticker: str) -> list[str]:
    """Listed option expiry dates (``YYYY-MM-DD``); empty if the stock has no listed options."""
    ticker = normalize_ticker(ticker)
    try:
        return list(_yf().Ticker(ticker).options)
    except Exception as exc:
        raise MarketDataError(f"Couldn't load option expiries for {ticker} right now.") from exc


def fetch_chain(ticker: str, expiry: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Raw calls and puts for one expiry."""
    ticker = normalize_ticker(ticker)
    try:
        chain = _yf().Ticker(ticker).option_chain(expiry)
    except Exception as exc:
        raise MarketDataError(f"Couldn't load the {expiry} option chain for {ticker} right now.") from exc
    return chain.calls, chain.puts


def fetch_risk_free() -> Optional[float]:
    """Current 13-week US T-bill yield as a continuously compounded rate, or ``None`` if unavailable.

    Yahoo's ``^IRX`` is quoted in percent; :math:`r = \\ln(1 + y)` converts the
    annual yield to the continuous rate the models use.
    """
    try:
        frame = _yf().Ticker("^IRX").history(period="5d")
        y = float(frame["Close"].dropna().iloc[-1]) / 100.0
    except Exception:
        return None
    if not math.isfinite(y) or y < -0.05 or y > 0.5:
        return None
    return math.log1p(y)


def expiry_date(expiry: str) -> date:
    return date.fromisoformat(expiry)
