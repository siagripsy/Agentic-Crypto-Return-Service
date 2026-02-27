from core.portfolio import PortfolioConstraints, build_portfolio
from core.risk import RiskReport


def _risk(symbol: str, cvar: float, mdd: float, horizon: int = 20) -> RiskReport:
    return RiskReport(
        symbol=symbol,
        horizon_days=horizon,
        var={"p95": -0.05},
        cvar={"p95": cvar},
        max_drawdown_est=mdd,
        tail_metrics={},
        notes=[],
    )


def test_build_portfolio_weights_sum_to_one_with_cash():
    scenarios = {
        "BTC-USD": {"metrics": {"horizon_return_summary": {"mean": 0.10}, "prob_profit": 0.60}},
        "ETH-USD": {"metrics": {"horizon_return_summary": {"mean": 0.07}, "prob_profit": 0.55}},
        "SOL-USD": {"metrics": {"horizon_return_summary": {"mean": 0.12}, "prob_profit": 0.52}},
    }
    risks = {
        "BTC-USD": _risk("BTC-USD", cvar=-0.20, mdd=-0.10),
        "ETH-USD": _risk("ETH-USD", cvar=-0.15, mdd=-0.08),
        "SOL-USD": _risk("SOL-USD", cvar=-0.35, mdd=-0.18),
    }

    c = PortfolioConstraints(user_risk_tolerance=20, top_k=2, allow_cash=True)
    res = build_portfolio(scenarios, risks, c)

    total = sum(res.weights.values())
    assert abs(total - 1.0) < 1e-9
    assert "CASH" in res.weights
    assert res.weights["CASH"] > 0


def test_build_portfolio_more_risk_tolerant_less_cash():
    scenarios = {
        "BTC-USD": {"metrics": {"horizon_return_summary": {"mean": 0.10}, "prob_profit": 0.60}},
        "ETH-USD": {"metrics": {"horizon_return_summary": {"mean": 0.07}, "prob_profit": 0.55}},
    }
    risks = {
        "BTC-USD": _risk("BTC-USD", cvar=-0.20, mdd=-0.10),
        "ETH-USD": _risk("ETH-USD", cvar=-0.15, mdd=-0.08),
    }

    low = build_portfolio(scenarios, risks, PortfolioConstraints(user_risk_tolerance=10, top_k=2, allow_cash=True))
    high = build_portfolio(scenarios, risks, PortfolioConstraints(user_risk_tolerance=90, top_k=2, allow_cash=True))

    assert low.weights.get("CASH", 0.0) > high.weights.get("CASH", 0.0)


def test_build_portfolio_respects_top_k():
    scenarios = {
        "A": {"metrics": {"horizon_return_summary": {"mean": 0.01}, "prob_profit": 0.51}},
        "B": {"metrics": {"horizon_return_summary": {"mean": 0.02}, "prob_profit": 0.52}},
        "C": {"metrics": {"horizon_return_summary": {"mean": 0.03}, "prob_profit": 0.53}},
        "D": {"metrics": {"horizon_return_summary": {"mean": 0.04}, "prob_profit": 0.54}},
    }
    risks = {
        "A": _risk("A", cvar=-0.10, mdd=-0.05),
        "B": _risk("B", cvar=-0.10, mdd=-0.05),
        "C": _risk("C", cvar=-0.10, mdd=-0.05),
        "D": _risk("D", cvar=-0.10, mdd=-0.05),
    }

    res = build_portfolio(scenarios, risks, PortfolioConstraints(user_risk_tolerance=50, top_k=2, allow_cash=False))

    assert len(res.details) == 2
    assert len(res.weights) == 2
