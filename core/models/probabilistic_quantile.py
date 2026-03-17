from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor


@dataclass
class QuantileModelBundle:
    """
    Holds a set of quantile regressors trained for different quantiles.

    Example:
        quantiles = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
        models[q] predicts the q-quantile of next-day returns
    """
    quantiles: List[float]
    models: Dict[float, GradientBoostingRegressor]
    feature_cols: List[str]


# Default ML feature set (excludes market_cap on purpose: it has many NaNs historically)
DEFAULT_FEATURES: List[str] = [
    "log_ret_1d",
    "log_ret_5d",
    "log_ret_10d",
    "vol_7d",
    "vol_30d",
    "risk_adj_ret_1d",
    "vol_ratio_7d_30d",
    "drawdown_30d",
]


def load_features_csv(path: str | pd.DataFrame) -> pd.DataFrame:
    """
    Loads feature data and returns it sorted by date.
    """
    if isinstance(path, pd.DataFrame):
        df = path.copy()
    else:
        df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def add_next_day_target(df: pd.DataFrame, ret_col: str = "log_ret_1d") -> pd.DataFrame:
    """
    Defines the supervised learning target as next-day log return:
        y_t = log_ret_1d[t+1]

    Implemented using shift(-1):
        target[t] = ret[t+1]

    This prevents leakage: features at time t predict outcomes at t+1.
    """
    out = df.copy()
    out["target_log_ret_1d"] = out[ret_col].shift(-1)
    out = out.dropna(subset=["target_log_ret_1d"]).reset_index(drop=True)
    return out


