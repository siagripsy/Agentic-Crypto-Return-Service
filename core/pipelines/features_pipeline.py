# core/pipelines/features_pipeline.py
from __future__ import annotations

from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository


def run_all() -> None:
    repository = get_market_data_repository()
    for symbol in get_coin_repository().list_symbols():
        inserted = repository.append_missing_features(symbol)
        print(f"[{symbol}] feature rows inserted: {inserted}")
