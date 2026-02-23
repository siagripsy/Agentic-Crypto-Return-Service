import numpy as np
import pandas as pd

from core.pipelines.scenario_engine import ScenarioEngine, ScenarioConfig

SAMPLE_PATH = "data/sample/sampleData_Test_Modelsanity.csv"

def test_scenario_engine_run_returns_valid_outputs():
    df = pd.read_csv(SAMPLE_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # ScenarioEngine expects price_df with at least "close"
    # Keep only one asset for deterministic sanity
    eth = df[df["symbol"] == "ETH"].copy()
    assert len(eth) >= 35  # should be enough for stable return estimation

    engine = ScenarioEngine(price_df=eth)

    config = ScenarioConfig(
        asset="ETH",
        horizon_days=10,
        n_scenarios=200,
    )

    out = engine.run(config)

    # --- structure checks ---
    assert isinstance(out, dict)

    for k in ["asset", "distribution", "summary", "paths"]:
        assert k in out, f"Missing key: {k}"

    assert out["asset"] == "ETH"

    # --- paths checks ---
    paths = out["paths"]
    assert isinstance(paths, np.ndarray)
    assert paths.shape[0] == config.n_scenarios
    assert paths.shape[1] == config.horizon_days + 1  # includes start day

    assert np.isfinite(paths).all(), "Paths contain NaN/inf"

    # --- summary checks ---
    summary = out["summary"]
    for k in ["start_price", "horizon_days", "n_scenarios", "terminal_mean", "terminal_p05", "terminal_p50", "terminal_p95"]:
        assert k in summary, f"Missing summary key: {k}"

    assert summary["horizon_days"] == config.horizon_days
    assert summary["n_scenarios"] == config.n_scenarios

    start_price = summary["start_price"]
    assert start_price > 0

    # Terminal stats sanity: quantiles should be ordered
    assert summary["terminal_p05"] <= summary["terminal_p50"] <= summary["terminal_p95"]

    # Mean should be within a reasonable range of the simulated terminals
    terminal = paths[:, -1]
    assert np.isfinite(terminal).all()
    assert abs(summary["terminal_mean"] - float(np.mean(terminal))) < 1e-6