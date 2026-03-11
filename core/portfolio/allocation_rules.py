"""
DEPRECATED: This module used to hold simple allocation rules for early demos.

From W8 onwards, portfolio allocation is implemented in:
  - core.portfolio.portfolio.build_portfolio
  - core.portfolio.schemas (PortfolioConstraints, PortfolioResult)

Keep this wrapper to avoid breaking older notebooks/scripts.
"""
from __future__ import annotations

from typing import Any, Dict
import warnings

from core.portfolio import build_portfolio, PortfolioConstraints
from core.risk import RiskReport


def allocate(
    *,
    scenarios: Dict[str, Dict[str, Any]],
    risks: Dict[str, RiskReport],
    user_risk_tolerance: float,
    top_k: int = 5,
    max_weight_per_asset: float = 0.40,
    min_weight_per_asset: float = 0.00,
    allow_cash: bool = True,
):
    warnings.warn(
        "core.portfolio.allocation_rules.allocate is deprecated. "
        "Use core.portfolio.build_portfolio with PortfolioConstraints instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    constraints = PortfolioConstraints(
        user_risk_tolerance=float(user_risk_tolerance),
        top_k=int(top_k),
        max_weight_per_asset=float(max_weight_per_asset),
        min_weight_per_asset=float(min_weight_per_asset),
        allow_cash=bool(allow_cash),
    )
    return build_portfolio(scenarios, risks, constraints)
