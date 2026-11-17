"""Parse and clean market data: price histories (CSV or Yahoo Finance) and option chains.

Nothing here touches the network, so every function can be tested with fixtures.

File formats accepted
---------------------
CSV (``.csv``) and Excel (``.xlsx``, ``.xlsm``, ``.xls``) files with a date column and a
price column. Recognised layouts include:

* Yahoo Finance download: ``Date, Open, High, Low, Close, Adj Close, Volume``
* Nasdaq.com historical data: ``Date, Close/Last, Volume, Open, High, Low`` (prices like ``$187.44``)
* Stooq: ``Date, Open, High, Low, Close, Volume``
* FactSet and other Excel exports: a title block above the table is skipped automatically,
  the first sheet that contains prices is used, and dates stored as Excel serial numbers work
* Anything simple: ``date, close`` or ``Date, Price``, with or without a header row

An optional ``Dividends`` column (cash per share on payment dates) is used for the
dividend yield. Adjusted close, when present, is used for returns and volatility so
that splits and dividends do not show up as fake price jumps; the unadjusted close is
used as today's spot price.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from pricing.historical import trailing_dividend_yield
from pricing.implied_vol import VolSurface, implied_volatility, otm_option_types
from pricing.models.black_scholes import black_scholes_price

MIN_ROWS = 30


class MarketDataError(ValueError):
    """Data could not be loaded or understood. The message is written for the end user."""


@dataclass(frozen=True)
class PriceHistory:
    """A daily price history for one instrument, oldest first.

    Attributes
    ----------
    label
        Ticker or file name shown to the user.
    source
        Where the data came from (e.g. ``"Yahoo Finance"``, ``"Uploaded CSV"``).
    dates
        Trading dates (timezone-naive).
    close
        Unadjusted closing prices: the last one is today's spot.
    adj_close
        Prices adjusted for splits and dividends, used for returns and volatility.
    dividend_dates, dividend_amounts
        Cash dividends per share and their payment dates (possibly empty).
    """

    label: str
    source: str
    dates: pd.DatetimeIndex
    close: np.ndarray
    adj_close: np.ndarray
    dividend_dates: pd.DatetimeIndex = field(default_factory=lambda: pd.DatetimeIndex([]))
    dividend_amounts: np.ndarray = field(default_factory=lambda: np.empty(0))

    def __post_init__(self) -> None:
        n = len(self.dates)
        if n < MIN_ROWS:
            raise MarketDataError(f"Need at least {MIN_ROWS} days of prices; found {n}.")
        if len(self.close) != n or len(self.adj_close) != n:
            raise MarketDataError("Dates and prices have different lengths.")

    @property
    def last_price(self) -> float:
        return float(self.close[-1])

    @property
    def last_date(self) -> date:
        return self.dates[-1].date()

    @property
    def dividend_yield(self) -> float:
        """Trailing 12-month dividend yield (continuous ``q`` estimate)."""
        if len(self.dividend_amounts) == 0:
            return 0.0
        ages = (self.dates[-1] - self.dividend_dates).days.to_numpy(dtype=float)
        return trailing_dividend_yield(self.dividend_amounts, ages, self.last_price)

    def window(self, days: int) -> np.ndarray:
        """Adjusted prices covering roughly the last ``days`` calendar days."""
        cutoff = self.dates[-1] - pd.Timedelta(days=days)
        return self.adj_close[self.dates >= cutoff]


# ---------------------------------------------------------------------------
# Price histories
# ---------------------------------------------------------------------------

# Header names are compared after normalising (lower case, punctuation and repeated spaces removed),
# so "Close*", "Adj. Close" and "PX_LAST" all match.
_DATE_NAMES = ("date", "datetime", "timestamp", "time", "day", "trade date", "as of date", "pricing date")
_CLOSE_NAMES = ("close/last", "close", "closing price", "close price", "price close", "last price", "price",
                "last", "pxlast", "adj close", "adjusted close", "adjclose")
_ADJ_NAMES = ("adj close", "adjusted close", "adjclose", "adj close price", "adjusted closing price")
_DIV_NAMES = ("dividends", "dividend", "dividend amount", "dividends per share")
_NOT_CLOSE = ("open", "high", "low", "change", "target", "volume", "bid", "ask")


def _norm(name: object) -> str:
    """Normalise a column header for matching."""
    import re

    text = re.sub(r"[^a-z0-9/ ]", "", str(name).lower().replace("_", " "))
    return " ".join(text.split())


def _to_number(series: pd.Series) -> pd.Series:
    """Parse prices that may contain currency symbols or thousands separators."""
    if series.dtype.kind in "if":
        return series.astype(float)
    cleaned = series.astype(str).str.replace(r"[$,\s]", "", regex=True).replace({"": np.nan, "null": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def _find(columns: dict[str, str], names: tuple[str, ...]) -> Optional[str]:
    for name in names:
        if name in columns:
            return columns[name]
    return None


def _find_close(columns: dict[str, str]) -> Optional[str]:
    """The closing-price column: an exact known name, else any header mentioning close or price."""
    exact = _find(columns, _CLOSE_NAMES)
    if exact is not None:
        return exact
    for key, col in columns.items():
        if ("close" in key or "price" in key) and not any(word in key for word in _NOT_CLOSE):
            return col
    return None


def _to_dates(series: pd.Series) -> pd.Series:
    """Parse dates, including Excel serial day numbers (e.g. 45610 = 2024-11-14)."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() > 0.8 and numeric.dropna().between(20000, 80000).all():
        return pd.to_datetime(numeric, unit="D", origin="1899-12-30", utc=True)
    return pd.to_datetime(series, errors="coerce", utc=True, format="mixed")


