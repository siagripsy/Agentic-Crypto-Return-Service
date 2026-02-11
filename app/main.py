from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal, Dict, Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.models.horizon_scenarios import forecast_horizon


app = FastAPI(
    title="Agentic Probabilistic Crypto Return Service",
    version="0.1.0",
    description=(
        "Prototype API that loads a probabilistic quantile model from disk "
        "and returns horizon risk/gain forecasts (VaR/CVaR + percentiles)."
    ),
)

# Where we load artifacts/data from (relative to repo root)
MODELS_DIR = Path("artifacts/models")
FEATURES_DIR = Path("data/processed/features")


def log_to_simple(x: float) -> float:
    """Convert log-return to simple return (e.g., 0.05 -> about 5.1%)."""
    return float(np.exp(x) - 1.0)


class HorizonRequest(BaseModel):
    symbol: str = Field(..., description="Asset symbol, e.g. BTC or ETH")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")

    # Provide exactly one:
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    horizon_days: Optional[int] = Field(None, description="Trading days to simulate (e.g., 10, 21, 252)")

    n_scenarios: int = Field(5000, ge=100, le=50000, description="Number of Monte Carlo scenarios")
    alpha: float = Field(0.05, gt=0.0, lt=0.5, description="Tail probability for VaR/CVaR")
    seed: int = Field(42, description="Random seed for reproducibility")

    return_format: Literal["log", "simple", "both"] = Field(
        "both",
        description="Return format for metrics: log returns, simple returns, or both",
    )


class HorizonResponse(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    horizon_days: int
    n_scenarios: int
    alpha: float
    assumptions: Dict[str, Any]
    summary: Dict[str, float]


def load_bundle(symbol: str):
    path = MODELS_DIR / f"{symbol.upper()}_quantile_bundle.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Model bundle not found: {path}")
    return joblib.load(path)


def load_features_df(symbol: str) -> pd.DataFrame:
    path = FEATURES_DIR / f"{symbol.upper()}_features.csv"
    if not path.exists():
        raise FileNotFoundError(f"Features CSV not found: {path}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def format_summary(summary_log: Dict[str, float], return_format: str) -> Dict[str, float]:
    """Convert summary values from log-return space to requested format."""
    if return_format == "log":
        return {k: float(v) for k, v in summary_log.items()}

    summary_simple = {k: log_to_simple(float(v)) for k, v in summary_log.items()}

    if return_format == "simple":
        return summary_simple

    # both
    out: Dict[str, float] = {}
    for k, v in summary_log.items():
        out[f"{k}_log"] = float(v)
        out[f"{k}_simple"] = summary_simple[k]
    return out


@app.get("/health")
def health():
    """Simple endpoint to confirm the API is running."""
    return {"status": "ok"}


@app.post("/forecast/horizon", response_model=HorizonResponse)
def forecast_horizon_endpoint(req: HorizonRequest):
    """
    Horizon forecast endpoint.

    Loads:
    - pre-trained quantile bundle from disk (joblib)
    - features CSV for the requested symbol

    Then returns:
    - horizon risk/gain summary (median/p05/p95/VaR/CVaR)

    Assumption (prototype):
    - regime-fixed: features are held constant across the horizon.
    """
    if (req.end_date is None) == (req.horizon_days is None):
        raise HTTPException(status_code=400, detail="Provide exactly one of end_date or horizon_days.")

    try:
        bundle = load_bundle(req.symbol)
        features_df = load_features_df(req.symbol)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    out = forecast_horizon(
        bundle=bundle,
        features_df=features_df,
        start_date=req.start_date,
        end_date=req.end_date,
        horizon_days=req.horizon_days,
        n_scenarios=req.n_scenarios,
        alpha=req.alpha,
        seed=req.seed,
    )

    summary = format_summary(out.summary, req.return_format)

    return HorizonResponse(
        symbol=req.symbol.upper(),
        start_date=str(out.start_date.date()),
        end_date=str(out.end_date.date()),
        horizon_days=out.horizon_days,
        n_scenarios=out.n_scenarios,
        alpha=out.alpha,
        assumptions={
            "regime_fixed": True,
            "features_constant_over_horizon": True,
            "notes": "Prototype: samples daily returns from the start_date conditional distribution.",
        },
        summary=summary,
    )
