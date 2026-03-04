# app/main.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal, Dict, Any, List, Deque
import json
import time
from collections import deque
from dataclasses import asdict, is_dataclass

import joblib
import numpy as np
import pandas as pd
import anyio
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Fast (regime-fixed) horizon sampling
from core.models.horizon_scenarios import forecast_horizon

# VaR/CVaR helper for regime-fixed risk curve (on samples)
from core.models.probabilistic_quantile import var_cvar

# Path engines + metrics
from core.pipelines.scenario_engine import ScenarioEngine, ScenarioConfig
from core.models.scenario_metrics import compute_scenario_metrics, MetricsConfig

# Portfolio stack (teammate changes)
from core.pipelines.portfolio_pipeline import run_portfolio_pipeline, PortfolioPipelineConfig
from core.risk.schemas import RiskReport

# Needed to rebuild portfolio after conservative risk merge (ensemble)
from core.portfolio.portfolio import build_portfolio
from core.portfolio.schemas import PortfolioConstraints


app = FastAPI(
    title="Agentic Probabilistic Crypto Return Service",
    version="0.1.0",
    description="API for probabilistic crypto risk forecasting using multiple scenario engines + portfolio layer.",
)


# -----------------------------
# Error handling
# -----------------------------
@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    # Converts missing artifact/CSV crashes into clean 404s
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# -----------------------------
# Paths (relative to repo root)
# -----------------------------
MODELS_DIR = Path("artifacts/models")
FEATURES_DIR = Path("data/processed/features")
COINS_PATH = Path("data/raw/metadata/coins.json")
OHLCV_DIR = Path("data/raw/ohlcv")


# -----------------------------
# Guardrails (safe defaults)
# -----------------------------
MAX_SYMBOLS = 20
MAX_HORIZON_DAYS = 252
MAX_SCENARIOS_REGIME_FIXED = 20000
MAX_SCENARIOS_REGIME_SIMILARITY = 10000
MAX_SCENARIOS_WALKFORWARD = 5000
MAX_SCENARIOS_ENSEMBLE = 5000

DEFAULT_TIMEOUT_SINGLE = 12  # seconds
DEFAULT_TIMEOUT_MULTI = 20   # seconds

# Rate limiting (simple in-memory per-IP)
RATE_LIMIT_PER_MINUTE = 60
_RATE_WINDOW_SECONDS = 60.0
_ip_hits: Dict[str, Deque[float]] = {}

# Lazy cache for symbol->yahoo_ticker mapping
_SYMBOL_TO_TICKER: Optional[Dict[str, str]] = None

RiskLevel = Literal["low", "medium", "high"]
EngineType = Literal["fast_regime_fixed", "walkforward_ml", "regime_similarity", "ensemble"]

RISK_LEVEL_TO_ALPHA: Dict[str, float] = {"low": 0.10, "medium": 0.05, "high": 0.01}

# Portfolio/scenario model types (used by ScenarioEngine + PortfolioPipelineConfig)
ENGINE_TO_MODEL_TYPE = {
    "walkforward_ml": "quantile_ml_walk_forward",
    "regime_similarity": "regime_similarity",
}
MODEL_TYPE_A = "quantile_ml_walk_forward"
MODEL_TYPE_B = "regime_similarity"


# -----------------------------
# Utilities
# -----------------------------
def _as_jsonable(x: Any) -> Any:
    """Convert dataclasses (and nested) to JSON-friendly dicts."""
    if is_dataclass(x):
        return asdict(x)
    if isinstance(x, dict):
        return {k: _as_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_as_jsonable(v) for v in x]
    return x


def log_to_simple(x: float) -> float:
    return float(np.exp(x) - 1.0)


def load_symbol_to_yahoo_ticker() -> Dict[str, str]:
    if not COINS_PATH.exists():
        raise FileNotFoundError(f"coins.json not found: {COINS_PATH}")
    data = json.loads(COINS_PATH.read_text(encoding="utf-8"))
    coins = data.get("coins", [])
    m: Dict[str, str] = {}
    for c in coins:
        sym = str(c.get("symbol", "")).upper().strip()
        yt = str(c.get("yahoo_ticker", "")).strip()
        if sym and yt:
            m[sym] = yt
    if not m:
        raise FileNotFoundError(f"No symbol->yahoo_ticker mappings found in {COINS_PATH}")
    return m


def _validate_horizon_args(end_date: Optional[str], horizon_days: Optional[int]) -> None:
    if (end_date is None) == (horizon_days is None):
        raise HTTPException(status_code=400, detail="Provide exactly one of end_date or horizon_days.")


def _validate_alphas(alphas: Optional[List[float]]) -> None:
    if alphas is None:
        return
    if len(alphas) == 0:
        raise HTTPException(status_code=400, detail="alphas must be a non-empty list if provided.")
    for a in alphas:
        a = float(a)
        if not (0.0 < a < 0.5):
            raise HTTPException(status_code=400, detail=f"Invalid alpha={a}. Must satisfy 0 < alpha < 0.5.")


def _resolve_primary_alpha(alpha: float, risk_level: Optional[str]) -> float:
    if risk_level is None:
        return float(alpha)
    rl = risk_level.lower().strip()
    if rl not in RISK_LEVEL_TO_ALPHA:
        raise HTTPException(status_code=400, detail=f"Invalid risk_level={risk_level}. Use low|medium|high.")
    return float(RISK_LEVEL_TO_ALPHA[rl])


