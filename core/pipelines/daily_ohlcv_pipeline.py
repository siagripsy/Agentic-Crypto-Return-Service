from typing import Optional

from core.config.ingestion_config import IngestionConfig
from core.data_sources.yahoo_ohlcv import fetch_daily_ohlcv
from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository
import pandas as pd


def run_one_ticker(ticker: str, start: Optional[str] = None) -> int:
    repository = get_market_data_repository()
    last_date = repository.get_last_ohlcv_date(ticker)

    if start is None:
       start = "2009-01-01"

    fetch_start = start
    if last_date:
        fetch_start = pd.to_datetime(last_date) + pd.Timedelta(days=1)
        fetch_start = fetch_start.strftime("%Y-%m-%d")

    if fetch_start:
        today = pd.Timestamp.today().normalize()
        fs = pd.to_datetime(fetch_start)
        if fs > today:
            print(f"[{ticker}] up-to-date (last_date={last_date}). No fetch needed.")
            return 0

    df_new = fetch_daily_ohlcv(ticker, start=fetch_start)
    if df_new.empty:
        print(f"[{ticker}] no new OHLCV rows to add (maybe up-to-date or unavailable).")
        return 0

    inserted = repository.save_ohlcv(ticker, df_new)
    return inserted

def run_all(start: Optional[str] = None) -> None:
    tickers = get_coin_repository().list_yahoo_tickers()

    for t in tickers:
        inserted = run_one_ticker(t, start=start)
        print(f"[{t}] inserted rows: {inserted}")

