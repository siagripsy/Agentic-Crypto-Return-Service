import os
from typing import Optional

import pandas as pd

from core.config.ingestion_config import IngestionConfig
from core.data_sources.coingecko_marketcap import fetch_marketcap_daily
from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository

def run_one_symbol(symbol: str, coingecko_id: str, api_key: Optional[str] = None) -> int:
    cfg = IngestionConfig()
    repository = get_market_data_repository()
    last_date = repository.get_last_market_cap_date(symbol)

    if last_date is None:
        days = cfg.coingecko_default_days
    else:
        today = pd.Timestamp.today().normalize()
        next_day = pd.to_datetime(last_date) + pd.Timedelta(days=1)

        if next_day > today:
            print(f"[{symbol}] up-to-date (last_date={last_date}). No fetch needed.")
            return 0

        delta_days = int((today - next_day).days) + 1
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

    if last_date is not None and not df_new.empty:
        df_new["date"] = df_new["date"].astype(str)
        df_new = df_new[df_new["date"] > str(last_date)]

        if df_new.empty:
            print(f"[{symbol}] no new market cap rows to add.")
            return 0

    inserted = repository.save_market_cap(symbol, df_new)
    print(f"[{symbol}] added {inserted} new rows (days_requested={days})")
    return inserted


def run_all(api_key: Optional[str] = None) -> None:
    coins = get_coin_repository().as_dataframe()
    for coin in coins.to_dict(orient="records"):
        inserted = run_one_symbol(coin["symbol"], coin["coingecko_id"], api_key=api_key)
        print(f"[{coin['symbol']}] inserted rows: {inserted}")
