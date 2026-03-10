from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from core.regime_detection.regime_detection import run_regime_historical_matching
from core.pipelines.scenario_engine import ScenarioEngine, ScenarioConfig
from core.risk.risk import compute_risk
from core.risk.schemas import RiskConfig
from core.portfolio.portfolio import build_portfolio
from core.portfolio.schemas import PortfolioConstraints


FEATURES_DIR = Path("data/processed/features")

MATCH_WINDOW_DAYS = 30
TOP_N = 10
SIMILARITY_METRIC = "cosine"
EMBARGO_DAYS = 5
LATENT_DIM = 16
TRAIN_EPOCHS = 40


def run_Crypto_Return_Service(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates:
    1) Regime Matching
    2) Scenario Engine
    3) Risk Assessment + Portfolio Allocation
    """
    assets = user_input["assets"]

    regime_outputs: Dict[str, Any] = {}
    scenario_outputs: Dict[str, Any] = {}
    risks: Dict[str, Any] = {}

    for ticker in assets.keys():
        features_path = FEATURES_DIR / f"{str.replace(ticker,'-USD','')}_features.csv"
        df = pd.read_csv(features_path)
        
        #=======================================
        # Step 1: Regime Matching
        #=======================================
        regime_outputs[ticker] = run_regime_historical_matching(
            features_csv_path=str(features_path),
            ticker=ticker,
            match_window_days=MATCH_WINDOW_DAYS,
            top_n=TOP_N,
            horizon_days=user_input["horizon_days"],
            similarity_metric=SIMILARITY_METRIC,
            embargo_days=EMBARGO_DAYS,
            latent_dim=LATENT_DIM,
            train_epochs=TRAIN_EPOCHS,
            force_retrain=False,
        )

        
        #=======================================
        #  Step 2: Scenario Engine
        #=======================================        
        engine = ScenarioEngine(features_df=df)
        scenario_outputs[ticker] = engine.run(
            ScenarioConfig(
                asset=ticker,
                horizon_days=user_input["horizon_days"],
                n_scenarios=user_input["n_scenarios"],
                model_type="quantile_ml_walk_forward",
            )
        )

        
        #=======================================
        # Step 3: Risk
        #=======================================   
        scenario_for_risk = {
            "asset": ticker,
            "summary": {
                "horizon_days": user_input["horizon_days"],
            },
            "metrics": scenario_outputs[ticker]["metrics"],
        }

        risk_cfg = RiskConfig()
        risks[ticker] = compute_risk(scenario_for_risk, risk_cfg)

        

        #=======================================
        # Step 4: Portfolio Allocation
        #=======================================   
        user_rt = user_input["risk_tolerance"]

        constraints = PortfolioConstraints(
            user_risk_tolerance=user_rt,
            top_k=len(user_input["assets"]),
            max_weight_per_asset=0.70,
            min_weight_per_asset=0.00,
            allow_cash=False,
        )

        portfolio = build_portfolio(
            scenario_outputs,
            risks,
            constraints
        )

    return {
        "input": user_input,
        "regime_matching": regime_outputs,
        "scenario_engine": scenario_outputs,
        "risks": risks,
        "portfolio": portfolio,
    }