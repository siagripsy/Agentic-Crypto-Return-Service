from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

import pandas as pd
import time
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
    t0 = time.perf_counter()
    print("[run_portfolio_pipeline] start")
    print(f"[run_portfolio_pipeline] symbols={list(assets.keys())}")
    print(
        f"[run_portfolio_pipeline] model_type={cfg.model_type} "
        f"horizon_days={cfg.horizon_days} n_scenarios={cfg.n_scenarios} "
        f"seed={cfg.seed}"
    )

    confidence_levels = cfg.confidence_levels or [0.95]
    risk_cfg = RiskConfig(confidence_levels=confidence_levels)

    scenario_outputs: Dict[str, Dict[str, Any]] = {}
    risks: Dict[str, RiskReport] = {}

    for sym, dfs in assets.items():
        asset_t0 = time.perf_counter()
        print(f"[run_portfolio_pipeline] processing symbol={sym}")

        price_df: Optional[pd.DataFrame] = dfs.get("price_df")
        features_df: Optional[pd.DataFrame] = dfs.get("features_df")

        if price_df is None and features_df is None:
            raise ValueError(f"No input data provided for symbol={sym}")

        price_rows = len(price_df) if price_df is not None else 0
        feature_rows = len(features_df) if features_df is not None else 0
        print(
            f"[run_portfolio_pipeline] {sym} price_rows={price_rows} "
            f"feature_rows={feature_rows}"
        )

        try:
            eng = ScenarioEngine(price_df=price_df, features_df=features_df)

            scfg = ScenarioConfig(
                asset=sym,
                horizon_days=int(cfg.horizon_days),
                n_scenarios=int(cfg.n_scenarios),
                seed=int(cfg.seed),
                model_type=cfg.model_type,  # type: ignore[arg-type]
            )

            print(f"[run_portfolio_pipeline] {sym} scenario generation start")
            sc_t0 = time.perf_counter()
            out = eng.run(scfg)
            sc_dt = time.perf_counter() - sc_t0
            print(
                f"[run_portfolio_pipeline] {sym} scenario generation done "
                f"in {sc_dt:.2f}s; output_keys={list(out.keys())}"
            )

            # Optional payload slimming:
            # if the frontend does not need raw paths for portfolio,
            # uncomment this block to reduce response size dramatically.
            #
            # if isinstance(out, dict) and "paths" in out:
            #     out = dict(out)
            #     out.pop("paths", None)

            scenario_outputs[sym] = out

            print(f"[run_portfolio_pipeline] {sym} risk computation start")
            risk_t0 = time.perf_counter()
            rr = compute_risk(out, risk_cfg)
            risk_dt = time.perf_counter() - risk_t0
            print(
                f"[run_portfolio_pipeline] {sym} risk computation done "
                f"in {risk_dt:.2f}s"
            )

            risks[sym] = rr

        except Exception as e:
            print(
                f"[run_portfolio_pipeline] ERROR for symbol={sym} "
                f"model_type={cfg.model_type}: {type(e).__name__}: {e}"
            )
            raise

        asset_dt = time.perf_counter() - asset_t0
        print(f"[run_portfolio_pipeline] finished symbol={sym} in {asset_dt:.2f}s")

    print("[run_portfolio_pipeline] building portfolio constraints")
    constraints = PortfolioConstraints(
        user_risk_tolerance=float(cfg.user_risk_tolerance),
        max_weight_per_asset=float(cfg.max_weight_per_asset),
        min_weight_per_asset=float(cfg.min_weight_per_asset),
        top_k=int(cfg.top_k),
        allow_cash=bool(cfg.allow_cash),
    )

    try:
        print("[run_portfolio_pipeline] portfolio construction start")
        pf_t0 = time.perf_counter()
        portfolio: PortfolioResult = build_portfolio(scenario_outputs, risks, constraints)
        pf_dt = time.perf_counter() - pf_t0
        print(f"[run_portfolio_pipeline] portfolio construction done in {pf_dt:.2f}s")
    except Exception as e:
        print(f"[run_portfolio_pipeline] ERROR in build_portfolio: {type(e).__name__}: {e}")
        raise

    total_dt = time.perf_counter() - t0
    print(f"[run_portfolio_pipeline] done total_time={total_dt:.2f}s")

    return {
        "scenarios": scenario_outputs,
        "risks": risks,
        "portfolio": portfolio,
    }
