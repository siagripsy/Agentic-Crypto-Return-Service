from __future__ import annotations

from typing import Dict, Any, List, Tuple
import math

from core.risk import RiskReport
from core.portfolio.schemas import PortfolioConstraints, PortfolioResult, AllocationDetail


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _get_expected_return_mean(scenarios: Dict[str, Any]) -> float:
    metrics = scenarios.get("metrics", {}) or {}
    hrs = metrics.get("horizon_return_summary", {}) or {}
    return _safe_float(hrs.get("mean", float("nan")))


def _get_prob_profit(scenarios: Dict[str, Any]) -> float:
    metrics = scenarios.get("metrics", {}) or {}
    return _safe_float(metrics.get("prob_profit", float("nan")))


def _risk_numbers_from_report(r: RiskReport) -> Tuple[float, float]:
    # pick the first key in var/cvar maps (e.g. "p95")
    cvar = float("nan")
    if r.cvar:
        first_key = list(r.cvar.keys())[0]
        cvar = _safe_float(r.cvar.get(first_key))
    mdd = _safe_float(r.max_drawdown_est)
    return cvar, mdd


def build_portfolio(
    scenarios: Dict[str, Dict[str, Any]],
    risks: Dict[str, RiskReport],
    constraints: PortfolioConstraints,
) -> PortfolioResult:
    """
    scenarios: dict[symbol] -> ScenarioEngine.run() output
    risks: dict[symbol] -> RiskReport (from core.risk.compute_risk)
    """
    # map user risk tolerance to a risk penalty lambda:
    # 0 => خیلی محافظه کار => lambda بزرگ
    # 100 => خیلی ریسک پذیر => lambda کوچک
    rt = _clamp(float(constraints.user_risk_tolerance), 0.0, 100.0)
    lam = 3.0 - (rt / 100.0) * 2.5  # 3.0 .. 0.5

    candidates: List[AllocationDetail] = []

    for sym, scen in scenarios.items():
        if sym not in risks:
            continue

        r = risks[sym]
        mu = _get_expected_return_mean(scen)             # expected log return (mean)
        pp = _get_prob_profit(scen)

        cvar, mdd = _risk_numbers_from_report(r)

        # risk magnitude: CVaR and drawdown are usually negative, use absolute size
        risk_mag = 0.0
        if math.isfinite(cvar):
            risk_mag += abs(cvar)
        if math.isfinite(mdd):
            risk_mag += 0.5 * abs(mdd)

        # utility score: return rewarded, risk penalized
        # small bonus for higher probability of profit
        score = 0.0
        if math.isfinite(mu):
            score += mu
        if math.isfinite(pp):
            score += 0.10 * (pp - 0.5)

        score -= lam * risk_mag

        candidates.append(
            AllocationDetail(
                symbol=sym,
                weight=0.0,
                expected_return_mean=mu if math.isfinite(mu) else 0.0,
                prob_profit=pp if math.isfinite(pp) else 0.0,
                cvar=cvar if math.isfinite(cvar) else 0.0,
                max_drawdown_est=mdd if math.isfinite(mdd) else 0.0,
                score=score,
                notes=[],
            )
        )

    # if nothing found, return 100% cash (if allowed) or empty
    if not candidates:
        weights = {"CASH": 1.0} if constraints.allow_cash else {}
        return PortfolioResult(weights=weights, details=[], metadata={"reason": "no_candidates"})

    # sort by score, keep top_k
    candidates.sort(key=lambda x: x.score, reverse=True)
    chosen = candidates[: max(1, int(constraints.top_k))]

    # convert scores to positive weights using softmax-like transform
    scores = [c.score for c in chosen]
    mx = max(scores)
    exps = [math.exp(s - mx) for s in scores]
    denom = sum(exps) if sum(exps) > 0 else 1.0
    raw_w = [e / denom for e in exps]

    # apply max cap, then renormalize
    capped = [_clamp(w, 0.0, float(constraints.max_weight_per_asset)) for w in raw_w]
    total = sum(capped)

    # if we capped too hard, redistribute proportionally among uncapped (simple loop)
    if total > 0:
        capped = [w / total for w in capped]
    else:
        capped = [1.0 / len(capped)] * len(capped)

    # apply min weight (only for selected assets), then renormalize
    if constraints.min_weight_per_asset > 0:
        mins = float(constraints.min_weight_per_asset)
        capped = [max(w, mins) for w in capped]
        total = sum(capped)
        capped = [w / total for w in capped]

    weights: Dict[str, float] = {}
    for c, w in zip(chosen, capped):
        c.weight = float(w)
        weights[c.symbol] = float(w)

    # optional cash allocation for conservative users
    cash_w = 0.0
    if constraints.allow_cash:
        # more conservative => more cash
        cash_w = (1.0 - rt / 100.0) * 0.25  # up to 25% cash
        if cash_w > 0:
            # scale down asset weights to make room
            scale = 1.0 - cash_w
            for k in list(weights.keys()):
                weights[k] *= scale
            weights["CASH"] = cash_w

            for c in chosen:
                c.weight *= scale

    # portfolio-level stats (very simple weighted aggregates)
    port_mu = 0.0
    port_cvar = 0.0
    port_mdd = 0.0
    wsum = 0.0

    for c in chosen:
        w = c.weight
        port_mu += w * c.expected_return_mean
        port_cvar += w * c.cvar
        port_mdd += w * c.max_drawdown_est
        wsum += w

    return PortfolioResult(
        weights=weights,
        details=chosen,
        portfolio_expected_return=port_mu if wsum > 0 else None,
        portfolio_cvar=port_cvar if wsum > 0 else None,
        portfolio_max_drawdown_est=port_mdd if wsum > 0 else None,
        metadata={
            "lambda": lam,
            "top_k": int(constraints.top_k),
            "cash_weight": cash_w,
        },
    )
