from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PortfolioConstraints:
    """
    user_risk_tolerance: 0..100 (0 = خیلی محافظه کار, 100 = خیلی ریسک پذیر)
    max_weight_per_asset: سقف وزن هر دارایی
    min_weight_per_asset: کف وزن هر دارایی (اگر در لیست انتخاب شد)
    top_k: حداکثر تعداد کوین هایی که داخل پورتفوی می آیند
    allow_cash: اگر True باشد بخشی از پورتفوی می تواند نقد باشد
    """
    user_risk_tolerance: float
    max_weight_per_asset: float = 0.40
    min_weight_per_asset: float = 0.00
    top_k: int = 5
    allow_cash: bool = True


@dataclass
class AllocationDetail:
    symbol: str
    weight: float

    # explainability fields
    expected_return_mean: float
    prob_profit: float
    cvar: float
    max_drawdown_est: float

    score: float
    notes: List[str] = field(default_factory=list)


@dataclass
class PortfolioResult:
    weights: Dict[str, float]
    details: List[AllocationDetail]

    # optional overall stats
    portfolio_expected_return: Optional[float] = None
    portfolio_cvar: Optional[float] = None
    portfolio_max_drawdown_est: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
