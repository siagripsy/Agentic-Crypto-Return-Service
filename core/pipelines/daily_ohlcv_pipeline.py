from typing import Optional
from pathlib import Path

from core.config.ingestion_config import IngestionConfig
from core.data_sources.coins_registry import load_coins_metadata, extract_yahoo_tickers
from core.data_sources.yahoo_ohlcv import fetch_daily_ohlcv
from core.storage.local_csv_store import save_dataframe_csv, raw_ohlcv_path

from core.storage.local_csv_store import read_last_date
import pandas as pd


def run_one_ticker(ticker: str, start: Optional[str] = None) -> Path:
    cfg = IngestionConfig()

    out_path = raw_ohlcv_path(cfg.raw_root, ticker)

    # if file exists -> incremental else we need to get data from start
    last_date = read_last_date(out_path)

    fetch_start = start
    if last_date:
        # fetch from next day
        fetch_start = pd.to_datetime(last_date) + pd.Timedelta(days=1)
        fetch_start = fetch_start.strftime("%Y-%m-%d")

    # Guard: if fetch_start is in the future, don't call Yahoo (avoids yfinance warning)
    if fetch_start:
        today = pd.Timestamp.today().normalize()
        fs = pd.to_datetime(fetch_start)
        if fs > today:
            print(f"[{ticker}] up-to-date (last_date={last_date}). No fetch needed.")
            return out_path

    df_new = fetch_daily_ohlcv(ticker, start=fetch_start)
    if df_new.empty:
        print(f"[{ticker}] no new OHLCV rows to add (maybe up-to-date or unavailable).")
        return out_path

    # if existing -> append + dedupe
    if out_path.exists():
        df_old = pd.read_csv(out_path)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
        df_all = df_all.drop_duplicates(subset=["date"]).sort_values("date")
    else:
        df_all = df_new

    save_dataframe_csv(df_all, out_path)
    return out_path





def run_all(start: Optional[str] = None) -> None:
    cfg = IngestionConfig()
    coins = load_coins_metadata(cfg.coins_metadata_path)
    tickers = extract_yahoo_tickers(coins)

    for t in tickers:
        out = run_one_ticker(t, start=start)
        print(f"saved: {out}")

