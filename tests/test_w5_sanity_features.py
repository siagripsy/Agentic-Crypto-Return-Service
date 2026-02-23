import pandas as pd

from core.features.feature_engineering import build_features_basic

SAMPLE_PATH = "data/sample/sampleData_Test_Modelsanity.csv"

def test_feature_engineering_on_sample_dataset():
    df = pd.read_csv(SAMPLE_PATH)
    assert not df.empty

    # Ensure expected columns exist
    required_cols = {"symbol", "date", "open", "high", "low", "close", "volume", "market_cap"}
    assert required_cols.issubset(set(df.columns)), f"Missing columns: {required_cols - set(df.columns)}"

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    feat = build_features_basic(df)

    assert not feat.empty
    assert "symbol" in feat.columns
    assert "date" in feat.columns
    # Expected engineered columns 
    expected = {
        "log_ret_1d", "log_ret_5d", "log_ret_10d",
        "vol_7d", "vol_30d",
        "risk_adj_ret_1d",
        "vol_ratio_7d_30d",
        "drawdown_30d",
    }
    missing = expected - set(feat.columns)
    assert not missing, f"Missing engineered cols: {missing}. Got: {feat.columns.tolist()}"

    # Sanity: log returns should have some NaNs at the beginning but not tons
    ret_cols = ["log_ret_1d", "log_ret_5d", "log_ret_10d"]
    nan_count = feat[ret_cols].isna().sum().sum()

    # With 1 symbol and short sample, some NaNs are expected; still should not be most rows
    assert nan_count < len(feat) * len(ret_cols), f"All returns are NaN? nan_count={nan_count}"

    # No infinite values
    assert not feat[ret_cols].isin([float("inf"), float("-inf")]).any().any()

    # Vol columns should be non-negative (ignoring NaNs at the start)
    vol_cols = ["vol_7d", "vol_30d"]
    for c in vol_cols:
        s = feat[c].dropna()
        assert (s >= 0).all(), f"Found negative volatility in {c}"

    # Drawdown should be <= 0 (0 at peak), not positive (ignoring NaNs)
    dd = feat["drawdown_30d"].dropna()
    assert (dd <= 1e-12).all(), "Drawdown should be <= 0"