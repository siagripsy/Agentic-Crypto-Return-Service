from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd

from core.models.scenario_generator_base import BaseScenarioGenerator, ScenarioResult


@dataclass
class RegimeSimilarityConfig:
    k_similar: int = 50
    min_history: int = 250
    feature_cols: Tuple[str, ...] = (
        "log_ret_5d",
        "log_ret_10d",
        "vol_7d",
        "vol_30d",
        "risk_adj_ret_1d",
        "vol_ratio_7d_30d",
        "drawdown_30d",
    )
    ret_col: str = "log_ret_1d"


class RegimeSimilarityScenarioGenerator(BaseScenarioGenerator):
    """
    Regime similarity + conditional scenario generation using precomputed features_df.

    Input expectation: features_df has at least:
    - date (string or datetime)
    - close
    - log_ret_1d
    - feature columns listed in cfg.feature_cols

    Scenario generation:
    - Find K most similar historical dates to the latest date using standardized feature distance.
    - For each scenario: choose one similar day i and take future returns:
        log_ret_1d[i+1 : i+1+horizon_days]
      Then convert to price path.
    """

    def _prep_features(self, features_df: pd.DataFrame, cfg: RegimeSimilarityConfig) -> pd.DataFrame:
        df = features_df.copy()
        df.columns = [c.lower() for c in df.columns]

        need = {"date", "close", cfg.ret_col.lower()} | {c.lower() for c in cfg.feature_cols}
        missing = need - set(df.columns)
        if missing:
            raise ValueError(f"features_df missing required columns: {sorted(missing)}")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

        # ensure numeric
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df[cfg.ret_col.lower()] = pd.to_numeric(df[cfg.ret_col.lower()], errors="coerce")
        for c in cfg.feature_cols:
            df[c.lower()] = pd.to_numeric(df[c.lower()], errors="coerce")

        # drop NaNs in features/returns
        cols = [cfg.ret_col.lower(), "close"] + [c.lower() for c in cfg.feature_cols]
        df = df.dropna(subset=cols).reset_index(drop=True)

        if len(df) < cfg.min_history:
            raise ValueError(f"Need at least {cfg.min_history} rows, got {len(df)}")

        return df

    def _standardize(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        mu = X.mean(axis=0)
        sd = X.std(axis=0, ddof=0)
        sd = np.where(sd == 0, 1.0, sd)
        Z = (X - mu) / sd
        return Z, mu, sd

    def _find_similar(self, df: pd.DataFrame, cfg: RegimeSimilarityConfig) -> Tuple[np.ndarray, np.ndarray]:
        feats = [c.lower() for c in cfg.feature_cols]
        X = df[feats].values.astype(float)

        Z, _, _ = self._standardize(X)
        z_t = Z[-1]
        Z_hist = Z[:-1]

        d = np.sqrt(((Z_hist - z_t) ** 2).sum(axis=1))

        k = int(cfg.k_similar)
        k = max(10, min(k, len(d)))

        idx = np.argsort(d)[:k]
        return idx, d[idx]

    def _sample_future_returns(
        self,
        df: pd.DataFrame,
        cfg: RegimeSimilarityConfig,
        similar_idx: np.ndarray,
        horizon_days: int,
        n_scenarios: int,
        rng: np.random.Generator,
    ) -> Tuple[np.ndarray, List[pd.Timestamp]]:
        # ensure we can read i+1 .. i+horizon
        max_i = len(df) - horizon_days - 1
        valid = similar_idx[similar_idx <= max_i]

        if len(valid) < 10:
            raise ValueError(
                "Not enough similar days with future horizon available. "
                "Reduce horizon_days or k_similar, or provide more history."
            )

        chosen = rng.choice(valid, size=n_scenarios, replace=True)

        ret_col = cfg.ret_col.lower()
        blocks = np.zeros((n_scenarios, horizon_days), dtype=float)
        chosen_dates: List[pd.Timestamp] = []

        for s, i in enumerate(chosen):
            blocks[s, :] = df[ret_col].iloc[i + 1 : i + 1 + horizon_days].values
            chosen_dates.append(pd.to_datetime(df["date"].iloc[i]))

        return blocks, chosen_dates

    def _returns_to_paths(self, start_price: float, ret_blocks: np.ndarray) -> np.ndarray:
        cum = np.cumsum(ret_blocks, axis=1)
        prices = start_price * np.exp(cum)
        start_col = np.full((ret_blocks.shape[0], 1), start_price, dtype=float)
        return np.concatenate([start_col, prices], axis=1)

    def generate(
        self,
        features_df: pd.DataFrame,
        *,
        horizon_days: int,
        n_scenarios: int,
        seed: int = 42,
        **kwargs,
    ) -> ScenarioResult:
        cfg: RegimeSimilarityConfig = kwargs.get("regime_cfg", RegimeSimilarityConfig())

        df = self._prep_features(features_df, cfg)

        start_price = float(df["close"].iloc[-1])

        similar_idx, similar_dist = self._find_similar(df, cfg)

        rng = np.random.default_rng(seed)
        ret_blocks, chosen_dates = self._sample_future_returns(
            df=df,
            cfg=cfg,
            similar_idx=similar_idx,
            horizon_days=int(horizon_days),
            n_scenarios=int(n_scenarios),
            rng=rng,
        )

        paths = self._returns_to_paths(start_price=start_price, ret_blocks=ret_blocks)

        metadata: Dict[str, Any] = {
            "generator": "regime_similarity_features",
            "seed": int(seed),
            "horizon_days": int(horizon_days),
            "n_scenarios": int(n_scenarios),
            "start_price": start_price,
            "k_similar": int(cfg.k_similar),
            "feature_cols": list(cfg.feature_cols),
            "ret_col": cfg.ret_col,
            "similar_dates_sample": [str(d) for d in chosen_dates[:10]],
            "similar_distances_sample": [float(x) for x in similar_dist[:10]],
            "latest_date": str(df["date"].iloc[-1]),
        }

        return ScenarioResult(scenarios=paths, metadata=metadata)