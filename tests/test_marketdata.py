"""Market data parsing and fetching, tested offline with fixtures and a fake yfinance."""

from __future__ import annotations

import math
import sys
import types
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from marketdata import fetch
from marketdata.parse import (
    MarketDataError,
    atm_implied_vol,
    clean_chain,
    history_from_frame,
    parse_price_csv,
    quotes_for_surface,
    surface_from_chains,
)
from pricing.models.black_scholes import black_scholes_price


def business_days(n: int, end: str = "2026-11-16") -> pd.DatetimeIndex:
    return pd.bdate_range(end=end, periods=n)


def price_series(n: int = 300, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 100 * np.exp(np.cumsum(0.015 * rng.standard_normal(n)))


# --------------------------------------------------------------------------- CSV formats

def test_yahoo_csv_uses_adjusted_close_for_returns_and_close_for_spot() -> None:
    d = business_days(60)
    close = np.linspace(100, 130, 60)
    csv = pd.DataFrame({"Date": d.strftime("%Y-%m-%d"), "Open": close, "High": close, "Low": close,
                        "Close": close, "Adj Close": close * 0.98, "Volume": 1000}).to_csv(index=False)
    h = parse_price_csv(csv.encode(), "aapl.csv")
    assert h.last_price == pytest.approx(130.0)
    assert h.adj_close[-1] == pytest.approx(130.0 * 0.98)
    assert h.last_date == date(2026, 11, 16) and h.source == "Uploaded CSV"


def test_nasdaq_csv_with_dollar_signs_newest_first() -> None:
    d = business_days(40)[::-1]  # Nasdaq exports newest first, MM/DD/YYYY
    close = np.linspace(200, 180, 40)
    csv = pd.DataFrame({"Date": d.strftime("%m/%d/%Y"), "Close/Last": [f"${c:,.2f}" for c in close],
                        "Volume": 5, "Open": "$1.00", "High": "$1.00", "Low": "$1.00"}).to_csv(index=False)
    h = parse_price_csv(csv.encode(), "msft.csv")
    assert h.dates.is_monotonic_increasing
    assert h.last_price == pytest.approx(200.0)  # first row of the file = most recent


def test_generic_two_column_csv_and_dividends_column() -> None:
    d = business_days(320)  # about 15 months
    close = np.full(320, 50.0)
    divs = np.zeros(320)
    divs[[10, 100, 160, 220, 290]] = 0.25  # five payments; the first is ~16 months old
    csv = pd.DataFrame({"date": d.strftime("%Y-%m-%d"), "price": close, "Dividends": divs}).to_csv(index=False)
    h = parse_price_csv(csv.encode(), "x.csv")
    assert h.dividend_yield == pytest.approx(4 * 0.25 / 50.0)


@pytest.mark.parametrize(
    "content",
    [b"", b"not,a,price\n1,2,3\n", b"Date,Close\n2026-01-01,100\n2026-01-02,101\n", b"\x00\x01garbage"],
)
def test_bad_csvs_raise_friendly_errors(content: bytes) -> None:
    with pytest.raises(MarketDataError):
        parse_price_csv(content, "bad.csv")


def test_history_from_yfinance_style_frame_with_timezone_index() -> None:
    d = pd.date_range(end="2026-11-16", periods=50, freq="B", tz="America/New_York")
    frame = pd.DataFrame({"Close": np.linspace(10, 20, 50), "Adj Close": np.linspace(9, 19, 50),
                          "Dividends": 0.0, "Stock Splits": 0.0}, index=d.rename("Date"))
    h = history_from_frame(frame, "XYZ", "Yahoo Finance")
    assert h.dates.tz is None and len(h.dates) == 50 and h.last_price == pytest.approx(20.0)


# --------------------------------------------------------------------------- option chains

def synthetic_chain(spot: float, sigma: float, years: float, r: float, q: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    strikes = np.arange(50, 151, 5.0)
    frames = []
    for kind in ("call", "put"):
        px = black_scholes_price(spot, strikes, years, r, sigma, q, kind)
        frames.append(pd.DataFrame({
            "strike": strikes, "bid": px * 0.99, "ask": px * 1.01, "lastPrice": px,
            "volume": 10.0, "openInterest": 100.0, "impliedVolatility": sigma,
        }))
    return frames[0], frames[1]


def test_clean_chain_recovers_volatility_and_keeps_out_of_the_money_only() -> None:
    today, expiry = date(2026, 11, 16), date(2026, 11, 16) + timedelta(days=91)
    calls, puts = synthetic_chain(100.0, 0.25, 91 / 365, 0.04, 0.01)
    ch = clean_chain(calls, puts, 100.0, expiry, today, 0.04, 0.01)
    forward = 100 * math.exp((0.04 - 0.01) * 91 / 365)
    assert set(ch["type"]) == {"call", "put"}
    assert (ch.loc[ch["type"] == "put", "strike"] < forward).all()
    assert (ch.loc[ch["type"] == "call", "strike"] >= forward).all()
    # mid of a symmetric 1% market reproduces the model price exactly, so IV is recovered.
    meaningful = ch["price"] > 1e-3
    np.testing.assert_allclose(ch.loc[meaningful, "iv"], 0.25, rtol=1e-6)
    assert atm_implied_vol(ch, 100.0) == pytest.approx(0.25, rel=1e-6)


def test_clean_chain_falls_back_to_last_trade_and_drops_unusable_quotes() -> None:
    today, expiry = date(2026, 11, 16), date(2026, 12, 18)
    calls = pd.DataFrame({"strike": [110.0, 120.0, 130.0], "bid": [0.0, 1.0, 0.0], "ask": [0.0, 1.2, 0.0],
                          "lastPrice": [2.0, 1.1, 0.0], "volume": [1, 1, 0], "openInterest": [1, 1, 0],
                          "impliedVolatility": [0.3, 0.3, 0.3]})
    ch = clean_chain(calls, pd.DataFrame(), 100.0, expiry, today, 0.04, 0.0)
    assert list(ch["strike"]) == [110.0, 120.0]          # 130 has no price at all
    assert ch.loc[0, "price"] == 2.0                      # no two-sided quote -> last trade
    assert ch.loc[1, "price"] == pytest.approx(1.1)       # mid of 1.0 / 1.2


def test_expired_chain_is_empty_and_quotes_table_shape() -> None:
    calls, puts = synthetic_chain(100.0, 0.2, 0.1, 0.0, 0.0)
    assert clean_chain(calls, puts, 100.0, date(2026, 1, 1), date(2026, 1, 1), 0.0, 0.0).empty
    ch = clean_chain(calls, puts, 100.0, date(2026, 3, 1), date(2026, 1, 1), 0.0, 0.0)
    table = quotes_for_surface([ch, ch.iloc[0:0]])
    assert list(table.columns) == ["strike", "expiry", "price", "type"] and len(table) == len(ch)


def test_surface_from_chains_interpolates_within_quoted_strikes_only() -> None:
    today = date(2026, 11, 16)
    chains = []
    for days, sigma in ((30, 0.30), (90, 0.25)):
        calls, puts = synthetic_chain(100.0, sigma, days / 365, 0.03, 0.0)
        chains.append(clean_chain(calls, puts, 100.0, today + timedelta(days=days), today, 0.03, 0.0))
    quotes = pd.concat(chains)
    surface = surface_from_chains(quotes[quotes["strike"] <= 115], 100.0, 0.03, 0.0)
    assert surface.vols.shape == (2, 25)
    np.testing.assert_allclose(surface.expiries, [30 / 365, 90 / 365])
    quoted = surface.strikes <= 115
    np.testing.assert_allclose(surface.vols[0, quoted], 0.30, rtol=1e-5)  # flat smile recovered
    assert np.isnan(surface.vols[:, ~quoted]).all()                        # no extrapolation past 115
    assert np.isfinite(surface.prices[:, quoted]).all()


# --------------------------------------------------------------------------- fetching (fake yfinance)

class FakeTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, period: str = "1y", **_: object) -> pd.DataFrame:
        if self.symbol == "BOOM":
            raise ConnectionError("network down")
        if self.symbol == "NOPE":
            return pd.DataFrame()
        if self.symbol == "^IRX":
            return pd.DataFrame({"Close": [4.10, 4.125]})
        idx = pd.date_range(end="2026-11-16", periods=120, freq="B", tz="America/New_York")
        p = price_series(120)
        return pd.DataFrame({"Close": p, "Adj Close": p, "Dividends": 0.0}, index=idx)

    @property
    def options(self) -> tuple[str, ...]:
        return ("2026-12-18", "2027-01-15")

    def option_chain(self, expiry: str) -> types.SimpleNamespace:
        calls, puts = synthetic_chain(100.0, 0.3, 0.1, 0.0, 0.0)
        return types.SimpleNamespace(calls=calls, puts=puts)


@pytest.fixture
def fake_yfinance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker))


