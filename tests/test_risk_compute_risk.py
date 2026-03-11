from core.risk import RiskConfig, compute_risk


def test_compute_risk_happy_path():
    scenarios = {
        "asset": "BTC-USD",
        "summary": {"horizon_days": 20},
        "metrics": {
            "VaR_CVaR_horizon_return": {"VaR": -0.10, "CVaR": -0.15},
            "max_drawdown_summary": {"mean": -0.08},
            "prob_profit": 0.55,
            "prob_loss": 0.45,
            "horizon_return_summary": {"mean": 0.02},
            "terminal_price_summary": {"mean": 50000.0},
        },
    }

    cfg = RiskConfig(confidence_levels=[0.95])
    rep = compute_risk(scenarios, cfg)

    assert rep.symbol == "BTC-USD"
    assert rep.horizon_days == 20
    assert "p95" in rep.var
    assert rep.var["p95"] == -0.10
    assert rep.cvar["p95"] == -0.15
    assert rep.max_drawdown_est == -0.08
    assert rep.tail_metrics["prob_profit"] == 0.55


def test_compute_risk_handles_missing_metrics():
    scenarios = {"asset": "ETH-USD", "summary": {"horizon_days": 10}, "metrics": {}}
    cfg = RiskConfig(confidence_levels=[0.90])

    rep = compute_risk(scenarios, cfg)

    assert rep.symbol == "ETH-USD"
    assert rep.horizon_days == 10
    assert "p90" in rep.var
