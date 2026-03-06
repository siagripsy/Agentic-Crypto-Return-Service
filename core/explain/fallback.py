# core/explain/fallback.py
from __future__ import annotations

from typing import Any, Dict, List, Optional


DISCLAIMER = (
    "Disclaimer: This explanation is informational only and not financial advice. "
    "Crypto returns are highly uncertain; results are based on historical patterns and simulations."
)


def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    try:
        return f"{100.0 * float(x):.2f}%"
    except Exception:
        return "N/A"


def _first_present(d: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def explain_forecast_fallback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: a dict that looks like your forecast response:
      - engine, horizon_days, alpha, summary/risk OR metrics/risk_curve_metrics, assumptions...
    Returns:
      {
        "mode": "fallback",
        "disclaimer": "...",
        "bullets": [...],
        "narrative": "..."
      }
    """
    engine = payload.get("engine") or payload.get("assumptions", {}).get("engine")
    horizon_days = payload.get("horizon_days")
    alpha = payload.get("alpha")

    bullets: List[str] = []
    bullets.append(f"Engine used: {engine}.")
    if horizon_days is not None:
        bullets.append(f"Forecast horizon: {horizon_days} trading days.")
    if alpha is not None:
        bullets.append(f"Primary risk level (alpha): {alpha} (lower means more conservative tail risk).")

    # Try fast-regime-fixed summary
    summary = payload.get("summary") or {}
    if isinstance(summary, dict) and summary:
        mean = _first_present(summary, ["mean", "mean_log", "mean_simple"])
        p05 = _first_present(summary, ["p05", "p05_log", "p05_simple"])
        p95 = _first_present(summary, ["p95", "p95_log", "p95_simple"])
        bullets.append(f"Expected return (mean): {_fmt_pct(mean)}.")
        bullets.append(f"Downside (5th pct): {_fmt_pct(p05)}; Upside (95th pct): {_fmt_pct(p95)}.")
    else:
        # Try path-based metrics
        metrics = payload.get("metrics")
        # metrics can be {"log":..., "simple":...} or a single dict
        m = None
        if isinstance(metrics, dict) and "simple" in metrics:
            m = metrics["simple"]
        elif isinstance(metrics, dict):
            m = metrics

        if isinstance(m, dict):
            hrs = m.get("horizon_return_summary", {})
            if isinstance(hrs, dict) and hrs:
                bullets.append(f"Expected return (mean): {_fmt_pct(hrs.get('mean'))}.")
                bullets.append(f"Downside (p05): {_fmt_pct(hrs.get('p05'))}; Upside (p95): {_fmt_pct(hrs.get('p95'))}.")
            v = m.get("VaR_CVaR_horizon_return", {})
            if isinstance(v, dict) and v:
                bullets.append(f"Tail risk (VaR): {_fmt_pct(v.get('VaR'))}; (CVaR): {_fmt_pct(v.get('CVaR'))}.")

    narrative = (
        "This forecast summarizes simulated outcomes over the requested horizon. "
        "Focus on the downside tail (VaR/CVaR or p05) to understand potential losses under adverse scenarios, "
        "and compare it to the expected return to judge risk-reward balance."
    )

    return {
        "mode": "fallback",
        "disclaimer": DISCLAIMER,
        "bullets": bullets,
        "narrative": narrative,
    }


def explain_portfolio_fallback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: dict that looks like your /portfolio/recommend response:
      - portfolio: weights/details/portfolio_expected_return/portfolio_cvar/...
      - risks: per-asset RiskReport dicts
      - assumptions: contains engine, constraints, etc.
    """
    assumptions = payload.get("assumptions", {})
    portfolio = payload.get("portfolio", {}) or {}

    engine = assumptions.get("engine")
    horizon_days = assumptions.get("horizon_days")
    conf = assumptions.get("confidence_levels")
    constraints = assumptions.get("portfolio_constraints", {})

    bullets: List[str] = []
    bullets.append(f"Portfolio engine: {engine}.")
    if horizon_days is not None:
        bullets.append(f"Horizon: {horizon_days} trading days.")
    if conf:
        bullets.append(f"Confidence levels used for risk: {conf}.")
    if constraints:
        bullets.append(
            f"Constraints: top_k={constraints.get('top_k')}, "
            f"max_weight={constraints.get('max_weight')}, "
            f"min_weight={constraints.get('min_weight')}, "
            f"allow_cash={constraints.get('allow_cash')}."
        )

    weights = portfolio.get("weights", {}) if isinstance(portfolio, dict) else {}
    if isinstance(weights, dict) and weights:
        # show top allocations
        sorted_w = sorted(weights.items(), key=lambda kv: float(kv[1]), reverse=True)
        top = ", ".join([f"{k}: {100*float(v):.1f}%" for k, v in sorted_w[:5]])
        bullets.append(f"Top allocations: {top}.")

    per = portfolio.get("portfolio_expected_return")
    pcvar = portfolio.get("portfolio_cvar")
    pdd = portfolio.get("portfolio_max_drawdown_est")
    if per is not None:
        bullets.append(f"Portfolio expected return (mean): {_fmt_pct(per)}.")
    if pcvar is not None:
        bullets.append(f"Portfolio tail risk (CVaR): {_fmt_pct(pcvar)}.")
    if pdd is not None:
        bullets.append(f"Estimated portfolio max drawdown: {_fmt_pct(pdd)}.")

    narrative = (
        "The recommended weights balance expected return versus tail risk given your constraints. "
        "If you want a more conservative portfolio, lower user_risk_tolerance, reduce max_weight, "
        "or increase the confidence level (e.g., 0.99) to emphasize downside protection."
    )

    return {
        "mode": "fallback",
        "disclaimer": DISCLAIMER,
        "bullets": bullets,
        "narrative": narrative,
    }