@pytest.mark.parametrize("raw,expected", [("aapl", "AAPL"), (" brk.b ", "BRK-B"), ("^GSPC", "^GSPC")])
def test_normalize_ticker(raw: str, expected: str) -> None:
    assert fetch.normalize_ticker(raw) == expected


@pytest.mark.parametrize("raw", ["", "123", "AAPL; DROP", "WAYTOOLONGTICKER"])
def test_normalize_ticker_rejects_non_tickers(raw: str) -> None:
    with pytest.raises(MarketDataError):
        fetch.normalize_ticker(raw)


def test_fetch_history_success_and_errors(fake_yfinance: None) -> None:
    h = fetch.fetch_history("msft", "1y")
    assert h.label == "MSFT" and h.source == "Yahoo Finance" and len(h.dates) == 120
    with pytest.raises(MarketDataError, match="No price data"):
        fetch.fetch_history("NOPE")
    with pytest.raises(MarketDataError, match="Couldn't reach"):
        fetch.fetch_history("BOOM")
    with pytest.raises(MarketDataError):
        fetch.fetch_history("MSFT", period="3d")


def test_fetch_chain_expiries_and_risk_free(fake_yfinance: None) -> None:
    assert fetch.fetch_expiries("AAPL") == ["2026-12-18", "2027-01-15"]
    calls, puts = fetch.fetch_chain("AAPL", "2026-12-18")
    assert len(calls) == len(puts) > 0
    assert fetch.fetch_risk_free() == pytest.approx(math.log1p(0.04125))
