from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import requests
import pandas as pd

def fetch_marketcap_daily(
    coingecko_id: str,
    api_key: Optional[str] = None,
    vs_currency: str = "usd",
    days: str = "365",
) -> pd.DataFrame:
    """
    Fetch market cap time series from CoinGecko.
    Returns DataFrame columns: date, market_cap, coingecko_id

    Notes:
    - Many endpoints return [timestamp_ms, value]
    """

    url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days}

    headers: Dict[str, str] = {}
    if api_key:
        # CoinGecko Demo keys use this header format in many setups
        headers["x-cg-demo-api-key"] = api_key

    r = requests.get(url, params=params, headers=headers, timeout=30)
    r = requests.get(url, params=params, headers=headers, timeout=30)

    if r.status_code != 200:
        # Don't crash the pipeline on CoinGecko limitations
        return pd.DataFrame(columns=["date", "market_cap", "coingecko_id"])

    data: Dict[str, Any] = r.json()
    points = data.get("market_caps", [])

    if not points:
        return pd.DataFrame(columns=["date", "market_cap", "coingecko_id"])

    df = pd.DataFrame(points, columns=["timestamp_ms", "market_cap"])
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True).dt.date
    df = df.drop(columns=["timestamp_ms"])

    # daily aggregation (keep last value of day)
    df = df.groupby("date", as_index=False).last()

    df["coingecko_id"] = coingecko_id
    return df
