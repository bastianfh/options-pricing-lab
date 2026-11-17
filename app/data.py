"""Cached access to market data, shared by the Market, Backtest and Payoff tools.

Network calls go through :mod:`marketdata.fetch` *by module attribute* (``fetch.fetch_history``),
so tests can swap in a fake data source.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from marketdata import fetch
from marketdata.parse import PriceHistory

POPULAR = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "V", "JNJ", "XOM", "KO", "SPY", "QQQ"]
FALLBACK_RATE = 0.04


@st.cache_data(ttl=900, show_spinner=False, max_entries=32)
def load_history(ticker: str, period: str) -> PriceHistory:
    return fetch.fetch_history(ticker, period)


@st.cache_data(ttl=900, show_spinner=False, max_entries=32)
def load_expiries(ticker: str) -> list[str]:
    return fetch.fetch_expiries(ticker)


@st.cache_data(ttl=600, show_spinner=False, max_entries=64)
def load_chain(ticker: str, expiry: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return fetch.fetch_chain(ticker, expiry)


@st.cache_data(ttl=3600, show_spinner=False)
def load_risk_free() -> float | None:
    return fetch.fetch_risk_free()


def dividends_on_dates(hist: PriceHistory) -> pd.Series:
    """Cash dividends aligned to the history's trading dates (zeros elsewhere)."""
    series = pd.Series(0.0, index=hist.dates)
    for d, amount in zip(hist.dividend_dates, hist.dividend_amounts):
        pos = hist.dates.searchsorted(d)
        if pos < len(series):
            series.iloc[pos] += float(amount)
    return series
