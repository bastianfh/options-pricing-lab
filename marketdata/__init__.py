"""marketdata: loading real US stock data for the lab.

* :mod:`marketdata.parse` turns raw data (uploaded CSVs, Yahoo Finance frames, option
  chains) into clean, typed objects. It does no network access, so it is fully testable.
* :mod:`marketdata.fetch` downloads data from Yahoo Finance through ``yfinance``.

The pricing maths stays in :mod:`pricing`; this package only gets data in and tidies it.
"""

from marketdata.parse import MarketDataError, PriceHistory

__all__ = ["MarketDataError", "PriceHistory"]
