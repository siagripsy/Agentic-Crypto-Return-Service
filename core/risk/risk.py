from __future__ import annotations

from typing import Any, Dict

from core.risk.schemas import RiskConfig, RiskReport


def compute_risk(scenarios: Dict[str, Any], config: RiskConfig) -> RiskReport:
    """
    scenarios: the dict returned by ScenarioEngine.run() for a single asset.
    We treat it as our current internal ScenarioSet.

    Expected keys:
      - "asset"
      - "summary" (contains horizon_days)
      - "metrics" (from compute_scenario_metrics)
    """
    asset = str(scenarios.get("asset", ""))
    summary = scenarios.get("summary", {}) or {}
    metrics = scenarios.get("metrics", {}) or {}

    horizon_days = int(summary.get("horizon_days", metrics.get("horizon_days", 0)))

    # Our scenario_metrics computes VaR/CVaR using alpha (e.g. 0.05).
    # interfaces wants confidence_levels (e.g. 0.95). Map: alpha = 1 - confidence.
    var_map: Dict[str, float] = {}
    cvar_map: Dict[str, float] = {}

    # If metrics already has VaR/CVaR at one alpha, use that.
    # Later we can recompute for multiple levels by calling compute_scenario_metrics with different alpha.
    hrc = metrics.get("VaR_CVaR_horizon_return", {}) or {}
    var_val = float(hrc.get("VaR", float("nan")))
    cvar_val = float(hrc.get("CVaR", float("nan")))

    # default label based on first confidence level
    conf = float(config.confidence_levels[0]) if config.confidence_levels else 0.95
    label = f"p{int(round(conf * 100))}"

    var_map[label] = var_val
    cvar_map[label] = cvar_val

    mdd_summary = metrics.get("max_drawdown_summary", {}) or {}
    max_dd_est = float(mdd_summary.get("mean", float("nan")))

    tail_metrics = {
        "prob_profit": float(metrics.get("prob_profit", float("nan"))),
        "prob_loss": float(metrics.get("prob_loss", float("nan"))),
        "horizon_return_summary": metrics.get("horizon_return_summary", {}),
        "terminal_price_summary": metrics.get("terminal_price_summary", {}),
        "max_drawdown_summary": mdd_summary,
    }

    notes = []
    if config.stress_mode:
        notes.append(f"stress_mode={config.stress_mode} (not implemented yet)")

    return RiskReport(
        symbol=asset,
        horizon_days=horizon_days,
        var=var_map,
        cvar=cvar_map,
        max_drawdown_est=max_dd_est,
        tail_metrics=tail_metrics,
        notes=notes,
    )
