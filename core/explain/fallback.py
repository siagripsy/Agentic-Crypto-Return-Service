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


def _fmt_pct_short(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    try:
        return f"{100.0 * float(x):.1f}%"
    except Exception:
        return "N/A"


def _fmt_num(x: Optional[float], digits: int = 2) -> str:
    if x is None:
        return "N/A"
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "N/A"


def explain_crypto_return_service_fallback(payload: Dict[str, Any]) -> Dict[str, Any]:
    regime_matching = payload.get("regime_matching") or {}
    scenario_engine = payload.get("scenario_engine") or {}
    risks = payload.get("risks") or {}
    portfolio = payload.get("portfolio") or {}
    input_payload = payload.get("input") or {}

    asset_names = list((portfolio.get("weights") or {}).keys()) or list(regime_matching.keys())
    capital = input_payload.get("capital")
    horizon_days = input_payload.get("horizon_days")
    n_scenarios = input_payload.get("n_scenarios")
    risk_tolerance = input_payload.get("risk_tolerance")

    regime_asset = None
    regime_prob = None
    regime_mean_profit = None
    regime_mean_dd = None
    for asset, block in regime_matching.items():
        summary = block.get("summary") or {}
        prob_profit = summary.get("prob_profit")
        if prob_profit is None:
            continue
        if regime_prob is None or float(prob_profit) > float(regime_prob):
            regime_prob = float(prob_profit)
            regime_asset = asset
            regime_mean_profit = (summary.get("profit_analysis") or {}).get("mean_profit")
            regime_mean_dd = (summary.get("drawdown_analysis") or {}).get("mean_max_drawdown")

    scenario_asset = None
    scenario_median = None
    scenario_range_low = None
    scenario_range_high = None
    for asset, block in scenario_engine.items():
        summary = block.get("summary") or {}
        terminal_median = summary.get("terminal_median")
        if terminal_median is None:
            continue
        if scenario_median is None or float(terminal_median) > float(scenario_median):
            scenario_asset = asset
            scenario_median = float(terminal_median)
            scenario_range_low = summary.get("terminal_p05")
            scenario_range_high = summary.get("terminal_p95")

    risk_asset = None
    risk_cvar = None
    for asset, block in risks.items():
        cvar_map = block.get("cvar") or {}
        cvar_value = next(iter(cvar_map.values()), None)
        if cvar_value is None:
            continue
        cvar_value = float(cvar_value)
        if risk_cvar is None or cvar_value < risk_cvar:
            risk_asset = asset
            risk_cvar = cvar_value

    weights = portfolio.get("weights") or {}
    top_weight_asset = None
    top_weight_value = None
    if isinstance(weights, dict) and weights:
        top_weight_asset, top_weight_value = max(weights.items(), key=lambda item: float(item[1]))

    overall_parts: List[str] = []
    if asset_names:
        overall_parts.append(f"The analysis covers {len(asset_names)} asset(s) across regime matching, scenario simulation, and portfolio risk.")
    if horizon_days is not None and n_scenarios is not None:
        overall_parts.append(
            f"It uses a {int(horizon_days)}-day horizon with {int(n_scenarios)} simulated scenarios per asset."
        )
    if top_weight_asset is not None and top_weight_value is not None:
        overall_parts.append(
            f"The largest portfolio weight is {top_weight_asset} at {_fmt_pct_short(float(top_weight_value))} of capital."
        )
    if capital is not None:
        overall_parts.append(f"The request evaluates a capital base of ${_fmt_num(float(capital), 0)}.")
    if risk_tolerance is not None:
        overall_parts.append(
            f"The requested risk tolerance is {_fmt_pct_short(float(risk_tolerance))}, which shapes how aggressively the final allocation can lean into return."
        )

    while len(overall_parts) < 4:
        overall_parts.append("All outputs should be read as model-based estimates with meaningful uncertainty.")

    regime_bullets = [
        (
            f"{regime_asset} had the strongest regime match profit rate at {_fmt_pct_short(regime_prob)}"
            if regime_asset is not None and regime_prob is not None
            else "Historical regime matches are summarized from similar prior windows for each selected asset."
        )
        + ".",
        (
            f"Its average gain across profitable matches was {_fmt_pct_short(regime_mean_profit)}."
            if regime_mean_profit is not None
            else "The profitable match average is only reported when prior profitable windows were available."
        ),
        (
            f"Average drawdown across those matched windows was {_fmt_pct_short(regime_mean_dd)}."
            if regime_mean_dd is not None
            else "Drawdown estimates from matched windows show that similar setups can still experience losses before the horizon ends."
        ),
        "The regime charts should be read as analog evidence, so a strong similarity score does not guarantee the same next move.",
        "Matches above the 0% return line represent historically profitable forward windows, while points below it show loss-making analogs that matter for downside planning.",
    ]

    scenario_bullets = [
        (
            f"{scenario_asset} has the highest median terminal scenario price at {_fmt_num(scenario_median)}."
            if scenario_asset is not None and scenario_median is not None
            else "Scenario paths summarize a distribution of possible future prices rather than a single forecast."
        ),
        (
            f"For {scenario_asset}, the central scenario range runs from {_fmt_num(scenario_range_low)} to {_fmt_num(scenario_range_high)}."
            if scenario_asset is not None and scenario_range_low is not None and scenario_range_high is not None
            else "Wide percentile bands indicate more uncertainty around the future path."
        ),
        "Scenario results should be read as simulated ranges, so the outer bands matter as much as the middle path.",
        "A wider gap between the lower and upper percentile bands means the asset has less concentrated forecast outcomes over the requested horizon.",
        "The terminal distribution box plot helps separate assets with tight but moderate outcomes from assets with higher upside and higher dispersion.",
    ]

    portfolio_expected_return = portfolio.get("portfolio_expected_return")
    portfolio_cvar = portfolio.get("portfolio_cvar")
    portfolio_max_drawdown = portfolio.get("portfolio_max_drawdown_est")
    risk_bullets = [
        (
            f"The largest tail-loss estimate among the assets is {risk_asset} with CVaR {_fmt_pct_short(risk_cvar)}."
            if risk_asset is not None and risk_cvar is not None
            else "Risk metrics compare downside severity across the selected assets."
        ),
        (
            f"The portfolio mean expected return is {_fmt_pct_short(portfolio_expected_return)} with portfolio CVaR {_fmt_pct_short(portfolio_cvar)}."
            if portfolio_expected_return is not None and portfolio_cvar is not None
            else "Portfolio summary metrics combine expected return with downside risk estimates."
        ),
        (
            f"Estimated portfolio max drawdown is {_fmt_pct_short(portfolio_max_drawdown)}."
            if portfolio_max_drawdown is not None
            else "Max drawdown estimates help show how deep losses could become in adverse scenarios."
        ),
        (
            f"The portfolio is most concentrated in {top_weight_asset} at {_fmt_pct_short(float(top_weight_value))}, so that asset has the largest influence on overall outcomes."
            if top_weight_asset is not None and top_weight_value is not None
            else "Weight concentration matters because a single large allocation can dominate the portfolio result."
        ),
        "Read expected return together with CVaR and drawdown rather than in isolation, because the highest-return asset is not always the best portfolio building block.",
    ]

    return {
        "mode": "fallback",
        "disclaimer": DISCLAIMER,
        "overall_summary": " ".join(overall_parts[:5]),
        "sections": {
            "regime_matching": {
                "headline": "Historical analogs provide context, not certainty.",
                "bullets": regime_bullets,
            },
            "scenario_engine": {
                "headline": "Simulated paths show a range of possible price outcomes.",
                "bullets": scenario_bullets,
            },
            "risk_portfolio": {
                "headline": "Portfolio metrics balance expected return against downside risk.",
                "bullets": risk_bullets,
            },
        },
    }