def history_from_frame(
    frame: pd.DataFrame,
    label: str,
    source: str,
    *,
    date_col: Optional[str] = None,
) -> PriceHistory:
    """Build a :class:`PriceHistory` from any frame with a date and a close column.

    The date can be a column or the index (as in ``yfinance`` output).
    """
    df = frame.copy()
    if date_col is None and isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
    cols = {_norm(c): c for c in df.columns}
    dcol = date_col or _find(cols, _DATE_NAMES) or (df.columns[0] if len(df.columns) else None)
    ccol = _find_close(cols)
    if dcol is None or ccol is None:
        raise MarketDataError(
            "Could not find a date column and a closing-price column. "
            "Expected headers like 'Date' and 'Close' (or 'Close/Last', 'Price')."
        )
    acol = _find(cols, _ADJ_NAMES)
    if acol == ccol:
        acol = None
    divcol = _find(cols, _DIV_NAMES)

    dates = _to_dates(df[dcol])
    out = pd.DataFrame({
        "date": dates.dt.tz_convert(None).dt.normalize(),
        "close": _to_number(df[ccol]),
        "adj": _to_number(df[acol]) if acol else np.nan,
        "div": _to_number(df[divcol]) if divcol else 0.0,
    })
    out = out.dropna(subset=["date", "close"])
    out = out[out["close"] > 0].sort_values("date").drop_duplicates("date", keep="last")
    if out["adj"].isna().all():
        out["adj"] = out["close"]
    out["adj"] = out["adj"].fillna(out["close"])
    if len(out) < MIN_ROWS:
        raise MarketDataError(f"Need at least {MIN_ROWS} days of prices; found {len(out)} usable rows.")

    divs = out[out["div"].fillna(0) > 0]
    return PriceHistory(
        label=label,
        source=source,
        dates=pd.DatetimeIndex(out["date"]),
        close=out["close"].to_numpy(dtype=float),
        adj_close=out["adj"].to_numpy(dtype=float),
        dividend_dates=pd.DatetimeIndex(divs["date"]),
        dividend_amounts=divs["div"].to_numpy(dtype=float),
    )


def parse_price_csv(data: bytes, label: str) -> PriceHistory:
    """Parse an uploaded CSV of daily prices (see module docstring for accepted layouts)."""
    try:
        frame = pd.read_csv(io.BytesIO(data))
    except Exception as exc:  # pandas raises several types for malformed files
        raise MarketDataError("That file isn't a readable CSV.") from exc
    if frame.empty:
        raise MarketDataError("That CSV has no rows.")
    return history_from_frame(frame, label=label, source="Uploaded CSV")


EXCEL_TYPES = ("xlsx", "xlsm", "xls")
UPLOAD_TYPES = ("csv", *EXCEL_TYPES)


