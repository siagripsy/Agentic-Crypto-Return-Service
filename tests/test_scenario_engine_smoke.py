import pandas as pd
from core.pipelines.scenario_engine import ScenarioEngine

def test_compute_returns_smoke():
    df = pd.read_csv("data/processed/daily/BTC_daily.csv")
    engine = ScenarioEngine(df[["date", "close"]])
    r = engine.compute_returns()

    assert len(r) > 100
    assert r.isna().sum() == 0

    # Test fit_distribution
    params = engine.fit_distribution(r)

    assert params["dist"] == "normal"
    assert params["sigma"] > 0
    assert params["n"] == len(r)


    # Test Monte Carlo simulation
    last_price = float(df["close"].iloc[-1])

    paths = engine.simulate_paths(
        params=params,
        start_price=last_price,
        horizon_days=30,
        n_scenarios=500,
    )

    assert paths.shape == (500, 31)
    assert (paths > 0).all()


    # Test run method
    from core.pipelines.scenario_engine import ScenarioConfig

    out = engine.run(ScenarioConfig(asset="BTC", horizon_days=30, n_scenarios=300))

    assert out["asset"] == "BTC"
    assert out["distribution"]["dist"] == "normal"
    assert out["summary"]["horizon_days"] == 30
    assert out["paths"].shape == (300, 31)
