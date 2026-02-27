from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RiskConfig:
    """
    Matches interfaces.md conceptually, but uses our current scenario metrics.
    confidence_levels: e.g. [0.90, 0.95, 0.99]
    Note: scenario_metrics currently uses alpha (e.g. 0.05). We will map.
    """
    confidence_levels: List[float] = field(default_factory=lambda: [0.95])
    stress_mode: str | None = None


@dataclass
class RiskReport:
    symbol: str
    horizon_days: int

    # e.g. {"p95": -0.12} means 95% VaR on horizon return
    var: Dict[str, float]

    # e.g. {"p95": -0.18}
    cvar: Dict[str, float]

    # optional, negative number (drawdown)
    max_drawdown_est: float | None = None

    # anything extra we want to keep for explainability
    tail_metrics: Dict[str, Any] = field(default_factory=dict)

    notes: List[str] = field(default_factory=list)
