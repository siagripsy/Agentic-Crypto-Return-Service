from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple

import os
import joblib
import numpy as np
import pandas as pd

from core.models.scenario_generator_base import BaseScenarioGenerator, ScenarioResult
from core.models.probabilistic_quantile import predict_quantiles, sample_from_quantiles


@dataclass
class WalkForwardMLConfig:
    models_root: str = "artifacts/models"
    warmup_rows: int = 80  # seed rolling features from recent real rows

    # sampling strategy for scenario population
    sampling_strategy: str = "stratified"  # "random" or "stratified"

    # stratified bins on u-space (CDF space): (low, high, fraction)
    # default: 10% left tail, 80% centre, 10% right tail
    stratified_bins: Tuple[Tuple[float, float, float], ...] = (
        (0.00, 0.10, 0.10),
        (0.10, 0.90, 0.80),
        (0.90, 1.00, 0.10),
    )

    seed: int = 42


class QuantileMLWalkForwardScenarioGenerator(BaseScenarioGenerator):
    """
    Walk-forward scenario generator using trained quantile ML models.

    Per day:
      1) recompute features from simulated history
      2) predict quantiles via ML model
      3) sample one log return (random or stratified across scenario population)
      4) update price and history
    """

    def _infer_ticker(self, df: pd.DataFrame, fallback: str = "BTC-USD") -> str:
        if "ticker" in df.columns:
            s = df["ticker"].dropna()
            if len(s) > 0:
                return str(s.iloc[-1])
        return fallback

    def _load_bundle(self, models_root: str, ticker: str) -> Dict[str, Any]:
        path = os.path.join(models_root, ticker, "quantile_model_bundle.joblib")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model bundle not found: {path}")
        return joblib.load(path)

    def _prep_features_df(self, features_df: pd.DataFrame) -> pd.DataFrame:
        df = features_df.copy()
        df.columns = [c.lower() for c in df.columns]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        return df


    # Given a history dataframe hist (real + simulated rows), it computes the features for the most recent day (the last row) 
    # that are needed for the ML model to predict quantiles for the next return. It returns a dictionary of feature values.
    # So each day’s “regime features” are consistent with your original feature engineering logic, but computed on-the-fly from the evolving path.
    def _compute_one_row_features(self, hist: pd.DataFrame) -> Dict[str, float]:
        close = hist["close"]
        r1 = hist["log_ret_1d"]

        def safe_log_ret_n(n: int) -> float:
            if len(close) <= n:
                return np.nan
            return float(np.log(close.iloc[-1] / close.iloc[-1 - n]))

        log_ret_5d = safe_log_ret_n(5)
        log_ret_10d = safe_log_ret_n(10)

        vol_7d = float(r1.iloc[-7:].std(ddof=1)) if len(r1) >= 7 else np.nan
        vol_30d = float(r1.iloc[-30:].std(ddof=1)) if len(r1) >= 30 else np.nan

        risk_adj = float(r1.iloc[-1] / vol_30d) if vol_30d and not np.isnan(vol_30d) else np.nan
        vol_ratio = (
            float(vol_7d / vol_30d)
            if vol_7d and vol_30d and not np.isnan(vol_7d) and not np.isnan(vol_30d)
            else np.nan
        )

        if len(close) >= 30:
            roll_max = float(close.iloc[-30:].max())
            drawdown = float((close.iloc[-1] / roll_max) - 1.0) if roll_max > 0 else np.nan
        else:
            drawdown = np.nan

        return {
            "log_ret_1d": float(r1.iloc[-1]),
            "log_ret_5d": log_ret_5d,
            "log_ret_10d": log_ret_10d,
            "vol_7d": vol_7d,
            "vol_30d": vol_30d,
            "risk_adj_ret_1d": risk_adj,
            "vol_ratio_7d_30d": vol_ratio,
            "drawdown_30d": drawdown,
        }

    def _build_u_vector_stratified(
        self,
        n: int,
        rng: np.random.Generator,
        bins: Tuple[Tuple[float, float, float], ...],
    ) -> np.ndarray:
        """
        Build stratified u values in [0,1] according to bins.
        bins: (low, high, fraction). Fractions should sum ~1.
        """
        if n <= 0:
            return np.array([], dtype=float)

        # initial allocation by rounding
        counts = [int(round(n * frac)) for _, _, frac in bins]

        # fix rounding to match exactly n
        diff = n - sum(counts)
        i = 0
        while diff != 0:
            j = i % len(counts)
            if diff > 0:
                counts[j] += 1
                diff -= 1
            else:
                if counts[j] > 0:
                    counts[j] -= 1
                    diff += 1
            i += 1

        u_parts = []
        for (low, high, _), c in zip(bins, counts):
            if c <= 0:
                continue
            # sample uniformly inside each bin
            u_parts.append(rng.uniform(low, high, size=c))

        u = np.concatenate(u_parts) if u_parts else rng.uniform(0.0, 1.0, size=n)
        rng.shuffle(u)
        return u

    def generate(
        self,
        features_df: pd.DataFrame,
        *,
        horizon_days: int,
        n_scenarios: int,
        seed: int = 42,
        **kwargs,
    ) -> ScenarioResult:
        cfg: WalkForwardMLConfig = kwargs.get("ml_cfg", WalkForwardMLConfig(seed=seed))

        df = self._prep_features_df(features_df)
        ticker = self._infer_ticker(features_df)

        bundle_obj = self._load_bundle(cfg.models_root, ticker)
        bundle = bundle_obj["bundle"]
        feature_cols = [c.lower() for c in bundle.feature_cols]

        if len(df) < cfg.warmup_rows:   # Takes the last warmup_rows real observations as base history
            raise ValueError(f"Not enough rows for warmup. Need {cfg.warmup_rows}, got {len(df)}")

        rng = np.random.default_rng(seed)

        paths = np.zeros((int(n_scenarios), int(horizon_days) + 1), dtype=float)
        start_price = float(df["close"].iloc[-1])
        paths[:, 0] = start_price

        base_hist = df.tail(cfg.warmup_rows).copy().reset_index(drop=True)
        if "log_ret_1d" not in base_hist.columns:        # Ensures log_ret_1d exists in history; if not, creates it from close.
            base_hist["log_ret_1d"] = np.log(base_hist["close"] / base_hist["close"].shift(1))

        # Pre-build u vectors per day (shared across scenarios) for stratified sampling
        u_by_day: List[np.ndarray] = []
        if cfg.sampling_strategy == "stratified":
            for _ in range(int(horizon_days)):
                u_by_day.append(self._build_u_vector_stratified(int(n_scenarios), rng, cfg.stratified_bins))

        for s in range(int(n_scenarios)):
            hist = base_hist.copy()
            current_price = float(hist["close"].iloc[-1])

            for t in range(1, int(horizon_days) + 1):
                feats = self._compute_one_row_features(hist)
                row = pd.DataFrame([{k: feats.get(k, np.nan) for k in feature_cols}])

                qpred = predict_quantiles(bundle, row)

                if cfg.sampling_strategy == "random":
                    r_next = float(
                        sample_from_quantiles(
                            qpred,
                            quantiles=bundle.quantiles,
                            n_samples=1,
                            seed=int(rng.integers(0, 1_000_000_000)),
                        )[0]
                    )
                else:
                    # stratified: pick u assigned to this scenario for this day
                    u = float(u_by_day[t - 1][s])

                    # we replicate sample_from_quantiles logic but with fixed u (inverse-CDF)
                    qs = np.array(sorted([float(q) for q in bundle.quantiles]), dtype=float)
                    vals = np.array([qpred.iloc[0][f"q_{q:.2f}"] for q in qs], dtype=float)

                    u_clamped = float(np.clip(u, qs.min(), qs.max()))
                    r_next = float(np.interp(u_clamped, qs, vals))

                current_price = current_price * float(np.exp(r_next))
                paths[s, t] = current_price

                hist = pd.concat(
                    [
                        hist,
                        pd.DataFrame(
                            {
                                "date": [hist["date"].iloc[-1] + pd.Timedelta(days=1)],
                                "close": [current_price],
                                "log_ret_1d": [r_next],
                            }
                        ),
                    ],
                    ignore_index=True,
                )

        metadata: Dict[str, Any] = {
            "generator": "quantile_ml_walk_forward",
            "ticker": ticker,
            "models_root": cfg.models_root,
            "seed": int(seed),
            "horizon_days": int(horizon_days),
            "n_scenarios": int(n_scenarios),
            "start_price": start_price,
            "warmup_rows": int(cfg.warmup_rows),
            "sampling_strategy": cfg.sampling_strategy,
            "stratified_bins": [list(b) for b in cfg.stratified_bins],
        }

        return ScenarioResult(scenarios=paths, metadata=metadata)