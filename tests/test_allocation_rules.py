import math

import pytest

from core.portfolio.allocation_rules import (
    AllocationConstraints,
    AssetRiskMetrics,
    RiskTolerance,
    allocate_weights,
)


def _sample_assets():
    # Simple fake metrics for deterministic behaviour
    return [
        AssetRiskMetrics(symbol="BTC", volatility=0.40, max_drawdown=-0.55, expected_return=0.35),
        AssetRiskMetrics(symbol="ETH", volatility=0.55, max_drawdown=-0.65, expected_return=0.45),
        AssetRiskMetrics(symbol="SOL", volatility=0.85, max_drawdown=-0.80, expected_return=0.70),
    ]


@pytest.mark.parametrize(
    "risk_tol",
    [RiskTolerance.CONSERVATIVE, RiskTolerance.MODERATE, RiskTolerance.AGGRESSIVE],
)
def test_allocate_weights_sum_to_one_and_non_negative(risk_tol):
    assets = _sample_assets()
    w = allocate_weights(risk_tol, assets)

    assert isinstance(w, dict)
    assert set(w.keys()) == {"BTC", "ETH", "SOL"}

    total = sum(w.values())
    assert math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-9)

    for v in w.values():
        assert v >= 0.0


def test_allocate_weights_is_deterministic_order():
    assets = _sample_assets()
    w = allocate_weights(RiskTolerance.MODERATE, assets)

    # output should be sorted by symbol (as implemented)
    assert list(w.keys()) == ["BTC", "ETH", "SOL"]


def test_max_weight_per_asset_cap_is_respected_for_multi_asset_case():
    assets = _sample_assets()
    constraints = AllocationConstraints(max_weight_per_asset=0.50)

    w = allocate_weights(RiskTolerance.CONSERVATIVE, assets, constraints=constraints)

    assert max(w.values()) <= 0.50 + 1e-9
    assert math.isclose(sum(w.values()), 1.0, rel_tol=0, abs_tol=1e-9)


def test_single_asset_best_effort_normalization():
    assets = [AssetRiskMetrics(symbol="BTC", volatility=0.40, max_drawdown=-0.55, expected_return=0.35)]
    constraints = AllocationConstraints(max_weight_per_asset=0.60)

    w = allocate_weights(RiskTolerance.CONSERVATIVE, assets, constraints=constraints)

    # baseline behaviour: must sum to 1.0 even if cap is infeasible without cash
    assert list(w.keys()) == ["BTC"]
    assert math.isclose(w["BTC"], 1.0, rel_tol=0, abs_tol=1e-9)
