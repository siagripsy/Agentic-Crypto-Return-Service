from __future__ import annotations

import os
import argparse
import joblib

from core.models.probabilistic_quantile import (
    load_features_csv,
    add_next_day_target,
    prepare_model_frame,
    time_split,
    fit_quantile_models,
)
from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository

DEFAULT_OUT_DIR = "artifacts/models"


def train_one_coin(symbol: str, out_dir: str, train_frac: float = 0.8) -> str:
    repository = get_market_data_repository()
    df = load_features_csv(repository.read_features(symbol=symbol))
    if df.empty:
        raise FileNotFoundError(f"No features found for symbol={symbol}")

    df = add_next_day_target(df, ret_col="log_ret_1d")

    model_df, feats, target = prepare_model_frame(df)

    train_df, test_df = time_split(model_df, train_frac=train_frac)

    bundle = fit_quantile_models(train_df, feature_cols=feats, target_col=target)

    ticker = None
    if "ticker" in df.columns:
        ticker = str(df["ticker"].dropna().iloc[-1])

    coin_dir = os.path.join(out_dir, ticker)
    os.makedirs(coin_dir, exist_ok=True)

    out_path = os.path.join(coin_dir, "quantile_model_bundle.joblib")
    joblib.dump(
        {
            "ticker": ticker,
            "bundle": bundle,
            "feature_cols": feats,
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "source_symbol": symbol.upper(),
        },
        out_path,
    )
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--train_frac", type=float, default=0.8)
    args = ap.parse_args()

    symbols = args.symbols or get_coin_repository().list_symbols()
    if not symbols:
        raise SystemExit("No symbols found in Coins table.")

    saved = []
    for symbol in symbols:
        out_path = train_one_coin(symbol, args.out_dir, train_frac=args.train_frac)
        saved.append(out_path)
        print(f"[OK] trained and saved: {out_path}")

    print(f"\nDone. Total models saved: {len(saved)}")


if __name__ == "__main__":
    main()