def prepare_model_frame(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    target_col: str = "target_log_ret_1d",
) -> Tuple[pd.DataFrame, List[str], str]:
    """
    Ensures:
    - required feature columns exist
    - no NaNs in selected features/target (GBR cannot handle NaNs)
    - returns a clean modeling frame

    Note: market_cap may still exist in df, but we do not use it as a feature by default.
    """
    feats = feature_cols or DEFAULT_FEATURES

    missing = [c for c in feats + [target_col] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    model_df = df.dropna(subset=feats + [target_col]).reset_index(drop=True)
    return model_df, feats, target_col


def time_split(df: pd.DataFrame, train_frac: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Chronological split. No shuffle.
    """
    split = int(len(df) * train_frac)
    train = df.iloc[:split].copy()
    test = df.iloc[split:].copy()
    return train, test


def fit_quantile_models(
    train_df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = "target_log_ret_1d",
    quantiles: List[float] = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99],
    random_state: int = 42,
    n_estimators: int = 200,
    learning_rate: float = 0.05,
    max_depth: int = 3,
) -> QuantileModelBundle:
    """
    Trains one GradientBoostingRegressor per quantile (loss='quantile').

    This yields an approximate conditional return distribution via multiple quantiles.
    """
    X = train_df[feature_cols].values
    y = train_df[target_col].values

    models: Dict[float, GradientBoostingRegressor] = {}
    for q in quantiles:
        m = GradientBoostingRegressor(
            loss="quantile",
            alpha=float(q),
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            random_state=random_state,
        )
        m.fit(X, y)
        models[float(q)] = m

    return QuantileModelBundle(quantiles=[float(q) for q in quantiles], models=models, feature_cols=feature_cols)


def predict_quantiles(bundle: QuantileModelBundle, df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns predicted quantiles for each row:
        columns: q_0.05, q_0.50, ...
    """
    X = df[bundle.feature_cols].values
    out = pd.DataFrame(index=df.index)
    for q in sorted(bundle.quantiles):
        out[f"q_{q:.2f}"] = bundle.models[q].predict(X)
    return out


def sample_from_quantiles(
    quantile_preds: pd.DataFrame,
    quantiles: List[float],
    n_samples: int = 5000,
    seed: int = 0,
) -> np.ndarray:
    """
    this function reconstructs a full distribution from quantiles and generates samples from it.
    Generates samples from a predicted distribution using inverse-CDF sampling.

    Input:
    - quantile_preds: a SINGLE-row DataFrame with columns q_0.05, q_0.50, ...
    - quantiles: list of quantile levels corresponding to those columns

    Method:
    - Approximate the CDF by linear interpolation between predicted quantile points.
    - Sample u ~ Uniform(0,1), map through inverse CDF     .
    - CDF (Cumulative Distribution Function): What is the probability the outcome is less than or equal to x?

    Note:
    - With only [0.05, 0.50, 0.95], tails are coarse.
    - More quantiles yield smoother distributions.
    """
    rng = np.random.default_rng(seed)

    if len(quantile_preds) != 1:
        raise ValueError("sample_from_quantiles expects predictions for exactly one row.")

    qs = np.array(sorted([float(q) for q in quantiles]), dtype=float)
    vals = np.array([quantile_preds.iloc[0][f"q_{q:.2f}"] for q in qs], dtype=float)

    u = rng.uniform(0, 1, size=n_samples)

    # Avoid extrapolating beyond our lowest/highest predicted quantiles
    u_clamped = np.clip(u, qs.min(), qs.max())

    return np.interp(u_clamped, qs, vals)


def var_cvar(samples: np.ndarray, alpha: float = 0.05) -> Tuple[float, float]:
    """
    Computes VaR and CVaR from return samples.

    - VaR(alpha): alpha-quantile of returns (e.g., 5% worst threshold)
    - CVaR(alpha): mean return within the worst alpha tail (returns <= VaR)

    Returns are in log-return units. Negative implies loss.
    """
    var = float(np.quantile(samples, alpha))
    tail = samples[samples <= var]
    cvar = float(tail.mean()) if len(tail) > 0 else var
    return var, cvar


def compute_var_cvar_timeseries(
    bundle: QuantileModelBundle,
    df_rows: pd.DataFrame,
    alpha: float = 0.05,
    n_samples: int = 3000,
    seed: int = 123,
    include_quantiles: bool = True,
) -> pd.DataFrame:
    """
    Compute per-row VaR/CVaR using the model's conditional quantile predictions.

    Parameters
    ----------
    bundle : QuantileModelBundle
        Trained quantile models.
    df_rows : pd.DataFrame
        Rows for which to compute VaR/CVaR (must contain bundle.feature_cols and date).
    alpha : float
        Tail probability for VaR/CVaR (e.g., 0.05).
    n_samples : int
        Number of samples per row for scenario sampling.
    seed : int
        Base seed for reproducible results.
    include_quantiles : bool
        If True, include q_0.50 and the key quantile columns in output when available.

    Returns
    -------
    pd.DataFrame
        Columns: date, VaR_alpha, CVaR_alpha, (optional) q_0.50, and any predicted quantiles.
    """
    rows = []
    df_rows = df_rows.copy().reset_index(drop=True)

    for i in range(len(df_rows)):
        one = df_rows.iloc[[i]]
        qpred = predict_quantiles(bundle, one)

        # vary seed per row to avoid identical sampling patterns
        samples = sample_from_quantiles(
            qpred,
            quantiles=bundle.quantiles,
            n_samples=n_samples,
            seed=seed + i,
        )
        var_a, cvar_a = var_cvar(samples, alpha=alpha)

        rec = {
            "date": one["date"].iloc[0] if "date" in one.columns else i,
            f"VaR_{int(alpha*100)}": var_a,
            f"CVaR_{int(alpha*100)}": cvar_a,
        }

        if include_quantiles:
            # include median if present
            if "q_0.50" in qpred.columns:
                rec["q_0.50"] = float(qpred["q_0.50"].iloc[0])
            # include all quantiles (useful for debugging/plots)
            for c in qpred.columns:
                rec[c] = float(qpred[c].iloc[0])

        rows.append(rec)

    out = pd.DataFrame(rows)
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.sort_values("date").reset_index(drop=True)
    return out
