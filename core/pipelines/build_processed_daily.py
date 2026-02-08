from pathlib import Path
import pandas as pd

from core.config.ingestion_config import IngestionConfig
from core.data_sources.coins_registry import load_coins_metadata

def build_one(symbol: str, yahoo_ticker: str) -> Path:
    cfg = IngestionConfig()

    ohlcv_path = cfg.raw_root / "ohlcv" / f"{yahoo_ticker}_daily.csv"
    mcap_path = cfg.raw_root / "market_cap" / f"{symbol}_daily.csv"

    if not ohlcv_path.exists():
        raise FileNotFoundError(f"Missing OHLCV raw file: {ohlcv_path}")

    df_ohlcv = pd.read_csv(ohlcv_path)
    df_ohlcv["date"] = df_ohlcv["date"].astype(str)

    # market cap might not exist or might be empty
    if mcap_path.exists():
        df_mcap = pd.read_csv(mcap_path)
        if not df_mcap.empty and "date" in df_mcap.columns:
            df_mcap["date"] = df_mcap["date"].astype(str)
            df_mcap = df_mcap[["date", "market_cap"]]
        else:
            df_mcap = pd.DataFrame(columns=["date", "market_cap"])
    else:
        df_mcap = pd.DataFrame(columns=["date", "market_cap"])

    df_final = df_ohlcv.merge(df_mcap, on="date", how="left")

    out_path = cfg.processed_root / "daily" / f"{symbol}_daily.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(out_path, index=False)

    return out_path

def build_all() -> None:
    cfg = IngestionConfig()
    coins = load_coins_metadata(cfg.coins_metadata_path)

    for c in coins["coins"]:
        symbol = c["symbol"]
        yahoo_ticker = c["yahoo_ticker"]
        out = build_one(symbol, yahoo_ticker)
        print(f"built: {out}")
