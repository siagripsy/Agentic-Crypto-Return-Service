import os
from pathlib import Path
from typing import Optional

import pandas as pd

from core.config.ingestion_config import IngestionConfig
from core.data_sources.coins_registry import load_coins_metadata, extract_coingecko_map
from core.data_sources.coingecko_marketcap import fetch_marketcap_daily
from core.storage.local_csv_store import save_dataframe_csv, raw_marketcap_path
from core.storage.local_csv_store import read_last_date

from datetime import datetime

def run_one_symbol(symbol: str, coingecko_id: str, api_key: Optional[str] = None) -> Path:
    cfg = IngestionConfig()
    out_path = raw_marketcap_path(cfg.raw_root, symbol)

    last_date = read_last_date(out_path)  # string like '2026-02-08' or None

    # Decide how many days to request from CoinGecko
    # - If no history: bootstrap 365
    # - If history exists: fetch only needed recent days (with small buffer)
    if last_date is None:
        days = cfg.coingecko_default_days

    else:
        today = pd.Timestamp.today().normalize()
        next_day = pd.to_datetime(last_date) + pd.Timedelta(days=1)

        # if already up-to-date, skip calling CoinGecko
        if next_day > today:
            print(f"[{symbol}] up-to-date (last_date={last_date}). No fetch needed.")
            return out_path

        delta_days = int((today - next_day).days) + 1

        # CoinGecko endpoint works well with small day windows. Add a small buffer.
        # Keep between 2 and 365.
        max_days = int(cfg.coingecko_default_days)
        days = str(min(max(delta_days + 2, 2), max_days))

    df_new = fetch_marketcap_daily(
        coingecko_id=coingecko_id,
        api_key=api_key,
        days=days,
    )

    # Ensure schema
    if df_new.empty:
        df_new = pd.DataFrame(columns=["date", "market_cap", "coingecko_id"])

    df_new["symbol"] = symbol

    # If we have history, only keep rows after last_date (even with buffer)
    if last_date is not None and not df_new.empty:
        df_new["date"] = df_new["date"].astype(str)
        df_new = df_new[df_new["date"] > str(last_date)]

        if df_new.empty:
            print(f"[{symbol}] no new market cap rows to add.")
            return out_path

    # Merge with existing file if exists
    if out_path.exists():
        df_old = pd.read_csv(out_path)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
        df_all["date"] = df_all["date"].astype(str)
        df_all = df_all.drop_duplicates(subset=["date"]).sort_values("date")
    else:
        df_all = df_new

    save_dataframe_csv(df_all, out_path)
    print(f"[{symbol}] added {len(df_new)} new rows (days_requested={days})")
    return out_path


def run_all(api_key: Optional[str] = None) -> None:
    cfg = IngestionConfig()
    coins = load_coins_metadata(cfg.coins_metadata_path)
    pairs = extract_coingecko_map(coins)

    for symbol, cg_id in pairs:
        out = run_one_symbol(symbol, cg_id, api_key=api_key)
        print(f"saved: {out}")