def _engine_max_scenarios(engine: str) -> int:
    if engine == "fast_regime_fixed":
        return MAX_SCENARIOS_REGIME_FIXED
    if engine == "regime_similarity":
        return MAX_SCENARIOS_REGIME_SIMILARITY
    if engine == "walkforward_ml":
        return MAX_SCENARIOS_WALKFORWARD
    if engine == "ensemble":
        return MAX_SCENARIOS_ENSEMBLE
    return MAX_SCENARIOS_ENSEMBLE


def _guardrails(engine: str, n_scenarios: int, horizon_days: Optional[int], symbols_count: int = 1) -> None:
    if symbols_count > MAX_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Too many symbols. max={MAX_SYMBOLS}")

    if horizon_days is not None and horizon_days > MAX_HORIZON_DAYS:
        raise HTTPException(status_code=400, detail=f"horizon_days too large. max={MAX_HORIZON_DAYS}")

    cap = _engine_max_scenarios(engine)
    if n_scenarios > cap:
        raise HTTPException(
            status_code=400,
            detail=f"n_scenarios too large for engine='{engine}'. max={cap}",
        )


def load_bundle(symbol: str):
    global _SYMBOL_TO_TICKER
    sym = symbol.upper().strip()
    if _SYMBOL_TO_TICKER is None:
        _SYMBOL_TO_TICKER = load_symbol_to_yahoo_ticker()

    ticker = _SYMBOL_TO_TICKER.get(sym)
    if not ticker:
        raise FileNotFoundError(f"No yahoo_ticker mapping found for symbol={sym} in {COINS_PATH}")

    path = MODELS_DIR / ticker / "quantile_model_bundle.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Model bundle not found: {path}")

    obj = joblib.load(path)
    if isinstance(obj, dict) and "bundle" in obj:
        return obj["bundle"]
    return obj


def load_features_df(symbol: str) -> pd.DataFrame:
    path = FEATURES_DIR / f"{symbol.upper()}_features.csv"
    if not path.exists():
        raise FileNotFoundError(f"Features CSV not found: {path}")
    df = pd.read_csv(path)

    # If your feature CSV date is non-uniform, this warning is normal. You can specify a format later.
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


