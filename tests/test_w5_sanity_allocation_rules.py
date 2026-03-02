import math

from core.portfolio.allocation_rules import (
    allocate_weights,
    RiskTolerance,
    AssetRiskMetrics,
    AllocationConstraints,
)

def _sum_close_to_one(weights: dict, tol: float = 1e-6) -> bool:
    return abs(sum(weights.values()) - 1.0) <= tol

def test_allocate_weights_basic_properties():
    assets = [
        AssetRiskMetrics(symbol="BTC", expected_return=0.12, volatility=0.80, max_drawdown=-0.55),
        AssetRiskMetrics(symbol="ETH", expected_return=0.10, volatility=0.95, max_drawdown=-0.60),
        AssetRiskMetrics(symbol="SOL", expected_return=0.16, volatility=1.20, max_drawdown=-0.70),
    ]

    constraints = AllocationConstraints(
        max_positions=3,
        min_weight_per_asset=0.0,
        max_weight_per_asset=1.0,
    )

    w = allocate_weights(RiskTolerance.MODERATE, assets, constraints)

    assert isinstance(w, dict)
    assert set(w.keys()) == {"BTC", "ETH", "SOL"}
    assert _sum_close_to_one(w)

    for k, v in w.items():
        assert v >= 0.0
        assert math.isfinite(v)

def test_allocate_weights_risk_tolerance_changes_result():
    assets = [
        AssetRiskMetrics(symbol="BTC", expected_return=0.12, volatility=0.80, max_drawdown=-0.55),
        AssetRiskMetrics(symbol="ETH", expected_return=0.10, volatility=0.95, max_drawdown=-0.60),
        AssetRiskMetrics(symbol="SOL", expected_return=0.16, volatility=1.20, max_drawdown=-0.70),
    ]

    constraints = AllocationConstraints(max_positions=3)

    w_cons = allocate_weights(RiskTolerance.CONSERVATIVE, assets, constraints)
    w_aggr = allocate_weights(RiskTolerance.AGGRESSIVE, assets, constraints)

    assert _sum_close_to_one(w_cons)
    assert _sum_close_to_one(w_aggr)

    # sanity expectation:
    # aggressive should not allocate less to the highest expected_return asset than conservative
    assert w_aggr["SOL"] >= w_cons["SOL"]

def test_allocate_weights_respects_max_positions():
    assets = [
        AssetRiskMetrics(symbol="BTC", expected_return=0.12, volatility=0.80, max_drawdown=-0.55),
        AssetRiskMetrics(symbol="ETH", expected_return=0.10, volatility=0.95, max_drawdown=-0.60),
        AssetRiskMetrics(symbol="SOL", expected_return=0.16, volatility=1.20, max_drawdown=-0.70),
        AssetRiskMetrics(symbol="ADA", expected_return=0.08, volatility=0.70, max_drawdown=-0.50),
    ]

    constraints = AllocationConstraints(max_positions=2)

    w = allocate_weights(RiskTolerance.MODERATE, assets, constraints)

    assert len(w) == 2
    assert _sum_close_to_one(w)

    for v in w.values():
        assert v >= 0.0
        assert math.isfinite(v)

def test_allocate_weights_respects_cap_per_asset():
    assets = [
        AssetRiskMetrics(symbol="BTC", expected_return=0.50, volatility=0.10, max_drawdown=-0.05),
        AssetRiskMetrics(symbol="ETH", expected_return=0.05, volatility=1.50, max_drawdown=-0.80),
        AssetRiskMetrics(symbol="SOL", expected_return=0.04, volatility=1.60, max_drawdown=-0.85),
    ]

    constraints = AllocationConstraints(max_positions=3, max_weight_per_asset=0.60)

    w = allocate_weights(RiskTolerance.CONSERVATIVE, assets, constraints)

    assert _sum_close_to_one(w)
    assert max(w.values()) <= 0.60 + 1e-9