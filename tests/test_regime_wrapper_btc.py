from core.regime_detection.schemas import RegimeMatchConfig
from core.regime_detection.regime_detection import run_regime_historical_matching

if __name__ == "__main__":
    cfg = RegimeMatchConfig(match_window_days=30, top_n=10, horizon_days=20)

    out = run_regime_historical_matching(
        features_csv_path="data/processed/features/BTC_features.csv",
        ticker="BTC-USD",
        config=cfg,
        latent_dim=16,
        train_epochs=20,
    )

    print(out["current_window"])
    print(out["summary"])
    print("first_match:", out["matches"][0])
    print("second_match:", out["matches"][1])