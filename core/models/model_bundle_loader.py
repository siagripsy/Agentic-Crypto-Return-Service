from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings

import joblib
import pandas as pd

from core.models.probabilistic_quantile import (
    add_next_day_target,
    fit_quantile_models,
    prepare_model_frame,
    time_split,
)
from core.numpy_compat import setup_numpy_compatibility
from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository


def load_quantile_model_bundle(
    bundle_path: str | Path,
    *,
    symbol: str | None = None,
    ticker: str | None = None,
    features_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """
    Load a saved quantile bundle. If an older pickle cannot be deserialized with
    the current NumPy / scikit-learn stack, rebuild it from feature data and
    overwrite the artifact in place.
    """
    path = Path(bundle_path)
    if not path.exists():
        raise FileNotFoundError(f"Model bundle not found: {path}")

    setup_numpy_compatibility()

    try:
        obj = joblib.load(path)
    except Exception as exc:
        obj = _rebuild_bundle_artifact(
            path,
            symbol=symbol,
            ticker=ticker,
            features_df=features_df,
            original_error=exc,
        )

    if isinstance(obj, dict) and "bundle" in obj:
        return obj
    return {"bundle": obj}


def _rebuild_bundle_artifact(
    bundle_path: Path,
    *,
    symbol: str | None,
    ticker: str | None,
    features_df: pd.DataFrame | None,
    original_error: Exception,
) -> dict[str, Any]:
    resolved_symbol, resolved_ticker = _resolve_symbol_and_ticker(symbol=symbol, ticker=ticker, features_df=features_df)

    df = features_df.copy() if features_df is not None else get_market_data_repository().read_features(symbol=resolved_symbol)
    if df.empty:
        raise RuntimeError(
            f"Could not rebuild model bundle for {resolved_symbol}: no feature data available."
        ) from original_error

    modeled = add_next_day_target(df, ret_col="log_ret_1d")
    model_df, feature_cols, target_col = prepare_model_frame(modeled)
    train_df, test_df = time_split(model_df, train_frac=0.8)
    bundle = fit_quantile_models(train_df, feature_cols=feature_cols, target_col=target_col)

    obj: dict[str, Any] = {
        "ticker": resolved_ticker,
        "bundle": bundle,
        "feature_cols": feature_cols,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "source_symbol": resolved_symbol,
    }

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, bundle_path)
    warnings.warn(
        (
            f"Rebuilt incompatible model bundle at {bundle_path} for {resolved_symbol} "
            f"after load failure: {original_error}"
        ),
        RuntimeWarning,
        stacklevel=2,
    )
    return obj


def _resolve_symbol_and_ticker(
    *,
    symbol: str | None,
    ticker: str | None,
    features_df: pd.DataFrame | None,
) -> tuple[str, str]:
    feature_ticker = _extract_last_string(features_df, "ticker")
    feature_symbol = _extract_last_string(features_df, "symbol")

    if symbol and ticker:
        return symbol.upper().strip(), ticker.upper().strip()

    if symbol and feature_ticker:
        return symbol.upper().strip(), feature_ticker.upper().strip()

    if ticker and feature_symbol:
        return feature_symbol.upper().strip(), ticker.upper().strip()

    if ticker:
        normalized_ticker = ticker.upper().strip()
        return normalized_ticker.split("-", 1)[0], normalized_ticker

    if symbol:
        coin_repository = get_coin_repository()
        coin = coin_repository.get_by_symbol(symbol)
        return coin.symbol, coin.yahoo_ticker

    if feature_ticker:
        normalized_ticker = feature_ticker.upper().strip()
        return (feature_symbol or normalized_ticker.split("-", 1)[0]).upper().strip(), normalized_ticker

    raise ValueError("Need symbol, ticker, or features_df with ticker column to load/rebuild model bundle.")


def _extract_last_string(features_df: pd.DataFrame | None, column: str) -> str | None:
    if features_df is None or column not in features_df.columns:
        return None
    values = features_df[column].dropna()
    if values.empty:
        return None
    return str(values.iloc[-1]).strip()
