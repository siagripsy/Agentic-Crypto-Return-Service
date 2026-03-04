from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

import pandas as pd

from core.pipelines.scenario_engine import ScenarioEngine, ScenarioConfig
from core.risk import RiskConfig, RiskReport, compute_risk
from core.portfolio import PortfolioConstraints, PortfolioResult, build_portfolio


@dataclass
class PortfolioPipelineConfig:
    # scenario config
    horizon_days: int
    n_scenarios: int = 10_000
    seed: int = 42
    model_type: str = "quantile_ml_walk_forward"  # default aligns with your latest work

    # risk config
    confidence_levels: list[float] = None  # type: ignore

    # portfolio constraints
    user_risk_tolerance: float = 50.0
    top_k: int = 5
    max_weight_per_asset: float = 0.40
    min_weight_per_asset: float = 0.00
    allow_cash: bool = True


def run_portfolio_pipeline(
    *,
    assets: Dict[str, Dict[str, pd.DataFrame]],
    cfg: PortfolioPipelineConfig,
) -> Dict[str, Any]:
    """
    assets: dict[symbol] -> {"price_df": df, "features_df": df}
      - price_df required for monte_carlo
      - features_df required for regime_similarity / quantile_ml_walk_forward

    Returns:
      {
        "scenarios": dict[symbol] -> scenario_engine output,
        "risks": dict[symbol] -> RiskReport,
        "portfolio": PortfolioResult
      }
    """
    confidence_levels = cfg.confidence_levels or [0.95]
    risk_cfg = RiskConfig(confidence_levels=confidence_levels)

    scenario_outputs: Dict[str, Dict[str, Any]] = {}
    risks: Dict[str, RiskReport] = {}

    for sym, dfs in assets.items():
        price_df: Optional[pd.DataFrame] = dfs.get("price_df")
        features_df: Optional[pd.DataFrame] = dfs.get("features_df")

        eng = ScenarioEngine(price_df=price_df, features_df=features_df)

        scfg = ScenarioConfig(
            asset=sym,
            horizon_days=int(cfg.horizon_days),
            n_scenarios=int(cfg.n_scenarios),
            seed=int(cfg.seed),
            model_type=cfg.model_type,  # type: ignore
        )

        out = eng.run(scfg)
        scenario_outputs[sym] = out
        risks[sym] = compute_risk(out, risk_cfg)

    constraints = PortfolioConstraints(
        user_risk_tolerance=float(cfg.user_risk_tolerance),
        max_weight_per_asset=float(cfg.max_weight_per_asset),
        min_weight_per_asset=float(cfg.min_weight_per_asset),
        top_k=int(cfg.top_k),
        allow_cash=bool(cfg.allow_cash),
    )

    portfolio: PortfolioResult = build_portfolio(scenario_outputs, risks, constraints)

    return {
        "scenarios": scenario_outputs,
        "risks": risks,
        "portfolio": portfolio,
    }