def _mostly_dates(values: pd.Series) -> bool:
    v = values.dropna()
    return len(v) >= MIN_ROWS and _to_dates(v).notna().mean() >= 0.8


def _mostly_numbers(values: pd.Series) -> bool:
    v = values.dropna()
    return len(v) >= MIN_ROWS and _to_number(v).notna().mean() >= 0.8


def _table_from_sheet(raw: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Locate the price table on a sheet read with ``header=None``.

    Looks in the first 50 rows for a header row with a price-like name (and ideally a date-like
    name), which skips title blocks such as FactSet's. A missing date header is filled in from
    the first column that holds dates. With no header at all, the first date column and the
    first numeric column after it are used.
    """
    raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    if raw.empty:
        return None
    def close_column(lookup: dict[str, int]) -> Optional[int]:
        exact = next((lookup[n] for n in _CLOSE_NAMES if n in lookup), None)
        if exact is not None:
            return exact
        return next((j for n, j in lookup.items()
                     if ("close" in n or "price" in n) and len(n) <= 30 and not any(w in n for w in _NOT_CLOSE)), None)

    candidates = []
    for i in range(min(50, len(raw))):
        names = [_norm(v) if pd.notna(v) else "" for v in raw.iloc[i]]
        lookup = {n: j for j, n in enumerate(names) if n}
        if len(lookup) < 2:  # a title line such as "Price History, Daily, USD" is a single cell
            continue
        close_j = close_column(lookup)
        if close_j is None:
            continue
        date_j = next((lookup[n] for n in _DATE_NAMES if n in lookup), None)
        candidates.append((date_j is None, i, names, close_j, date_j))
    # Prefer a header naming both a date and a price column; otherwise infer the date column.
    for _, i, names, close_j, date_j in sorted(candidates, key=lambda c: (c[0], c[1])):
        body = raw.iloc[i + 1:].reset_index(drop=True)
        headers = [str(raw.iloc[i, j]).strip() if names[j] else f"column_{j}" for j in range(raw.shape[1])]
        if date_j is None:
            date_j = next((j for j in range(raw.shape[1]) if j != close_j and _mostly_dates(body.iloc[:, j])), None)
            if date_j is None:
                continue
        headers[date_j] = "Date"
        body.columns = headers
        return body
    # No header row: first date-like column, then the first numeric column after it.
    date_j = next((j for j in range(raw.shape[1]) if _mostly_dates(raw.iloc[:, j])), None)
    if date_j is None:
        return None
    close_j = next((j for j in range(date_j + 1, raw.shape[1]) if _mostly_numbers(raw.iloc[:, j])), None)
    if close_j is None:
        return None
    return pd.DataFrame({"Date": raw.iloc[:, date_j], "Close": raw.iloc[:, close_j]})


def parse_price_excel(data: bytes, label: str, extension: str = "xlsx") -> PriceHistory:
    """Parse an Excel workbook of daily prices, using the first sheet that contains a price table."""
    engine = "xlrd" if extension == "xls" else "openpyxl"
    try:
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, engine=engine)
    except ImportError as exc:  # pragma: no cover - both engines are in requirements.txt
        raise MarketDataError(f"Reading .{extension} files needs the '{engine}' package.") from exc
    except Exception as exc:
        raise MarketDataError(
            "That file isn't a readable Excel workbook. If it's password-protected, save an unprotected copy."
        ) from exc
    problems = []
    for name, raw in sheets.items():
        table = _table_from_sheet(raw)
        if table is None:
            continue
        try:
            source = "Uploaded Excel" if len(sheets) == 1 else f"Uploaded Excel, sheet '{name}'"
            return history_from_frame(table, label=label, source=source, date_col="Date" if "Date" in table else None)
        except MarketDataError as exc:
            problems.append(f"'{name}': {exc}")
    detail = f" ({'; '.join(problems)})" if problems else ""
    raise MarketDataError(
        "Couldn't find a table of dates and closing prices in that workbook. Make sure one sheet has a "
        f"date column and a price column (headed e.g. 'Date' and 'Price' or 'Close').{detail}"
    )


def parse_price_file(data: bytes, filename: str, label: Optional[str] = None) -> PriceHistory:
    """Parse an uploaded price history, choosing the reader from the file extension."""
    stem, _, ext = filename.rpartition(".")
    ext = ext.lower() if stem else ""
    label = label or (stem or filename).upper()
    if ext in ("csv", "txt"):
        return parse_price_csv(data, label)
    if ext in EXCEL_TYPES:
        return parse_price_excel(data, label, ext)
    if ext == "pdf":
        raise MarketDataError(
            "PDFs can't be read reliably (table columns shift and numbers get split). "
            "Export the price history to Excel or CSV instead."
        )
    raise MarketDataError(f"Unsupported file type '.{ext}'. Upload a CSV or Excel file (.xlsx, .xls).")


# ---------------------------------------------------------------------------
# Option chains
# ---------------------------------------------------------------------------

CHAIN_COLUMNS = ["type", "strike", "expiry", "years", "bid", "ask", "mid", "last", "price",
                 "volume", "open_interest", "yahoo_iv", "iv"]


def clean_chain(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: float,
    expiry: date,
    today: date,
    r: float,
    q: float,
    moneyness: tuple[float, float] = (0.6, 1.5),
) -> pd.DataFrame:
    """Tidy one expiry of a Yahoo-style option chain and compute implied vols with our solver.

    * Uses the bid/ask mid when both sides are quoted, otherwise the last trade.
    * Keeps out-of-the-money options only (puts below the forward, calls above), as
      market practice does for volatility surfaces.
    * Drops strikes outside ``moneyness`` (K/S) and quotes with no usable price.

    US single-stock options are American; inverting them with Black-Scholes gives the
    usual market-convention implied vol, slightly overstated for deep in-the-money puts,
    which the OTM filter avoids.
    """
    years = max((expiry - today).days, 0) / 365.0
    if years <= 0:
        return pd.DataFrame(columns=CHAIN_COLUMNS)
    forward = spot * math.exp((r - q) * years)

    rows = []
    for kind, frame in (("call", calls), ("put", puts)):
        if frame is None or frame.empty:
            continue
        f = frame.copy()
        for col in ("bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"):
            if col not in f:
                f[col] = np.nan
        bid, ask, last = f["bid"].astype(float), f["ask"].astype(float), f["lastPrice"].astype(float)
        two_sided = (bid > 0) & (ask >= bid)
        f["mid"] = np.where(two_sided, (bid + ask) / 2.0, np.nan)
        f["price"] = f["mid"].fillna(last.where(last > 0))
        k = f["strike"].astype(float)
        otm = (k >= forward) if kind == "call" else (k < forward)
        within = (k / spot >= moneyness[0]) & (k / spot <= moneyness[1])
        f = f[otm & within & (f["price"] > 0)]
        for row in f.itertuples(index=False):
            rows.append({
                "type": kind, "strike": float(row.strike), "expiry": expiry, "years": years,
                "bid": float(row.bid), "ask": float(row.ask), "mid": float(row.mid),
                "last": float(row.lastPrice), "price": float(row.price),
                "volume": float(row.volume) if pd.notna(row.volume) else 0.0,
                "open_interest": float(row.openInterest) if pd.notna(row.openInterest) else 0.0,
                "yahoo_iv": float(row.impliedVolatility) if pd.notna(row.impliedVolatility) else np.nan,
            })
    out = pd.DataFrame(rows, columns=CHAIN_COLUMNS[:-1])
    if out.empty:
        return pd.DataFrame(columns=CHAIN_COLUMNS)

    def solve(row: pd.Series) -> float:
        try:
            return implied_volatility(row["price"], spot, row["strike"], row["years"], r, q, row["type"])
        except ValueError:
            return float("nan")  # price outside no-arbitrage bounds (stale or crossed quote)

    out["iv"] = out.apply(solve, axis=1)
    return out.sort_values("strike").reset_index(drop=True)


def atm_implied_vol(chain: pd.DataFrame, spot: float) -> float:
    """Implied vol of the strike closest to spot (interpolated linearly in strike)."""
    c = chain.dropna(subset=["iv"]).sort_values("strike")
    if len(c) == 0:
        return float("nan")
    if len(c) == 1:
        return float(c["iv"].iloc[0])
    return float(np.interp(spot, c["strike"], c["iv"]))


def quotes_for_surface(chains: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack cleaned chains into the ``strike, expiry, price, type`` table the surface page reads."""
    frames = [c[["strike", "years", "price", "type"]].rename(columns={"years": "expiry"}) for c in chains if len(c)]
    if not frames:
        return pd.DataFrame(columns=["strike", "expiry", "price", "type"])
    return pd.concat(frames, ignore_index=True)


def surface_from_chains(
    quotes: pd.DataFrame,
    spot: float,
    r: float,
    q: float,
    moneyness: tuple[float, float] = (0.8, 1.2),
    n_strikes: int = 25,
) -> VolSurface:
    """Interpolate market implied vols onto a common strike grid, one row per expiry.

    Listed strikes differ between expiries, so each expiry's smile (its ``iv`` by
    ``strike``) is interpolated linearly onto ``spot * linspace(*moneyness)``. Points
    outside the strikes actually quoted for that expiry are left as ``nan`` rather than
    extrapolated. Prices on the grid are the Black-Scholes prices at those vols, using
    the out-of-the-money option at each point.
    """
    strikes = spot * np.linspace(moneyness[0], moneyness[1], n_strikes)
    q_ = quotes.dropna(subset=["iv"])
    expiries = np.sort(q_["years"].unique()) if len(q_) else np.empty(0)
    vols = np.full((len(expiries), len(strikes)), np.nan)
    for i, T in enumerate(expiries):
        smile = q_[q_["years"] == T].sort_values("strike")
        if len(smile) < 2:
            continue
        k, v = smile["strike"].to_numpy(float), smile["iv"].to_numpy(float)
        inside = (strikes >= k.min()) & (strikes <= k.max())
        vols[i, inside] = np.interp(strikes[inside], k, v)
    keep = np.isfinite(vols).any(axis=1)
    expiries, vols = expiries[keep], vols[keep]
    types = otm_option_types(strikes, expiries, spot, r, q)
    prices = np.full(vols.shape, np.nan)
    for i, T in enumerate(expiries):
        ok = np.isfinite(vols[i])
        for kind in ("call", "put"):
            m = ok & (types[i] == kind)
            if m.any():
                prices[i, m] = black_scholes_price(spot, strikes[m], T, r, vols[i, m], q, kind)
    return VolSurface(strikes, expiries, vols, prices, types)


@dataclass(frozen=True)
class LegQuote:
    """A listed option chosen for a strategy leg, priced at the side of the market you trade on."""

    kind: str
    strike: float
    bid: float
    ask: float
    mid: float
    fill: float  # buy at the ask, sell at the bid (falling back to mid, then last trade)
    iv: float  # implied vol of the mid (or fill) from the lab's solver; nan if not solvable


def leg_quote(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    kind: str,
    target_strike: float,
    quantity: float,
    spot: float,
    years: float,
    r: float,
    q: float,
) -> Optional[LegQuote]:
    """Snap ``target_strike`` to the nearest listed strike and price the leg from live quotes.

    Long legs (``quantity > 0``) fill at the ask and short legs at the bid, which is what a
    retail order would actually pay or receive. Returns ``None`` if the chain has no usable
    quote for that option type.
    """
    frame = calls if kind == "call" else puts
    if frame is None or frame.empty:
        return None
    f = frame.copy()
    for col in ("bid", "ask", "lastPrice"):
        if col not in f:
            f[col] = np.nan
    bid_s, ask_s, last_s = f["bid"].astype(float), f["ask"].astype(float), f["lastPrice"].astype(float)
    usable = ((bid_s > 0) & (ask_s >= bid_s)) | (last_s > 0)
    f = f[usable]
    if f.empty:
        return None
    row = f.iloc[int(np.argmin(np.abs(f["strike"].astype(float) - target_strike)))]
    bid, ask, last = float(row["bid"]), float(row["ask"]), float(row["lastPrice"])
    two_sided = bid > 0 and ask >= bid
    mid = (bid + ask) / 2.0 if two_sided else last
    if quantity > 0:
        fill = ask if ask > 0 else mid
    else:
        fill = bid if bid > 0 else mid
    try:
        iv = implied_volatility(mid if mid > 0 else fill, spot, float(row["strike"]), years, r, q, kind)
    except ValueError:
        iv = float("nan")
    return LegQuote(kind, float(row["strike"]), bid, ask, mid, float(fill), iv)
