from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True)
class AssetRiskMetrics:
    symbol: str
    volatility: float       # must be consistent across assets (same scale/horizon)
    max_drawdown: float     # negative value, e.g. -0.35
    expected_return: float  # must be consistent across assets (same scale/horizon)


@dataclass(frozen=True)
class AllocationConstraints:
    max_positions: Optional[int] = None
    max_weight_per_asset: float = 0.60
    min_weight_per_asset: float = 0.00
    allow_short: bool = False  # baseline: not supported yet


def _validate_inputs(
    assets: List[AssetRiskMetrics],
    constraints: AllocationConstraints,
) -> None:
    if not assets:
        raise ValueError("assets must not be empty")

    if constraints.allow_short:
        raise NotImplementedError("Shorting is not supported in this baseline allocator.")

    if constraints.max_weight_per_asset <= 0 or constraints.max_weight_per_asset > 1:
        raise ValueError("max_weight_per_asset must be in (0, 1].")

    if constraints.min_weight_per_asset < 0 or constraints.min_weight_per_asset >= 1:
        raise ValueError("min_weight_per_asset must be in [0, 1).")

    if constraints.min_weight_per_asset > constraints.max_weight_per_asset:
        raise ValueError("min_weight_per_asset cannot exceed max_weight_per_asset.")

    if constraints.max_positions is not None and constraints.max_positions <= 0:
        raise ValueError("max_positions must be positive when provided.")


def _risk_score(a: AssetRiskMetrics) -> float:
    """
    Lower is safer.
    A simple deterministic baseline:
      risk_score = volatility + abs(max_drawdown)

    Notes:
      - This is intentionally simple and explainable.
      - Later we can improve with scaling, percentiles, regime-conditioned risk, etc.
    """
    return float(a.volatility) + abs(float(a.max_drawdown))


def _select_universe(
    assets: List[AssetRiskMetrics],
    constraints: AllocationConstraints,
    risk_tolerance: RiskTolerance,
) -> List[AssetRiskMetrics]:
    """
    Choose which assets to include when max_positions is set.
    Conservative: prefer safest (lowest risk_score)
    Aggressive: prefer highest expected_return (tie-break by risk)
    Moderate: mix (expected_return - risk_score)
    """
    if constraints.max_positions is None or constraints.max_positions >= len(assets):
        return assets

    scored: List[Tuple[AssetRiskMetrics, float]] = []
    for a in assets:
        r = _risk_score(a)
        if risk_tolerance == RiskTolerance.CONSERVATIVE:
            key = r
        elif risk_tolerance == RiskTolerance.AGGRESSIVE:
            key = -float(a.expected_return)  # higher return first
        else:
            key = -(float(a.expected_return) - r)  # higher (return - risk) first
        scored.append((a, key))

    scored.sort(key=lambda x: (x[1], x[0].symbol))
    picked = [a for a, _ in scored[: constraints.max_positions]]
    return picked


def _raw_weights(
    risk_tolerance: RiskTolerance,
    assets: List[AssetRiskMetrics],
) -> Dict[str, float]:
    """
    Produce unnormalized weights (positive).
    Conservative: inverse risk
    Moderate: balance (return) vs (risk)
    Aggressive: emphasize expected_return but still penalize extreme risk
    """
    eps = 1e-12
    w: Dict[str, float] = {}

    for a in assets:
        r = _risk_score(a)
        er = float(a.expected_return)

        if risk_tolerance == RiskTolerance.CONSERVATIVE:
            score = 1.0 / (r + eps)
        elif risk_tolerance == RiskTolerance.MODERATE:
            score = max(eps, (er + 1.0) / (r + 1.0))
        else:
            score = max(eps, (er + 1.0) / ((r + 1.0) ** 0.5))

        w[a.symbol] = float(score)

    return w


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Invalid weights: sum must be positive.")
    return {k: v / total for k, v in weights.items()}


def _apply_caps_and_floors(
    weights: Dict[str, float],
    constraints: AllocationConstraints,
) -> Dict[str, float]:
    """
    Apply max/min weight per asset with a simple iterative renormalization.
    Deterministic behaviour: always process symbols in sorted order.
    """
    w = dict(weights)

    # 1) Apply caps
    for sym in sorted(w.keys()):
        if w[sym] > constraints.max_weight_per_asset:
            w[sym] = constraints.max_weight_per_asset

    # 2) Apply floors
    for sym in sorted(w.keys()):
        if w[sym] < constraints.min_weight_per_asset:
            w[sym] = constraints.min_weight_per_asset

    # 3) Renormalize while respecting caps/floors (simple loop)
    # If constraints are impossible, we will best-effort normalize without violating caps,
    # and raise only if sum becomes invalid.
    for _ in range(10):
        total = sum(w.values())
        if abs(total - 1.0) < 1e-9:
            return w

        # If total is 0 or negative, invalid
        if total <= 0:
            raise ValueError("Constraints produced invalid weights (sum <= 0).")

        # Scale non-fixed weights to make sum 1.0
        # Fixed weights are those at caps or floors.
        fixed = set()
        for sym in w:
            if abs(w[sym] - constraints.max_weight_per_asset) < 1e-12:
                fixed.add(sym)
            if abs(w[sym] - constraints.min_weight_per_asset) < 1e-12:
                fixed.add(sym)

        free_syms = [s for s in sorted(w.keys()) if s not in fixed]
        if not free_syms:
            # nothing we can scale, return normalized best-effort
            return _normalize(w)

        fixed_sum = sum(w[s] for s in fixed)
        free_sum = sum(w[s] for s in free_syms)

        target_free_sum = 1.0 - fixed_sum
        if target_free_sum <= 0:
            # too much fixed weight, best-effort normalize
            return _normalize(w)

        scale = target_free_sum / max(1e-12, free_sum)
        for s in free_syms:
            w[s] *= scale

        # Re-apply caps/floors after scaling
        for sym in sorted(w.keys()):
            if w[sym] > constraints.max_weight_per_asset:
                w[sym] = constraints.max_weight_per_asset
            if w[sym] < constraints.min_weight_per_asset:
                w[sym] = constraints.min_weight_per_asset

    return _normalize(w)


def allocate_weights(
    risk_tolerance: RiskTolerance,
    assets: List[AssetRiskMetrics],
    constraints: Optional[AllocationConstraints] = None,
) -> Dict[str, float]:
    """
    Baseline rule based allocator.

    Output:
      dict of {symbol: weight}, weights sum to 1.0

    High-level logic:
      1) pick universe (if max_positions set)
      2) compute raw weights based on risk_tolerance
      3) normalize
      4) apply caps/floors and renormalize
    """
    if constraints is None:
        constraints = AllocationConstraints()

    _validate_inputs(assets, constraints)

    selected = _select_universe(assets, constraints, risk_tolerance)
    raw = _raw_weights(risk_tolerance, selected)
    normalized = _normalize(raw)
    final = _apply_caps_and_floors(normalized, constraints)

    # ensure deterministic order in output (helps tests)
    return {k: final[k] for k in sorted(final.keys())}
