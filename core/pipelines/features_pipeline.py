# core/pipelines/features_pipeline.py
from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.config.ingestion_config import IngestionConfig
from core.data_sources.coins_registry import load_coins_metadata, extract_symbols
from core.features.feature_engineering import build_features_basic


def _processed_daily_path(cfg: IngestionConfig, symbol: str) -> Path:
    # data/processed/daily/{SYMBOL}_daily.csv
    return cfg.processed_root / "daily" / f"{symbol}_daily.csv"


def _processed_features_path(cfg: IngestionConfig, symbol: str) -> Path:
    # Ensure the "features" directory exists (create it if missing)
    # data/processed/features/{SYMBOL}_features.csv
    features_dir = cfg.processed_root / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    return features_dir / f"{symbol}_features.csv"


# Main pipeline entrypoint for feature generation across all coins
def run_all() -> None:
    cfg = IngestionConfig()
    coins = load_coins_metadata(cfg.coins_metadata_path)
    symbols = extract_symbols(coins)
    # Iterate through each symbol and build its feature dataset
    for symbol in symbols:
        daily_path = _processed_daily_path(cfg, symbol)
        # If daily data hasn't been built yet, skip this symbol
        if not daily_path.exists():
            print(f"missing processed daily: {daily_path} (run build_processed_daily first)")
            continue

        df = pd.read_csv(daily_path)
        feats = build_features_basic(df)
        # Generate engineered features
        out_path = _processed_features_path(cfg, symbol)
        # Save engineered features to CSV
        feats.to_csv(out_path, index=False)
        print(f"saved: {out_path}")
