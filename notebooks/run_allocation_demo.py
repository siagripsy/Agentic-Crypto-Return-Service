import sys
from pathlib import Path

# Add project root to Python path so `core` can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))




from core.portfolio.allocation_rules import (
    AssetRiskMetrics,
    AllocationConstraints,
    RiskTolerance,
    allocate_weights,
)

assets = [
    AssetRiskMetrics("BTC", volatility=0.40, max_drawdown=-0.55, expected_return=0.35),
    AssetRiskMetrics("ETH", volatility=0.55, max_drawdown=-0.65, expected_return=0.45),
    AssetRiskMetrics("SOL", volatility=0.85, max_drawdown=-0.80, expected_return=0.70),
]

constraints = AllocationConstraints(
    max_positions=None,
    max_weight_per_asset=0.60,
    min_weight_per_asset=0.00,
)

for tol in [RiskTolerance.CONSERVATIVE, RiskTolerance.MODERATE, RiskTolerance.AGGRESSIVE]:
    w = allocate_weights(tol, assets, constraints=constraints)
    print(f"\nRiskTolerance = {tol.value}")
    for k, v in w.items():
        print(f"  {k}: {v:.4f}")
    print(f"  SUM: {sum(w.values()):.4f}")
