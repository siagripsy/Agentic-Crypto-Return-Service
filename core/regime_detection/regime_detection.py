import numpy as np

from core.regime_detection.historical_matching import (
    FEATURE_COLUMNS,
    load_feature_data,
    scale_features,
    apply_scaler,
    build_rolling_windows,
    train_autoencoder,
    compute_embeddings,
    save_regime_artifacts,
    load_regime_artifacts,
    find_top_n_similar_windows,
    evaluate_forward_outcomes,
    summarize_outcomes,
)


def run_regime_historical_matching(
    features_df,
    ticker: str,
    match_window_days: int = 30,
    top_n: int = 10,
    horizon_days: int = 20,
    similarity_metric: str = "cosine",
    embargo_days: int = 5,
    latent_dim: int = 16,
    train_epochs: int = 40,
    force_retrain: bool = False,
):
    """
    End-to-end:
    - load features
    - scale features (fit scaler if training, reuse scaler if loading)
    - build rolling windows
    - train or load AE
    - compute embeddings
    - find top-n similar windows to current
    - evaluate forward outcomes using horizon_days
    - summarize
    """

    df_raw = load_feature_data(features_df)

    artifacts = None if force_retrain else load_regime_artifacts(
        ticker=ticker,
        match_window_days=match_window_days,
        latent_dim=latent_dim,
    )

    if artifacts is not None:
        model = artifacts["model"]
        scaler = artifacts["scaler"]
        df_scaled = apply_scaler(df_raw, scaler)
    else:
        df_scaled, scaler = scale_features(df_raw)

    windows, window_end_indices = build_rolling_windows(
        df_scaled=df_scaled,
        match_window_days=match_window_days,
    )

    if windows.size == 0:
        raise ValueError("No valid windows were built. Check for NaNs or match_window_days too large.")

    if artifacts is None:
        model, _ = train_autoencoder(
            windows=windows,
            latent_dim=latent_dim,
            epochs=train_epochs,
            batch_size=64,
            lr=1e-3,
        )

        train_cfg = {
            "match_window_days": int(match_window_days),
            "similarity_metric": str(similarity_metric),
            "embargo_days": int(embargo_days),
            "latent_dim": int(latent_dim),
            "feature_columns": list(FEATURE_COLUMNS),
        }

        save_regime_artifacts(
            ticker=ticker,
            model=model,
            scaler=scaler,
            train_config=train_cfg,
        )

        used_cached_model = False
    else:
        used_cached_model = True

    embeddings = compute_embeddings(model=model, windows=windows)

    matches = find_top_n_similar_windows(
        embeddings=embeddings,
        window_end_indices=window_end_indices,
        top_n=top_n,
        similarity_metric=similarity_metric,
        embargo_days=embargo_days,
    )

    evaluated = evaluate_forward_outcomes(
        df_raw=df_raw,
        matches=matches,
        match_window_days=match_window_days,
        horizon_days=horizon_days,
    )

    summary = summarize_outcomes(evaluated)

    current_end_idx = window_end_indices[-1] - 1
    current_start_idx = window_end_indices[-1] - match_window_days

    current_window_info = {
        "ticker": ticker,
        "current_window_start_date": str(df_raw.loc[current_start_idx, "date"]),
        "current_window_end_date": str(df_raw.loc[current_end_idx, "date"]),
        "match_window_days": int(match_window_days),
        "top_n": int(top_n),
        "horizon_days": int(horizon_days),
    }

    return {
        "current_window": current_window_info,
        "matches": evaluated,
        "summary": summary,
        "used_cached_model": used_cached_model and (not force_retrain),
    }
