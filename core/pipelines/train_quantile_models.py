from __future__ import annotations

import os
import glob
import argparse
import joblib
import pandas as pd

from core.models.probabilistic_quantile import (
    add_next_day_target,
    prepare_model_frame,
    time_split,
    fit_quantile_models,
)

DEFAULT_FEATURE_DIR = "data/processed/features"
DEFAULT_OUT_DIR = "artifacts/models"


def train_one_coin(csv_path: str, out_dir: str, train_frac: float = 0.8) -> str:
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # define next-day target (no leakage)
    df = add_next_day_target(df, ret_col="log_ret_1d")

    model_df, feats, target = prepare_model_frame(df)

    train_df, test_df = time_split(model_df, train_frac=train_frac)

    bundle = fit_quantile_models(train_df, feature_cols=feats, target_col=target)

    ticker = None
    if "ticker" in df.columns:
        ticker = str(df["ticker"].dropna().iloc[-1])
    if not ticker:
        # fallback from filename
        base = os.path.basename(csv_path)
        ticker = base.split("_")[0].upper()

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
            "source_csv": csv_path,
        },
        out_path,
    )
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features_dir", default=DEFAULT_FEATURE_DIR)
    ap.add_argument("--out_dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--pattern", default="*_features.csv")
    ap.add_argument("--train_frac", type=float, default=0.8)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.features_dir, args.pattern)))
    if not files:
        raise SystemExit(f"No feature files found in {args.features_dir} with pattern {args.pattern}")

    saved = []
    for f in files:
        out_path = train_one_coin(f, args.out_dir, train_frac=args.train_frac)
        saved.append(out_path)
        print(f"[OK] trained and saved: {out_path}")

    print(f"\nDone. Total models saved: {len(saved)}")


if __name__ == "__main__":
    main()