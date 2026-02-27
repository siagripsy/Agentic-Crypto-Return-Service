import pandas as pd
import numpy as np

from core.pipelines.portfolio_pipeline import (
    run_portfolio_pipeline,
    PortfolioPipelineConfig,
)


def _fake_price_df():
    dates = pd.date_range("2023-01-01", periods=200, freq="D")
    prices = 100 + np.cumsum(np.random.normal(0, 1, size=len(dates)))
    return pd.DataFrame({"date": dates, "close": prices})


def _fake_features_df():
    dates = pd.date_range("2023-01-01", periods=200, freq="D")
    return pd.DataFrame({
        "date": dates,
        "log_ret_1d": np.random.normal(0, 0.01, size=len(dates)),
        "log_ret_5d": np.random.normal(0, 0.02, size=len(dates)),
        "vol_7d": np.random.uniform(0.01, 0.05, size=len(dates)),
    })


def test_portfolio_pipeline_runs_and_weights_sum_to_one():
    assets = {
        "BTC-USD": {
            "price_df": _fake_price_df(),
            "features_df": _fake_features_df(),
        },
        "ETH-USD": {
            "price_df": _fake_price_df(),
            "features_df": _fake_features_df(),
        },
    }

    cfg = PortfolioPipelineConfig(
        horizon_days=10,
        n_scenarios=100,
        model_type="monte_carlo",  # keep simple for fake data
        user_risk_tolerance=50,
        top_k=2,
        allow_cash=True,
    )

    result = run_portfolio_pipeline(assets=assets, cfg=cfg)

    portfolio = result["portfolio"]
    total = sum(portfolio.weights.values())

    assert abs(total - 1.0) < 1e-6
    assert len(portfolio.weights) >= 1
