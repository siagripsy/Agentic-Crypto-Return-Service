import pandas as pd
import yfinance as yf
from typing import Optional

def fetch_daily_ohlcv(
    ticker: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns columns:
    date, open, high, low, close, volume, ticker
    """

    df = yf.download(
        ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        # No new data (or delisted / unavailable). Caller will decide what to do.
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "ticker"])


    # Handle MultiIndex columns: (PriceField, Ticker)
    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs(ticker, axis=1, level=1)

    df = df.reset_index()

    # Normalize names
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    required = ["date", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for {ticker}: {missing}. Got: {list(df.columns)}")

    out = df[required].copy()
    out["ticker"] = ticker
    return out