def load_price_df(symbol: str) -> pd.DataFrame:
    """
    Portfolio pipeline expects a 'price_df' per asset.
    Load from data/raw/ohlcv/<YAHOO_TICKER>_daily.csv (ex: BTC-USD_daily.csv).
    """
    global _SYMBOL_TO_TICKER
    sym = symbol.upper().strip()
    if _SYMBOL_TO_TICKER is None:
        _SYMBOL_TO_TICKER = load_symbol_to_yahoo_ticker()

    ticker = _SYMBOL_TO_TICKER.get(sym)
    if not ticker:
        raise FileNotFoundError(f"No yahoo_ticker mapping found for symbol={sym} in {COINS_PATH}")

    path = OHLCV_DIR / f"{ticker}_daily.csv"
    if not path.exists():
        raise FileNotFoundError(f"OHLCV CSV not found: {path}")

    df = pd.read_csv(path)
    if "date" not in df.columns:
        raise HTTPException(status_code=500, detail=f"OHLCV CSV missing 'date' column: {path}")
    if "close" not in df.columns:
        if "Close" in df.columns:
            df = df.rename(columns={"Close": "close"})
        else:
            raise HTTPException(status_code=500, detail=f"OHLCV CSV missing 'close' column: {path}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


def format_summary(summary_log: Dict[str, float], return_format: str) -> Dict[str, float]:
    """Convert summary values from log-return space to requested format."""
    if return_format == "log":
        return {k: float(v) for k, v in summary_log.items()}

    summary_simple = {k: log_to_simple(float(v)) for k, v in summary_log.items()}

    if return_format == "simple":
        return summary_simple

    out: Dict[str, float] = {}
    for k, v in summary_log.items():
        out[f"{k}_log"] = float(v)
        out[f"{k}_simple"] = summary_simple[k]
    return out


def format_risk_curve_from_samples(samples_log: np.ndarray, alphas: List[float], return_format: str) -> Dict[str, float]:
    """Risk curve for regime-fixed engine (computed from horizon log-return samples)."""
    out: Dict[str, float] = {}
    for a in alphas:
        a = float(a)
        var_a, cvar_a = var_cvar(samples_log, alpha=a)
        pct = int(round(a * 100))

        if return_format == "log":
            out[f"VaR_{pct}"] = float(var_a)
            out[f"CVaR_{pct}"] = float(cvar_a)
        elif return_format == "simple":
            out[f"VaR_{pct}"] = log_to_simple(float(var_a))
            out[f"CVaR_{pct}"] = log_to_simple(float(cvar_a))
        else:
            out[f"VaR_{pct}_log"] = float(var_a)
            out[f"VaR_{pct}_simple"] = log_to_simple(float(var_a))
            out[f"CVaR_{pct}_log"] = float(cvar_a)
            out[f"CVaR_{pct}_simple"] = log_to_simple(float(cvar_a))
    return out


def _convert_metrics_returns_to_simple(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    compute_scenario_metrics() produces horizon returns in log space by default.
    For return_format="simple", convert return-type fields to simple returns.
    Note: drawdown is already a simple percentage drawdown (negative), so we keep it.
    """
    m = json.loads(json.dumps(metrics))  # deep-ish copy

    def conv(x):
        try:
            return log_to_simple(float(x))
        except Exception:
            return x

    if "horizon_return_summary" in m and isinstance(m["horizon_return_summary"], dict):
        for k in ["mean", "median", "p05", "p95"]:
            if k in m["horizon_return_summary"]:
                m["horizon_return_summary"][k] = conv(m["horizon_return_summary"][k])

    if "VaR_CVaR_horizon_return" in m and isinstance(m["VaR_CVaR_horizon_return"], dict):
        for k in ["VaR", "CVaR"]:
            if k in m["VaR_CVaR_horizon_return"]:
                m["VaR_CVaR_horizon_return"][k] = conv(m["VaR_CVaR_horizon_return"][k])

    if "profit_analysis" in m and isinstance(m["profit_analysis"], dict):
        for k in ["mean_profit", "max_profit", "min_profit"]:
            if k in m["profit_analysis"]:
                m["profit_analysis"][k] = conv(m["profit_analysis"][k])

    if "loss_analysis" in m and isinstance(m["loss_analysis"], dict):
        for k in ["mean_loss", "worst_loss", "smallest_loss"]:
            if k in m["loss_analysis"]:
                m["loss_analysis"][k] = conv(m["loss_analysis"][k])

    return m


def compute_metrics_and_curve(
    paths: np.ndarray,
    *,
    primary_alpha: float,
    alphas: Optional[List[float]],
    return_format: str,
) -> Dict[str, Any]:
    metrics = compute_scenario_metrics(paths, cfg=MetricsConfig(alpha=primary_alpha, use_log_returns=True))

    if return_format == "simple":
        metrics = _convert_metrics_returns_to_simple(metrics)
    elif return_format == "both":
        metrics = {"log": metrics, "simple": _convert_metrics_returns_to_simple(metrics)}

    risk_curve_metrics: Optional[Dict[str, Any]] = None
    if alphas is not None:
        curve: Dict[str, Any] = {}
        for a in alphas:
            cfg = MetricsConfig(alpha=float(a), use_log_returns=True)
            m = compute_scenario_metrics(paths, cfg=cfg)

            key = f"alpha_{float(a):.2f}"
            if return_format == "simple":
                m = _convert_metrics_returns_to_simple(m)
            elif return_format == "both":
                m = {"log": m, "simple": _convert_metrics_returns_to_simple(m)}

            def pick(src):
                if isinstance(src, dict) and "log" in src and "simple" in src:
                    return {
                        "log": {
                            "VaR_CVaR_horizon_return": src["log"]["VaR_CVaR_horizon_return"],
                            "VaR_CVaR_max_drawdown": src["log"]["VaR_CVaR_max_drawdown"],
                        },
                        "simple": {
                            "VaR_CVaR_horizon_return": src["simple"]["VaR_CVaR_horizon_return"],
                            "VaR_CVaR_max_drawdown": src["simple"]["VaR_CVaR_max_drawdown"],
                        },
                    }
                return {
                    "VaR_CVaR_horizon_return": src.get("VaR_CVaR_horizon_return"),
                    "VaR_CVaR_max_drawdown": src.get("VaR_CVaR_max_drawdown"),
                }

            curve[key] = pick(m)

        risk_curve_metrics = curve

    return {"metrics": metrics, "risk_curve_metrics": risk_curve_metrics}


def conservative_merge_metrics(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Conservative merge for FULL metrics dict."""
    out = json.loads(json.dumps(a))

    def get(d, *path, default=None):
        cur = d
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur

    def setv(d, value, *path):
        cur = d
        for p in path[:-1]:
            cur = cur.setdefault(p, {})
        cur[path[-1]] = value

    setv(out, max(float(get(a, "prob_loss", default=0.0)), float(get(b, "prob_loss", default=0.0))), "prob_loss")
    setv(out, min(float(get(a, "prob_profit", default=1.0)), float(get(b, "prob_profit", default=1.0))), "prob_profit")

    for k in ["VaR", "CVaR"]:
        va = get(a, "VaR_CVaR_horizon_return", k)
        vb = get(b, "VaR_CVaR_horizon_return", k)
        if va is not None and vb is not None:
            setv(out, min(float(va), float(vb)), "VaR_CVaR_horizon_return", k)

    for k in ["VaR", "CVaR"]:
        va = get(a, "VaR_CVaR_max_drawdown", k)
        vb = get(b, "VaR_CVaR_max_drawdown", k)
        if va is not None and vb is not None:
            setv(out, min(float(va), float(vb)), "VaR_CVaR_max_drawdown", k)

    for stat in ["mean", "median", "p05", "p95"]:
        va = get(a, "horizon_return_summary", stat)
        vb = get(b, "horizon_return_summary", stat)
        if va is not None and vb is not None:
            setv(out, min(float(va), float(vb)), "horizon_return_summary", stat)

    for stat in ["mean_profit", "max_profit", "min_profit"]:
        va = get(a, "profit_analysis", stat)
        vb = get(b, "profit_analysis", stat)
        if va is not None and vb is not None:
            setv(out, min(float(va), float(vb)), "profit_analysis", stat)

    for stat in ["mean_loss", "worst_loss", "smallest_loss"]:
        va = get(a, "loss_analysis", stat)
        vb = get(b, "loss_analysis", stat)
        if va is not None and vb is not None:
            setv(out, min(float(va), float(vb)), "loss_analysis", stat)

    return out


def conservative_merge_tail_only(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Conservative merge for tail-only dict used in risk_curve_metrics."""
    out: Dict[str, Any] = {}
    out["VaR_CVaR_horizon_return"] = {
        "VaR": min(float(a["VaR_CVaR_horizon_return"]["VaR"]), float(b["VaR_CVaR_horizon_return"]["VaR"])),
        "CVaR": min(float(a["VaR_CVaR_horizon_return"]["CVaR"]), float(b["VaR_CVaR_horizon_return"]["CVaR"])),
    }
    out["VaR_CVaR_max_drawdown"] = {
        "VaR": min(float(a["VaR_CVaR_max_drawdown"]["VaR"]), float(b["VaR_CVaR_max_drawdown"]["VaR"])),
        "CVaR": min(float(a["VaR_CVaR_max_drawdown"]["CVaR"]), float(b["VaR_CVaR_max_drawdown"]["CVaR"])),
    }
    return out


from typing import Dict, Any, List
import re

def _merge_risk_reports_conservative(a: RiskReport, b: RiskReport) -> RiskReport:
    """
    Conservative merge for RiskReport:
    - var/cvar dicts: take worse tail (more negative)
    - max_drawdown_est: worse (more negative)
    - tail_metrics:
        * prob_loss: max
        * prob_profit: min
        * summary blocks: percentile-aware merge (p05 vs p95 etc.)
    - notes: include "ensemble" marker
    """

    # --------------------
    # helpers
    # --------------------
    def _is_number(x: Any) -> bool:
        try:
            float(x)
            return True
        except Exception:
            return False

    def _merge_scalar(key: str, va: Any, vb: Any, *, block: str) -> Any:
        """
        Percentile-aware merge rule.
        - downside percentiles (p01/p05/p10): min
        - upside percentiles (p90/p95/p99): max
        - mean/median: keep A (stable)
        - otherwise: if numeric -> keep A (stable), else prefer A then B
        """
        if va is None:
            return vb
        if vb is None:
            return va

        # non-numeric => prefer A
        if not (_is_number(va) and _is_number(vb)):
            return va

        fa, fb = float(va), float(vb)

        k = str(key).lower().strip()

        # mean/median: keep A (or choose min if you want pessimistic mean)
        if k in {"mean", "median"}:
            return fa

        # detect pXX patterns
        m = re.match(r"p(\d{1,2})$", k)
        if m:
            p = int(m.group(1))
            # downside
            if p <= 10:
                return min(fa, fb)
            # upside
            if p >= 90:
                return max(fa, fb)
            # middle percentiles: keep A
            return fa

        # fallback numeric fields: keep A
        return fa

    def _merge_block(block_name: str, da: Dict[str, Any], db: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for kk in set(da.keys()) | set(db.keys()):
            out[kk] = _merge_scalar(kk, da.get(kk), db.get(kk), block=block_name)
        return out

    # --------------------
    # var/cvar (worse tail)
    # --------------------
    var: Dict[str, float] = {}
    cvar: Dict[str, float] = {}

    a_var = getattr(a, "var", {}) or {}
    b_var = getattr(b, "var", {}) or {}
    a_cvar = getattr(a, "cvar", {}) or {}
    b_cvar = getattr(b, "cvar", {}) or {}

    for k in set(a_var.keys()) | set(b_var.keys()):
        if k in a_var and k in b_var:
            var[k] = min(float(a_var[k]), float(b_var[k]))
        else:
            var[k] = float(a_var.get(k, b_var.get(k)))  # type: ignore[arg-type]

    for k in set(a_cvar.keys()) | set(b_cvar.keys()):
        if k in a_cvar and k in b_cvar:
            cvar[k] = min(float(a_cvar[k]), float(b_cvar[k]))
        else:
            cvar[k] = float(a_cvar.get(k, b_cvar.get(k)))  # type: ignore[arg-type]

    # --------------------
    # max drawdown (worse)
    # --------------------
    max_dd = min(float(getattr(a, "max_drawdown_est")), float(getattr(b, "max_drawdown_est")))

    # --------------------
    # tail metrics merge
    # --------------------
    ta = getattr(a, "tail_metrics", None) or {}
    tb = getattr(b, "tail_metrics", None) or {}
    tail: Dict[str, Any] = dict(ta)

    if "prob_loss" in ta or "prob_loss" in tb:
        tail["prob_loss"] = max(float(ta.get("prob_loss", 0.0)), float(tb.get("prob_loss", 0.0)))
    if "prob_profit" in ta or "prob_profit" in tb:
        tail["prob_profit"] = min(float(ta.get("prob_profit", 1.0)), float(tb.get("prob_profit", 1.0)))

    # Percentile-aware merge for summary blocks
    for block in ["horizon_return_summary", "terminal_price_summary", "max_drawdown_summary"]:
        if isinstance(ta.get(block), dict) and isinstance(tb.get(block), dict):
            tail[block] = _merge_block(block, ta[block], tb[block])

    # --------------------
    # identity fields + notes
    # --------------------
    sym = getattr(a, "symbol", None) or getattr(a, "asset", None)
    horizon_days = getattr(a, "horizon_days", None)
    conf_levels = getattr(a, "confidence_levels", None)

    notes_parts: List[str] = []
    if getattr(a, "notes", None):
        notes_parts.append(str(getattr(a, "notes")))
    if getattr(b, "notes", None):
        notes_parts.append(str(getattr(b, "notes")))
    notes_parts.append("Conservative merge across engines (ensemble).")
    notes = " ".join([p for p in notes_parts if p]).strip() or None

    kwargs: Dict[str, Any] = {
        "var": var,
        "cvar": cvar,
        "max_drawdown_est": max_dd,
        "tail_metrics": tail,
        "notes": notes,
    }
    if sym is not None:
        if hasattr(a, "symbol"):
            kwargs["symbol"] = sym
        elif hasattr(a, "asset"):
            kwargs["asset"] = sym
    if horizon_days is not None and hasattr(a, "horizon_days"):
        kwargs["horizon_days"] = horizon_days
    if conf_levels is not None and hasattr(a, "confidence_levels"):
        kwargs["confidence_levels"] = conf_levels

    return RiskReport(**kwargs)  # type: ignore[arg-type]


# -----------------------------
# Middleware: Rate limiting
# -----------------------------
def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limit_check(ip: str) -> Optional[int]:
    now = time.monotonic()
    dq = _ip_hits.get(ip)
    if dq is None:
        dq = deque()
        _ip_hits[ip] = dq

    while dq and (now - dq[0]) > _RATE_WINDOW_SECONDS:
        dq.popleft()

    if len(dq) >= RATE_LIMIT_PER_MINUTE:
        retry_after = int(max(1.0, _RATE_WINDOW_SECONDS - (now - dq[0])))
        return retry_after

    dq.append(now)
    return None


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = _client_ip(request)
    retry_after = _rate_limit_check(ip)
    if retry_after is not None:
        return Response(
            content=json.dumps({"detail": "Rate limit exceeded. Try again later."}),
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": str(retry_after)},
        )
    return await call_next(request)


# -----------------------------
# Schemas: Forecasting
# -----------------------------
class HorizonRequest(BaseModel):
    symbol: str = Field(..., description="Asset symbol, e.g. BTC or ETH")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = None
    horizon_days: Optional[int] = Field(None, description="Trading days to simulate (e.g., 10, 21, 252)")

    engine: EngineType = Field(
        "ensemble",
        description="Scenario engine: fast_regime_fixed | walkforward_ml | regime_similarity | ensemble",
    )

    n_scenarios: int = Field(5000, ge=100, le=50000)

    alpha: float = Field(0.05, gt=0.0, lt=0.5)
    risk_level: Optional[RiskLevel] = None
    alphas: Optional[List[float]] = None

    seed: int = 42
    return_format: Literal["log", "simple", "both"] = "both"

    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)


class HorizonResponse(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    horizon_days: int
    n_scenarios: int
    alpha: float
    engine: str
    assumptions: Dict[str, Any]

    summary: Optional[Dict[str, float]] = None
    risk: Optional[Dict[str, float]] = None
    metrics: Optional[Dict[str, Any]] = None
    risk_curve_metrics: Optional[Dict[str, Any]] = None


class MultiHorizonRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1)
    start_date: str
    end_date: Optional[str] = None
    horizon_days: Optional[int] = None

    engine: EngineType = "ensemble"

    n_scenarios: int = Field(5000, ge=100, le=50000)

    alpha: float = Field(0.05, gt=0.0, lt=0.5)
    risk_level: Optional[RiskLevel] = None
    alphas: Optional[List[float]] = None

    seed: int = 42
    return_format: Literal["log", "simple", "both"] = "both"

    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)


class MultiHorizonResponse(BaseModel):
    results: List[HorizonResponse]


# -----------------------------
# Schemas: Portfolio
# -----------------------------
PortfolioEngine = Literal["walkforward_ml", "regime_similarity", "ensemble"]


class PortfolioRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, description="Portfolio asset symbols, e.g. ['BTC','ETH']")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    horizon_days: int = Field(..., ge=1, le=252)

    engine: PortfolioEngine = Field("ensemble", description="walkforward_ml | regime_similarity | ensemble")
    n_scenarios: int = Field(3000, ge=100, le=50000)
    seed: int = 42

    confidence_levels: List[float] = Field(default_factory=lambda: [0.95], description="e.g., [0.95]")

    user_risk_tolerance: int = Field(50, ge=0, le=100, description="0=conservative, 100=aggressive")
    top_k: int = Field(5, ge=1, le=20)
    max_weight: float = Field(0.50, gt=0.0, le=1.0)
    min_weight: float = Field(0.00, ge=0.0, le=1.0)
    allow_cash: bool = True

    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)


class PortfolioResponse(BaseModel):
    assumptions: Dict[str, Any]
    risks: Dict[str, Any]
    portfolio: Dict[str, Any]


# -----------------------------
# Timeout helper
# -----------------------------
async def _run_with_timeout(timeout_s: int, fn, *args, **kwargs):
    try:
        with anyio.fail_after(timeout_s):
            return await anyio.to_thread.run_sync(fn, *args, **kwargs)
    except TimeoutError:
        raise HTTPException(status_code=504, detail=f"Request timed out after {timeout_s} seconds.")


# -----------------------------
# Engine runners (forecast endpoints)
# -----------------------------
def _run_fast_regime_fixed(
    *,
    symbol: str,
    bundle,
    features_df: pd.DataFrame,
    start_date: str,
    end_date: Optional[str],
    horizon_days: Optional[int],
    n_scenarios: int,
    primary_alpha: float,
    alphas: Optional[List[float]],
    seed: int,
    return_format: str,
) -> Dict[str, Any]:
    out = forecast_horizon(
        bundle=bundle,
        features_df=features_df,
        start_date=start_date,
        end_date=end_date,
        horizon_days=horizon_days,
        n_scenarios=n_scenarios,
        alpha=primary_alpha,
        seed=seed,
    )

    summary = format_summary(out.summary, return_format)

    risk = None
    if alphas is not None:
        risk = format_risk_curve_from_samples(np.asarray(out.samples), alphas, return_format)

    return {
        "start_date": str(out.start_date.date()),
        "end_date": str(out.end_date.date()),
        "horizon_days": int(out.horizon_days),
        "summary": summary,
        "risk": risk,
        "metrics": None,
        "risk_curve_metrics": None,
    }


def _run_path_engine(
    *,
    symbol: str,
    features_df: pd.DataFrame,
    start_date: str,
    horizon_days: int,
    n_scenarios: int,
    seed: int,
    primary_alpha: float,
    alphas: Optional[List[float]],
    return_format: str,
    model_type: Literal["quantile_ml_walk_forward", "regime_similarity"],
) -> Dict[str, Any]:
    engine = ScenarioEngine(features_df=features_df)
    cfg = ScenarioConfig(
        asset=symbol,
        horizon_days=int(horizon_days),
        n_scenarios=int(n_scenarios),
        seed=int(seed),
        model_type=model_type,
    )

    out = engine.run(cfg)
    paths = out["paths"]

    met = compute_metrics_and_curve(
        paths,
        primary_alpha=primary_alpha,
        alphas=alphas,
        return_format=return_format,
    )

    sd = pd.to_datetime(start_date)
    ed = (sd + pd.Timedelta(days=int(horizon_days))).date()

    return {
        "start_date": str(sd.date()),
        "end_date": str(ed),
        "horizon_days": int(horizon_days),
        "summary": None,
        "risk": None,
        "metrics": met["metrics"],
        "risk_curve_metrics": met["risk_curve_metrics"],
    }


def _run_ensemble(
    *,
    symbol: str,
    features_df: pd.DataFrame,
    start_date: str,
    horizon_days: int,
    n_scenarios: int,
    seed: int,
    primary_alpha: float,
    alphas: Optional[List[float]],
    return_format: str,
) -> Dict[str, Any]:
    a = _run_path_engine(
        symbol=symbol,
        features_df=features_df,
        start_date=start_date,
        horizon_days=horizon_days,
        n_scenarios=n_scenarios,
        seed=seed,
        primary_alpha=primary_alpha,
        alphas=alphas,
        return_format=return_format,
        model_type="quantile_ml_walk_forward",
    )
    b = _run_path_engine(
        symbol=symbol,
        features_df=features_df,
        start_date=start_date,
        horizon_days=horizon_days,
        n_scenarios=n_scenarios,
        seed=seed,
        primary_alpha=primary_alpha,
        alphas=alphas,
        return_format=return_format,
        model_type="regime_similarity",
    )

    if return_format in ("log", "simple"):
        merged_metrics = conservative_merge_metrics(a["metrics"], b["metrics"])  # type: ignore[arg-type]
    else:
        merged_metrics = {
            "log": conservative_merge_metrics(a["metrics"]["log"], b["metrics"]["log"]),
            "simple": conservative_merge_metrics(a["metrics"]["simple"], b["metrics"]["simple"]),
        }

    merged_curve = None
    if a["risk_curve_metrics"] is not None and b["risk_curve_metrics"] is not None:
        merged_curve = {}
        for k in a["risk_curve_metrics"].keys():
            if k not in b["risk_curve_metrics"]:
                continue

            if return_format in ("log", "simple"):
                merged_curve[k] = conservative_merge_tail_only(a["risk_curve_metrics"][k], b["risk_curve_metrics"][k])
            else:
                merged_curve[k] = {
                    "log": conservative_merge_tail_only(a["risk_curve_metrics"][k]["log"], b["risk_curve_metrics"][k]["log"]),
                    "simple": conservative_merge_tail_only(a["risk_curve_metrics"][k]["simple"], b["risk_curve_metrics"][k]["simple"]),
                }

    return {
        "start_date": a["start_date"],
        "end_date": a["end_date"],
        "horizon_days": a["horizon_days"],
        "summary": None,
        "risk": None,
        "metrics": merged_metrics,
        "risk_curve_metrics": merged_curve,
    }


# -----------------------------
# Endpoints
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/forecast/horizon", response_model=HorizonResponse)
async def forecast_horizon_endpoint(req: HorizonRequest):
    _validate_horizon_args(req.end_date, req.horizon_days)
    _validate_alphas(req.alphas)

    primary_alpha = _resolve_primary_alpha(req.alpha, req.risk_level)

    if req.engine in ("walkforward_ml", "regime_similarity", "ensemble") and req.horizon_days is None:
        raise HTTPException(status_code=400, detail="horizon_days is required for path-based engines.")

    _guardrails(req.engine, req.n_scenarios, req.horizon_days, symbols_count=1)
    timeout_s = req.timeout_seconds or DEFAULT_TIMEOUT_SINGLE

    features_df = load_features_df(req.symbol)

    bundle = None
    if req.engine == "fast_regime_fixed":
        try:
            bundle = load_bundle(req.symbol)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse coins.json: {e}")

    symbol = req.symbol.upper().strip()

    def _compute():
        if req.engine == "fast_regime_fixed":
            return _run_fast_regime_fixed(
                symbol=symbol,
                bundle=bundle,
                features_df=features_df,
                start_date=req.start_date,
                end_date=req.end_date,
                horizon_days=req.horizon_days,
                n_scenarios=req.n_scenarios,
                primary_alpha=primary_alpha,
                alphas=req.alphas,
                seed=req.seed,
                return_format=req.return_format,
            )

        if req.engine == "walkforward_ml":
            return _run_path_engine(
                symbol=symbol,
                features_df=features_df,
                start_date=req.start_date,
                horizon_days=int(req.horizon_days),  # type: ignore[arg-type]
                n_scenarios=req.n_scenarios,
                seed=req.seed,
                primary_alpha=primary_alpha,
                alphas=req.alphas,
                return_format=req.return_format,
                model_type="quantile_ml_walk_forward",
            )

        if req.engine == "regime_similarity":
            return _run_path_engine(
                symbol=symbol,
                features_df=features_df,
                start_date=req.start_date,
                horizon_days=int(req.horizon_days),  # type: ignore[arg-type]
                n_scenarios=req.n_scenarios,
                seed=req.seed,
                primary_alpha=primary_alpha,
                alphas=req.alphas,
                return_format=req.return_format,
                model_type="regime_similarity",
            )

        if req.engine == "ensemble":
            return _run_ensemble(
                symbol=symbol,
                features_df=features_df,
                start_date=req.start_date,
                horizon_days=int(req.horizon_days),  # type: ignore[arg-type]
                n_scenarios=req.n_scenarios,
                seed=req.seed,
                primary_alpha=primary_alpha,
                alphas=req.alphas,
                return_format=req.return_format,
            )

        raise ValueError(f"Unknown engine: {req.engine}")

    out = await _run_with_timeout(timeout_s, _compute)

    assumptions: Dict[str, Any] = {
        "engine": req.engine,
        "timeout_seconds": timeout_s,
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
    }
    if req.risk_level is not None:
        assumptions["risk_level"] = req.risk_level
        assumptions["risk_level_alpha"] = primary_alpha
    if req.alphas is not None:
        assumptions["risk_curve_alphas"] = [float(a) for a in req.alphas]

    return HorizonResponse(
        symbol=symbol,
        start_date=out["start_date"],
        end_date=out["end_date"],
        horizon_days=out["horizon_days"],
        n_scenarios=req.n_scenarios,
        alpha=primary_alpha,
        engine=req.engine,
        assumptions=assumptions,
        summary=out["summary"],
        risk=out["risk"],
        metrics=out["metrics"],
        risk_curve_metrics=out["risk_curve_metrics"],
    )


@app.post("/forecast/horizon/multi", response_model=MultiHorizonResponse)
async def forecast_horizon_multi_endpoint(req: MultiHorizonRequest):
    _validate_horizon_args(req.end_date, req.horizon_days)
    _validate_alphas(req.alphas)

    primary_alpha = _resolve_primary_alpha(req.alpha, req.risk_level)

    if req.engine in ("walkforward_ml", "regime_similarity", "ensemble") and req.horizon_days is None:
        raise HTTPException(status_code=400, detail="horizon_days is required for path-based engines.")

    _guardrails(req.engine, req.n_scenarios, req.horizon_days, symbols_count=len(req.symbols))
    timeout_s = req.timeout_seconds or DEFAULT_TIMEOUT_MULTI

    symbols = [s.upper().strip() for s in req.symbols]
    if any(not s for s in symbols):
        raise HTTPException(status_code=400, detail="symbols must not contain empty strings.")

    def _compute_all():
        results: List[HorizonResponse] = []
        for symbol in symbols:
            features_df = load_features_df(symbol)

            bundle = None
            if req.engine == "fast_regime_fixed":
                bundle = load_bundle(symbol)

            if req.engine == "fast_regime_fixed":
                out = _run_fast_regime_fixed(
                    symbol=symbol,
                    bundle=bundle,
                    features_df=features_df,
                    start_date=req.start_date,
                    end_date=req.end_date,
                    horizon_days=req.horizon_days,
                    n_scenarios=req.n_scenarios,
                    primary_alpha=primary_alpha,
                    alphas=req.alphas,
                    seed=req.seed,
                    return_format=req.return_format,
                )
            elif req.engine == "walkforward_ml":
                out = _run_path_engine(
                    symbol=symbol,
                    features_df=features_df,
                    start_date=req.start_date,
                    horizon_days=int(req.horizon_days),  # type: ignore[arg-type]
                    n_scenarios=req.n_scenarios,
                    seed=req.seed,
                    primary_alpha=primary_alpha,
                    alphas=req.alphas,
                    return_format=req.return_format,
                    model_type="quantile_ml_walk_forward",
                )
            elif req.engine == "regime_similarity":
                out = _run_path_engine(
                    symbol=symbol,
                    features_df=features_df,
                    start_date=req.start_date,
                    horizon_days=int(req.horizon_days),  # type: ignore[arg-type]
                    n_scenarios=req.n_scenarios,
                    seed=req.seed,
                    primary_alpha=primary_alpha,
                    alphas=req.alphas,
                    return_format=req.return_format,
                    model_type="regime_similarity",
                )
            else:
                out = _run_ensemble(
                    symbol=symbol,
                    features_df=features_df,
                    start_date=req.start_date,
                    horizon_days=int(req.horizon_days),  # type: ignore[arg-type]
                    n_scenarios=req.n_scenarios,
                    seed=req.seed,
                    primary_alpha=primary_alpha,
                    alphas=req.alphas,
                    return_format=req.return_format,
                )

            assumptions: Dict[str, Any] = {
                "engine": req.engine,
                "timeout_seconds": timeout_s,
                "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
            }
            if req.risk_level is not None:
                assumptions["risk_level"] = req.risk_level
                assumptions["risk_level_alpha"] = primary_alpha
            if req.alphas is not None:
                assumptions["risk_curve_alphas"] = [float(a) for a in req.alphas]

            results.append(
                HorizonResponse(
                    symbol=symbol,
                    start_date=out["start_date"],
                    end_date=out["end_date"],
                    horizon_days=out["horizon_days"],
                    n_scenarios=req.n_scenarios,
                    alpha=primary_alpha,
                    engine=req.engine,
                    assumptions=assumptions,
                    summary=out["summary"],
                    risk=out["risk"],
                    metrics=out["metrics"],
                    risk_curve_metrics=out["risk_curve_metrics"],
                )
            )

        return MultiHorizonResponse(results=results)

    return await _run_with_timeout(timeout_s, _compute_all)


# -----------------------------
# NEW Endpoint: Portfolio recommendation
# -----------------------------
@app.post("/portfolio/recommend", response_model=PortfolioResponse)
async def portfolio_recommend_endpoint(req: PortfolioRequest):
    symbols = [s.upper().strip() for s in req.symbols]
    if any(not s for s in symbols):
        raise HTTPException(status_code=400, detail="symbols must not contain empty strings.")
    if len(symbols) > MAX_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Too many symbols. max={MAX_SYMBOLS}")
    if req.horizon_days > MAX_HORIZON_DAYS:
        raise HTTPException(status_code=400, detail=f"horizon_days too large. max={MAX_HORIZON_DAYS}")

    if req.engine not in ("walkforward_ml", "regime_similarity", "ensemble"):
        raise HTTPException(status_code=400, detail="portfolio endpoint supports walkforward_ml | regime_similarity | ensemble only.")

    _guardrails("ensemble" if req.engine == "ensemble" else req.engine, req.n_scenarios, req.horizon_days, symbols_count=len(symbols))
    timeout_s = req.timeout_seconds or DEFAULT_TIMEOUT_MULTI

    def _compute_portfolio():
        engine = str(req.engine).strip().lower()

        # 1) assets dict: symbol -> {price_df, features_df}
        assets: Dict[str, Dict[str, pd.DataFrame]] = {}
        for sym in symbols:
            price_df = load_price_df(sym)
            features_df = load_features_df(sym)
            assets[sym] = {"price_df": price_df, "features_df": features_df}

        # 2) choose model types
        if engine == "ensemble":
            model_types = [MODEL_TYPE_A, MODEL_TYPE_B]
        else:
            mt = ENGINE_TO_MODEL_TYPE.get(engine)
            if mt is None:
                raise HTTPException(status_code=400, detail="Invalid engine for portfolio. Use: walkforward_ml | regime_similarity | ensemble")
            model_types = [mt]

        # 3) run pipeline once or twice
        outs: List[Dict[str, Any]] = []
        for mt in model_types:
            cfg = PortfolioPipelineConfig(
                horizon_days=int(req.horizon_days),
                n_scenarios=int(req.n_scenarios),
                seed=int(req.seed),
                model_type=mt,
                confidence_levels=list(req.confidence_levels) if req.confidence_levels else None,
                user_risk_tolerance=float(req.user_risk_tolerance),
                top_k=int(req.top_k),
                max_weight_per_asset=float(req.max_weight),
                min_weight_per_asset=float(req.min_weight),
                allow_cash=bool(req.allow_cash),
            )
            outs.append(run_portfolio_pipeline(assets=assets, cfg=cfg))

        # Single-engine
        if len(outs) == 1:
            return outs[0]

        # 4) ENSEMBLE: conservative merge risks + rebuild portfolio using merged risks
        out_a, out_b = outs

        # Conservative merge RiskReport objects
        merged_risks: Dict[str, RiskReport] = {}
        for sym in out_a["risks"].keys():
            merged_risks[sym] = _merge_risk_reports_conservative(out_a["risks"][sym], out_b["risks"][sym])

        # Rebuild portfolio using scenarios from A (paths are heavy; we keep scenarios internal, but portfolio needs them)
        constraints = PortfolioConstraints(
            user_risk_tolerance=float(req.user_risk_tolerance),
            max_weight_per_asset=float(req.max_weight),
            min_weight_per_asset=float(req.min_weight),
            top_k=int(req.top_k),
            allow_cash=bool(req.allow_cash),
        )

        # build_portfolio expects: scenario_outputs, risks, constraints
        portfolio = build_portfolio(out_a["scenarios"], merged_risks, constraints)

        return {
            "scenarios": out_a["scenarios"],   # keep for building; response serialization can omit or keep (we don't expose raw paths anyway)
            "risks": merged_risks,
            "portfolio": portfolio,
        }

    out = await _run_with_timeout(timeout_s, _compute_portfolio)

    assumptions = {
        "engine": req.engine,
        "timeout_seconds": timeout_s,
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
        "horizon_days": req.horizon_days,
        "n_scenarios": req.n_scenarios,
        "confidence_levels": req.confidence_levels,
        "portfolio_constraints": {
            "user_risk_tolerance": req.user_risk_tolerance,
            "top_k": req.top_k,
            "max_weight": req.max_weight,
            "min_weight": req.min_weight,
            "allow_cash": req.allow_cash,
        },
    }
    if req.engine == "ensemble":
        assumptions["ensemble_models"] = [MODEL_TYPE_A, MODEL_TYPE_B]

    # Serialize outputs (dataclasses -> dict)
    risks_json = {k: _as_jsonable(v) for k, v in out["risks"].items()}
    portfolio_json = _as_jsonable(out["portfolio"])

    return PortfolioResponse(
        assumptions=assumptions,
        risks=risks_json,
        portfolio=portfolio_json,
    )