from core.regime_detection.schemas import RegimeMatchConfig
from core.regime_detection.historical_matching import train_for_coin

if __name__ == "__main__":
    cfg = RegimeMatchConfig(
        match_window_days=30,
        top_n=10,
        horizon_days=20,
        similarity_metric="cosine",
        embargo_days=5,
    )

    result = train_for_coin(
        features_csv_path="data/processed/features/BTC_features.csv",
        ticker="BTC",
        config=cfg,
        latent_dim=16,
    )

    print("TRAIN DONE")
    print("n_windows:", result["n_windows"])
    print("window_shape:", result["window_shape"])
    print("embeddings_shape:", result["embeddings_shape"])


    from core.regime_detection.historical_matching import find_top_n_similar_windows

    matches = find_top_n_similar_windows(
        embeddings=result["embeddings"],
        window_end_indices=result["window_end_indices"],
        config=cfg,
    )

    print("TOP MATCHES:")
    for m in matches[:5]:
        print(m)

    from core.regime_detection.historical_matching import evaluate_forward_outcomes, summarize_outcomes

    evaluated = evaluate_forward_outcomes(
        df_raw=result["df"],
        matches=matches,
        config=cfg,
    )

    print("EVALUATED (first 3):")
    for e in evaluated[:3]:
        print(e)

    summary = summarize_outcomes(evaluated)
    print("SUMMARY:")
    print(summary)