from pathlib import Path

import pandas as pd
import numpy as np

from core.models.model_bundle_loader import load_quantile_model_bundle


def _sample_features() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=80, freq="D")
    close = pd.Series(range(100, 180), dtype=float)
    log_ret_1d = np.log(close / close.shift(1)).fillna(0.0)

    return pd.DataFrame(
        {
            "date": dates,
            "open": close - 1,
            "high": close + 1,
            "low": close - 2,
            "close": close,
            "volume": [1000.0] * len(dates),
            "market_cap": [100000.0] * len(dates),
            "log_ret_1d": log_ret_1d.fillna(0.0),
            "log_ret_5d": log_ret_1d.rolling(5).sum().fillna(0.0),
            "log_ret_10d": log_ret_1d.rolling(10).sum().fillna(0.0),
            "vol_7d": log_ret_1d.rolling(7).std().fillna(0.0),
            "vol_30d": log_ret_1d.rolling(30).std().fillna(0.0),
            "risk_adj_ret_1d": [0.0] * len(dates),
            "vol_ratio_7d_30d": [1.0] * len(dates),
            "drawdown_30d": [0.0] * len(dates),
            "ticker": ["BTC-USD"] * len(dates),
        }
    )


def test_load_quantile_model_bundle_rebuilds_incompatible_artifact(monkeypatch):
    bundle_path = Path("tests/.tmp/model_bundle_loader/artifacts/models/BTC-USD/quantile_model_bundle.joblib")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_bytes(b"placeholder")

    call_count = {"load": 0, "dump": 0}

    def fake_load(path):
        call_count["load"] += 1
        raise ValueError("<class 'numpy.random._mt19937.MT19937'> is not a known BitGenerator module.")

    def fake_dump(obj, path):
        call_count["dump"] += 1
        assert obj["ticker"] == "BTC-USD"
        assert obj["source_symbol"] == "BTC"
        assert "bundle" in obj
        assert Path(path) == bundle_path

    monkeypatch.setattr("core.models.model_bundle_loader.joblib.load", fake_load)
    monkeypatch.setattr("core.models.model_bundle_loader.joblib.dump", fake_dump)

    obj = load_quantile_model_bundle(bundle_path, symbol="BTC", features_df=_sample_features())

    assert call_count == {"load": 1, "dump": 1}
    assert obj["ticker"] == "BTC-USD"
    assert obj["source_symbol"] == "BTC"
    assert obj["bundle"].feature_cols
