"""
Scenario engine (orchestrator).

W5 baseline: Monte Carlo (normal shocks) from raw price_df.
W7: Adds pluggable scenario generators, including:
- Regime similarity conditional sampling (features_df)
- Quantile ML Walk-forward scenarios (features_df + trained model artifacts)

This version also computes scenario-based risk/return metrics from generated paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal

import numpy as np
import pandas as pd

from core.models.scenario_generator_base import BaseScenarioGenerator, ScenarioResult
from core.models.monte_carlo_generator import MonteCarloScenarioGenerator

from core.models.regime_similarity_generator import (
    RegimeSimilarityScenarioGenerator,
    RegimeSimilarityConfig,
)

from core.models.quantile_ml_walkforward_generator import (
    QuantileMLWalkForwardScenarioGenerator,
    WalkForwardMLConfig,
)

from core.models.scenario_metrics import compute_scenario_metrics


ModelType = Literal["monte_carlo", "regime_similarity", "quantile_ml_walk_forward"]


@dataclass
class ScenarioConfig:
    asset: str
    horizon_days: int
    n_scenarios: int = 10_000
    seed: int = 42

    # choose which model/generator to use
    model_type: ModelType = "monte_carlo"

    # optional configs for specific models
    regime_cfg: Optional[RegimeSimilarityConfig] = None
    ml_walk_cfg: Optional[WalkForwardMLConfig] = None


class ScenarioEngine:
    """
    Orchestrates scenario generation and keeps a stable output structure.

    Output:
        {
          "asset": ...,
          "distribution": ...,
          "summary": ...,
          "paths": np.ndarray,
          "metadata": ...,
          "metrics": ...
        }

    Inputs:
    - price_df: required for monte_carlo
    - features_df: required for regime_similarity and quantile_ml_walk_forward
    - generator: optional explicit injection (overrides model_type)
    """

    def __init__(
        self,
        *,
        price_df: Optional[pd.DataFrame] = None,
        features_df: Optional[pd.DataFrame] = None,
        generator: Optional[BaseScenarioGenerator] = None,
    ):
        self.price_df = price_df.copy() if price_df is not None else None
        self.features_df = features_df.copy() if features_df is not None else None
        self.generator = generator

    def _select_generator(self, config: ScenarioConfig) -> BaseScenarioGenerator:
        if self.generator is not None:
            return self.generator

        if config.model_type == "monte_carlo":
            if self.price_df is None:
                raise ValueError("price_df is required for model_type='monte_carlo'")
            return MonteCarloScenarioGenerator()

        if config.model_type == "regime_similarity":
            if self.features_df is None:
                raise ValueError("features_df is required for model_type='regime_similarity'")
            return RegimeSimilarityScenarioGenerator()

        if config.model_type == "quantile_ml_walk_forward":
            if self.features_df is None:
                raise ValueError("features_df is required for model_type='quantile_ml_walk_forward'")
            return QuantileMLWalkForwardScenarioGenerator()

        raise ValueError(f"Unknown model_type: {config.model_type}")

    def _get_input_df(self, config: ScenarioConfig) -> pd.DataFrame:
        if config.model_type == "monte_carlo":
            return self.price_df  # type: ignore
        if config.model_type in ("regime_similarity", "quantile_ml_walk_forward"):
            return self.features_df  # type: ignore
        raise ValueError(f"Unknown model_type: {config.model_type}")

    def run(self, config: ScenarioConfig) -> Dict[str, Any]:
        gen = self._select_generator(config)
        inp = self._get_input_df(config)

        kwargs: Dict[str, Any] = {}

        if config.model_type == "regime_similarity" and config.regime_cfg is not None:
            kwargs["regime_cfg"] = config.regime_cfg

        if config.model_type == "quantile_ml_walk_forward" and config.ml_walk_cfg is not None:
            kwargs["ml_cfg"] = config.ml_walk_cfg

        result: ScenarioResult = gen.generate(
            inp,
            horizon_days=int(config.horizon_days),
            n_scenarios=int(config.n_scenarios),
            seed=int(config.seed),
            **kwargs,
        )

        paths = result.scenarios
        terminal = paths[:, -1]

        summary = {
            "start_price": float(paths[0, 0]),
            "horizon_days": int(config.horizon_days),
            "n_scenarios": int(config.n_scenarios),
            "terminal_mean": float(np.mean(terminal)),
            "terminal_median": float(np.median(terminal)),
            "terminal_p05": float(np.percentile(terminal, 5)),
            "terminal_p50": float(np.percentile(terminal, 50)),
            "terminal_p95": float(np.percentile(terminal, 95)),
        }

        dist = result.metadata.get("distribution", {"dist": result.metadata.get("generator", "unknown")})

        # NEW: compute risk/return metrics from scenarios
        metrics = compute_scenario_metrics(paths)

        return {
            "asset": config.asset,
            "distribution": dist,
            "summary": summary,
            "paths": paths,
            "metadata": result.metadata,
            "metrics": metrics,
        }