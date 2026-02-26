# core/models/horizon_scenarios.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from typing import Literal
import numpy as np
import pandas as pd

from core.models.probabilistic_quantile import (
    QuantileModelBundle,
    predict_quantiles,
    sample_from_quantiles,
    var_cvar,
)


@dataclass(frozen=True)
class HorizonForecast:
    """
    Output container for a horizon forecast.
    All returns are cumulative *log returns* over the horizon.
    """
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    horizon_days: int
    n_scenarios: int
    alpha: float
    summary: Dict[str, float]
    samples: np.ndarray  # cumulative log-return samples


def _ensure_datetime(x) -> pd.Timestamp:
    return pd.to_datetime(x)


def trading_days_between(start_date, end_date) -> int:
    """
    Convert an explicit (start_date, end_date) into an approximate trading-day horizon.
    Uses business days as a simple proxy (no exchange calendar yet).

    Returns horizon_days >= 1.
    """
    start = _ensure_datetime(start_date)
    end = _ensure_datetime(end_date)
    if end <= start:
        raise ValueError("end_date must be after start_date")
    # business days inclusive; horizon is number of steps forward
    bdays = pd.bdate_range(start=start, end=end)
    return max(int(len(bdays) - 1), 1)


def pick_feature_row(features_df: pd.DataFrame, start_date) -> pd.DataFrame:
    """
    Pick the feature row for a requested start_date.
    If exact date not present, pick the most recent date BEFORE start_date.
    (This avoids 'future' leakage.)
    """
    if "date" not in features_df.columns:
        raise ValueError("features_df must contain a 'date' column")

    df = features_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    start = _ensure_datetime(start_date)

    # exact match first
    exact = df[df["date"] == start]
    if len(exact) >= 1:
        return exact.iloc[[0]]

    # otherwise choose last date before start_date
    prior = df[df["date"] < start]
    if len(prior) == 0:
        raise ValueError("No feature rows exist before the requested start_date.")
    return prior.iloc[[-1]]


def simulate_horizon_log_returns(
    bundle: QuantileModelBundle,
    start_row: pd.DataFrame,
    horizon_days: int,
    n_scenarios: int = 5000,
    seed: int = 42,
) -> np.ndarray:
    """
    Simulate cumulative log-returns over horizon_days using regime-fixed sampling.

    Regime-fixed assumption:
    - Predict quantiles once using start_row (today's regime).
    - Each simulated day draws a return from that same conditional distribution.
    - Sum daily log returns to get horizon cumulative log return.

    Output:
    - array shape (n_scenarios,)
    """
    if len(start_row) != 1:
        raise ValueError("start_row must be a single-row DataFrame")
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")

    # Predict distribution ONCE (regime fixed)
    qpred = predict_quantiles(bundle, start_row)

    # Stable RNG across numpy versions
    rng = np.random.Generator(np.random.PCG64(seed))

    # Pull quantiles + predicted values for this single row
    qs = np.array(sorted(bundle.quantiles), dtype=float)
    vals = np.array([qpred.iloc[0][f"q_{q:.2f}"] for q in qs], dtype=float)

    cum = np.zeros(n_scenarios, dtype=float)

    for _ in range(horizon_days):
        # Draw U~Uniform(0,1) and map through inverse CDF (linear interp)
        u = rng.uniform(0.0, 1.0, size=n_scenarios)

        # Clamp to avoid extrapolation beyond our quantile grid
        u = np.clip(u, qs.min(), qs.max())

        daily = np.interp(u, qs, vals)  # inverse-CDF sampling approximation
        cum += daily

    return cum


def forecast_horizon(
    bundle: QuantileModelBundle,
    features_df: pd.DataFrame,
    start_date,
    *,
    end_date: Optional[str] = None,
    horizon_days: Optional[int] = None,
    n_scenarios: int = 5000,
    alpha: float = 0.05,
    seed: int = 42
) -> HorizonForecast:
    """
    General horizon forecast API.

    You provide:
    - start_date
    AND either:
      - end_date (explicit date range), OR
      - horizon_days (number of trading days to simulate)

    Returns:
    - HorizonForecast with cumulative log-return samples and summary metrics.
    """
    if (end_date is None) == (horizon_days is None):
        raise ValueError("Provide exactly one of end_date or horizon_days.")

    start_dt = _ensure_datetime(start_date)

    if end_date is not None:
        end_dt = _ensure_datetime(end_date)
        h = trading_days_between(start_dt, end_dt)
    else:
        h = int(horizon_days)
        if h < 1:
            raise ValueError("horizon_days must be >= 1")
        # approximate end date using business days
        end_dt = (pd.bdate_range(start=start_dt, periods=h + 1)[-1]).to_pydatetime()

    # select the row that represents the regime at start_date
    start_row = pick_feature_row(features_df, start_dt)

    samples = simulate_horizon_log_returns(
        bundle=bundle,
        start_row=start_row,
        horizon_days=h,
        n_scenarios=n_scenarios,
        seed=seed,
        
    )

    VaR, CVaR = var_cvar(samples, alpha=alpha)

    summary = {
        "median": float(np.median(samples)),
        "mean": float(np.mean(samples)),
        "p05": float(np.percentile(samples, 5)),
        "p95": float(np.percentile(samples, 95)),
        f"VaR_{int(alpha*100)}": float(VaR),
        f"CVaR_{int(alpha*100)}": float(CVaR),
    }

    return HorizonForecast(
        start_date=pd.to_datetime(start_row["date"].iloc[0]),
        end_date=pd.to_datetime(end_dt),
        horizon_days=int(h),
        n_scenarios=int(n_scenarios),
        alpha=float(alpha),
        summary=summary,
        samples=samples,
    )
