# app/main.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal, Dict, Any, List, Deque
import json
import time
from collections import deque
from dataclasses import asdict, is_dataclass

import numpy as np
import pandas as pd
import anyio

# Setup numpy compatibility for old pickles
from core.numpy_compat import setup_numpy_compatibility
setup_numpy_compatibility()

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Fast (regime-fixed) horizon sampling
from core.models.horizon_scenarios import forecast_horizon
from core.models.model_bundle_loader import load_quantile_model_bundle

# VaR/CVaR helper for regime-fixed risk curve (on samples)
from core.models.probabilistic_quantile import var_cvar

# Path engines + metrics
from core.pipelines.scenario_engine import ScenarioEngine, ScenarioConfig
from core.models.scenario_metrics import compute_scenario_metrics, MetricsConfig

# NEW: portfolio stack (teammate changes)
from core.pipelines.portfolio_pipeline import run_portfolio_pipeline, PortfolioPipelineConfig
from core.risk.schemas import RiskConfig, RiskReport

# Call All Core Services (regime matching, scenario engine, risk, portfolio) in one workflow
from core.services.user_portfolio_workflow import run_Crypto_Return_Service

# Explanation engine (LLM-first + deterministic fallback)
from core.explain.explanation_agent import load_explanation_engine_from_env
from core.explain.fallback import (
    explain_crypto_return_service_fallback,
    explain_forecast_fallback,
    explain_portfolio_fallback,
)
from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository

from fastapi.middleware.cors import CORSMiddleware

# -----------------------------
# Frontend (React/Vite build)
# -----------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = ROOT_DIR / "crypto-risk-dashboard" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"


app = FastAPI(
    title="Agentic Probabilistic Crypto Return Service",
    version="0.1.0",
    description="API for probabilistic crypto risk forecasting using multiple scenario engines + portfolio layer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_ASSETS_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="static")


# -----------------------------
# Error handling
# -----------------------------
@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    # Converts missing artifact/CSV crashes into clean 404s
    return JSONResponse(status_code=404, content={"detail": str(exc)})


MODELS_DIR = ROOT_DIR / "artifacts" / "models"


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

# Global explanation engine (safe: falls back if disabled/unconfigured)
EXPLAIN_ENGINE = load_explanation_engine_from_env()


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


# -----------------------------
# Explanation engine (fallback-first, LLM-ready)
# -----------------------------
EXPLANATION_DISCLAIMER = (
    "Disclaimer: This is an educational, automatically generated explanation. "
    "It is not financial advice and does not guarantee future performance."
)



# -----------------------------
# Explanation helpers
# -----------------------------
def _pydantic_dump(model: Any) -> Dict[str, Any]:
    """Pydantic v1/v2 compatible dump to dict."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()  # type: ignore[return-value]


async def _build_explanation(
    *,
    target: str,
    mode: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Return an explanation dict. If mode='fallback', force deterministic fallback."""
    if mode == "fallback":
        if target == "crypto_return_service":
            return explain_crypto_return_service_fallback(payload)
        return explain_portfolio_fallback(payload) if target == "portfolio" else explain_forecast_fallback(payload)
    # mode == "llm" (LLM-first engine will still fallback safely if unconfigured)
    return await EXPLAIN_ENGINE.explain(target=target, payload=payload)

def _fmt_pct(x: Optional[float]) -> Optional[str]:
    if x is None:
        return None
    try:
        return f"{100.0 * float(x):.2f}%"
    except Exception:
        return None


def build_fallback_forecast_explanation(
    *,
    symbol: str,
    engine: str,
    horizon_days: int,
    alpha: float,
    return_format: str,
    summary: Optional[Dict[str, Any]],
    metrics: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Deterministic explanation based on returned fields.
    Kept simple + stable for zero-cost deployments.
    """
    bullets: List[str] = []
    bullets.append(f"Symbol: {symbol}")
    bullets.append(f"Engine: {engine} (scenario generator)")
    bullets.append(f"Horizon: {horizon_days} day(s)")
    bullets.append(f"Tail risk alpha: {alpha} (lower = more conservative tail focus)")
    bullets.append(f"Return format: {return_format}")

    # Regime-fixed summaries
    if summary:
        for k in ["mean", "median", "p05", "p95"]:
            if k in summary:
                bullets.append(f"Summary {k}: {summary[k]}")
        for k in ["VaR_5", "CVaR_5", "VaR_1", "CVaR_1", "VaR_10", "CVaR_10"]:
            if k in summary:
                bullets.append(f"{k}: {summary[k]}")

    # Path-engine metrics (can be nested under log/simple/both)
    if metrics:
        m = metrics
        if isinstance(metrics, dict) and "log" in metrics and "simple" in metrics:
            # choose log for narrative by default
            m = metrics.get("log") or metrics

        if isinstance(m, dict):
            hrs = m.get("horizon_return_summary")
            if isinstance(hrs, dict):
                for k in ["mean", "median", "p05", "p95"]:
                    if k in hrs:
                        bullets.append(f"Horizon return {k}: {hrs[k]}")

            pp = m.get("prob_profit")
            pl = m.get("prob_loss")
            if pp is not None:
                bullets.append(f"Probability of profit: {_fmt_pct(pp) or pp}")
            if pl is not None:
                bullets.append(f"Probability of loss: {_fmt_pct(pl) or pl}")

            vc = m.get("VaR_CVaR_horizon_return")
            if isinstance(vc, dict):
                if "VaR" in vc:
                    bullets.append(f"VaR (horizon return): {vc['VaR']}")
                if "CVaR" in vc:
                    bullets.append(f"CVaR (horizon return): {vc['CVaR']}")

    text = (
        "How to read this forecast:\n"
        "- Returns are simulated scenarios, not point predictions.\n"
        "- VaR is the loss threshold at the chosen tail level; CVaR is the average loss beyond VaR.\n"
        "- Higher prob_loss / more negative CVaR means higher downside risk.\n"
    )

    return {
        "mode": "fallback",
        "disclaimer": EXPLANATION_DISCLAIMER,
        "highlights": bullets[:12],
        "text": text,
    }


def build_fallback_portfolio_explanation(
    *,
    engine: str,
    symbols: List[str],
    horizon_days: int,
    confidence_levels: List[float],
    portfolio: Dict[str, Any],
    risks: Dict[str, Any],
) -> Dict[str, Any]:
    bullets: List[str] = []
    bullets.append(f"Engine: {engine}")
    bullets.append(f"Assets evaluated: {', '.join(symbols)}")
    bullets.append(f"Horizon: {horizon_days} day(s)")
    bullets.append(f"Confidence levels: {confidence_levels}")

    weights = portfolio.get("weights", {})
    if isinstance(weights, dict) and weights:
        top = sorted(weights.items(), key=lambda kv: float(kv[1]), reverse=True)[:5]
        bullets.append("Top weights: " + ", ".join([f"{k}={v:.3f}" for k, v in top]))

    if risks and confidence_levels:
        conf_key = f"p{int(round(confidence_levels[0]*100))}"
        worst = None
        for sym, rr in risks.items():
            try:
                c = rr.get("cvar", {}).get(conf_key)
                if c is None:
                    continue
                c = float(c)
                if worst is None or c < worst[1]:
                    worst = (sym, c)
            except Exception:
                continue
        if worst:
            bullets.append(f"Worst CVaR at {conf_key}: {worst[0]} ({worst[1]})")

    text = (
        "How to read this portfolio:\n"
        "- Weights are a suggested allocation under the provided constraints.\n"
        "- Risk metrics are scenario-based estimates (VaR/CVaR, drawdown).\n"
        "- Cash may be included if allow_cash=true and the optimizer prefers it under risk tolerance.\n"
    )

    return {
        "mode": "fallback",
        "disclaimer": EXPLANATION_DISCLAIMER,
        "highlights": bullets[:12],
        "text": text,
    }


def log_to_simple(x: float) -> float:
    return float(np.exp(x) - 1.0)


def _fallback_symbol_to_ticker_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if MODELS_DIR.exists():
        for child in sorted(MODELS_DIR.iterdir()):
            if not child.is_dir():
                continue
            ticker = child.name.strip().upper()
            if not ticker:
                continue
            symbol = ticker.split("-", 1)[0]
            if symbol and ticker.endswith("-USD"):
                mapping[symbol] = ticker
    return mapping


def load_symbol_to_yahoo_ticker() -> Dict[str, str]:
    try:
        mapping = get_coin_repository().get_symbol_to_ticker_map()
    except Exception:
        mapping = _fallback_symbol_to_ticker_map()
    if not mapping:
        raise FileNotFoundError("No symbol->yahoo_ticker mappings found in Coins table or model artifacts.")
    return mapping


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
        raise FileNotFoundError(f"No yahoo_ticker mapping found for symbol={sym} in Coins table.")

    path = MODELS_DIR / ticker / "quantile_model_bundle.joblib"
    obj = load_quantile_model_bundle(path, symbol=sym, ticker=ticker)
    return obj["bundle"]


def load_features_df(symbol: str) -> pd.DataFrame:
    df = get_market_data_repository().read_features(symbol=symbol)
    if df.empty:
        raise FileNotFoundError(f"Features data not found for symbol={symbol.upper()}.")
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


def load_price_df(symbol: str) -> pd.DataFrame:
    """
    Portfolio pipeline expects a 'price_df' per asset.
    We load OHLCV rows from the database and keep at least date/close columns.
    """
    global _SYMBOL_TO_TICKER
    sym = symbol.upper().strip()
    if _SYMBOL_TO_TICKER is None:
        _SYMBOL_TO_TICKER = load_symbol_to_yahoo_ticker()

    ticker = _SYMBOL_TO_TICKER.get(sym)
    if not ticker:
        raise FileNotFoundError(f"No yahoo_ticker mapping found for symbol={sym} in Coins table.")

    df = get_market_data_repository().read_ohlcv(yahoo_ticker=ticker)
    if df.empty:
        raise FileNotFoundError(f"OHLCV data not found for symbol={sym}.")
    if "date" not in df.columns:
        raise HTTPException(status_code=500, detail=f"OHLCV data missing 'date' column for symbol={sym}.")
    if "close" not in df.columns:
        if "Close" in df.columns:
            df = df.rename(columns={"Close": "close"})
        else:
            raise HTTPException(status_code=500, detail=f"OHLCV data missing 'close' column for symbol={sym}.")

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
    m = json.loads(json.dumps(metrics))  # deep-ish copy (safe for JSON-like dicts)

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
    """
    Returns:
      {
        "metrics": {...},                 # computed at primary_alpha
        "risk_curve_metrics": {...}|None  # multi-alpha metrics subset
      }
    """
    metrics = compute_scenario_metrics(paths, cfg=MetricsConfig(alpha=primary_alpha, use_log_returns=True))

    if return_format == "simple":
        metrics = _convert_metrics_returns_to_simple(metrics)
    elif return_format == "both":
        metrics = {
            "log": metrics,
            "simple": _convert_metrics_returns_to_simple(metrics),
        }

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
    """
    Conservative merge for FULL metrics dict:
    - worse tail risk (more negative VaR/CVaR)
    - higher prob_loss, lower prob_profit
    - lower upside
    """
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
    """
    Conservative merge for the SMALL tail-only dict used in risk_curve_metrics:
      { VaR_CVaR_horizon_return: {VaR,CVaR}, VaR_CVaR_max_drawdown: {VaR,CVaR} }
    """
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


def _merge_risk_reports_conservative(a: RiskReport, b: RiskReport) -> RiskReport:
    """
    Conservative merge for RiskReport:
    - var/cvar dictionaries: take worse tail (more negative)
    - max_drawdown_est: take worse (more negative), handling None safely
    - tail_metrics: conservative prob_loss/profit if present
    """

    var: Dict[str, float] = {}
    cvar: Dict[str, float] = {}

    for k in set(a.var.keys()) | set(b.var.keys()):
        if k in a.var and k in b.var:
            var[k] = min(float(a.var[k]), float(b.var[k]))
        elif k in a.var:
            var[k] = float(a.var[k])
        else:
            var[k] = float(b.var[k])

    for k in set(a.cvar.keys()) | set(b.cvar.keys()):
        if k in a.cvar and k in b.cvar:
            cvar[k] = min(float(a.cvar[k]), float(b.cvar[k]))
        elif k in a.cvar:
            cvar[k] = float(a.cvar[k])
        else:
            cvar[k] = float(b.cvar[k])

    if a.max_drawdown_est is None and b.max_drawdown_est is None:
        max_dd = None
    elif a.max_drawdown_est is None:
        max_dd = float(b.max_drawdown_est)
    elif b.max_drawdown_est is None:
        max_dd = float(a.max_drawdown_est)
    else:
        max_dd = min(float(a.max_drawdown_est), float(b.max_drawdown_est))

    tail: Dict[str, Any] = {}
    tail.update(a.tail_metrics or {})
    tb = b.tail_metrics or {}

    if "prob_loss" in tail or "prob_loss" in tb:
        tail["prob_loss"] = max(
            float(tail.get("prob_loss", 0.0)),
            float(tb.get("prob_loss", 0.0)),
        )

    if "prob_profit" in tail or "prob_profit" in tb:
        tail["prob_profit"] = min(
            float(tail.get("prob_profit", 1.0)),
            float(tb.get("prob_profit", 1.0)),
        )

    notes: List[str] = []
    if a.notes:
        notes.extend(a.notes)
    if b.notes:
        notes.extend(b.notes)
    notes.append("Conservative merge across engines (ensemble).")

    return RiskReport(
        symbol=a.symbol,
        horizon_days=a.horizon_days,
        var=var,
        cvar=cvar,
        max_drawdown_est=max_dd,
        tail_metrics=tail,
        notes=notes,
    )


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

    # Optional: attach natural-language explanation to the response
    include_explanation: bool = Field(False, description="If true, include an explanation field in the response.")
    explanation_mode: Literal["fallback", "llm"] = Field("fallback", description="Explanation mode: fallback (deterministic) or llm (if configured).")


class HorizonResponse(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    horizon_days: int
    n_scenarios: int
    alpha: float
    engine: str
    assumptions: Dict[str, Any]

    # regime-fixed output
    summary: Optional[Dict[str, float]] = None
    risk: Optional[Dict[str, float]] = None

    # path-engine output
    metrics: Optional[Dict[str, Any]] = None
    risk_curve_metrics: Optional[Dict[str, Any]] = None

    # Optional explanation payload (deterministic fallback or LLM-generated)
    explanation: Optional[Dict[str, Any]] = None


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

    # Optional: attach natural-language explanation to each result
    include_explanation: bool = Field(False, description="If true, include explanation fields in each result.")
    explanation_mode: Literal["fallback", "llm"] = Field("fallback", description="Explanation mode: fallback (deterministic) or llm (if configured).")


class MultiHorizonResponse(BaseModel):
    results: List[HorizonResponse]


# -----------------------------
# Schemas: Portfolio (NEW)
# -----------------------------
PortfolioEngine = Literal["walkforward_ml", "regime_similarity", "ensemble"]


class PortfolioRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, description="Portfolio asset symbols, e.g. ['BTC','ETH']")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    horizon_days: int = Field(..., ge=1, le=252)

    engine: PortfolioEngine = Field("ensemble", description="walkforward_ml | regime_similarity | ensemble")
    n_scenarios: int = Field(3000, ge=100, le=50000)
    seed: int = 42

    # Risk config for portfolio layer
    confidence_levels: List[float] = Field(default_factory=lambda: [0.95], description="e.g., [0.95]")

    # Allocation constraints
    user_risk_tolerance: int = Field(50, ge=0, le=100, description="0=conservative, 100=aggressive")
    top_k: int = Field(5, ge=1, le=20)
    max_weight: float = Field(0.50, gt=0.0, le=1.0)
    min_weight: float = Field(0.00, ge=0.0, le=1.0)
    allow_cash: bool = True

    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)

    # Optional: attach natural-language explanation to the response
    include_explanation: bool = Field(False, description="If true, include an explanation field in the response.")
    explanation_mode: Literal["fallback", "llm"] = Field("fallback", description="Explanation mode: fallback (deterministic) or llm (if configured).")


class PortfolioResponse(BaseModel):
    assumptions: Dict[str, Any]
    risks: Dict[str, Any]
    portfolio: Dict[str, Any]

    # Optional explanation payload (deterministic fallback or LLM-generated)
    explanation: Optional[Dict[str, Any]] = None


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
    paths = out["paths"]  # ndarray (n_scenarios, horizon_days+1)

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
                merged_curve[k] = conservative_merge_tail_only(
                    a["risk_curve_metrics"][k],
                    b["risk_curve_metrics"][k],
                )
            else:
                merged_curve[k] = {
                    "log": conservative_merge_tail_only(
                        a["risk_curve_metrics"][k]["log"],
                        b["risk_curve_metrics"][k]["log"],
                    ),
                    "simple": conservative_merge_tail_only(
                        a["risk_curve_metrics"][k]["simple"],
                        b["risk_curve_metrics"][k]["simple"],
                    ),
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

def serialize_crypto_return_service_result(result: dict) -> dict:
    risks = {k: vars(v) for k, v in result["risks"].items()}

    portfolio_obj = result["portfolio"]
    portfolio_dict = vars(portfolio_obj).copy()
    portfolio_dict["details"] = [vars(item) for item in portfolio_obj.details]

    scenario_engine_serialized = {}

    for asset, se in result["scenario_engine"].items():
        se_dict = dict(se)

        if "paths" in se_dict and hasattr(se_dict["paths"], "tolist"):
            se_dict["paths"] = se_dict["paths"].tolist()

        scenario_engine_serialized[asset] = se_dict

    response = {
        "input": result.get("input"),
        "regime_matching": result["regime_matching"],
        "scenario_engine": scenario_engine_serialized,
        "risks": risks,
        "portfolio": portfolio_dict,
    }
    if "explanation" in result:
        response["explanation"] = result["explanation"]
    return response

# -----------------------------
# Endpoints
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/assets/options")
def list_asset_options():
    rows = []
    try:
        for symbol, yahoo_ticker in sorted(_fallback_symbol_to_ticker_map().items()):
            rows.append(
                {
                    "symbol": symbol,
                    "yahoo_ticker": yahoo_ticker,
                }
            )
        if rows:
            return {"items": rows}

        repository = get_coin_repository()
        for coin in repository.as_dataframe().sort_values(by=["symbol"]).to_dict(orient="records"):
            yahoo_ticker = str(coin.get("yahoo_ticker", "")).strip().upper()
            symbol = str(coin.get("symbol", "")).strip().upper()
            if not yahoo_ticker:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "yahoo_ticker": yahoo_ticker,
                }
            )
    except Exception:
        for symbol, yahoo_ticker in load_symbol_to_yahoo_ticker().items():
            rows.append(
                {
                    "symbol": symbol,
                    "yahoo_ticker": yahoo_ticker,
                }
            )
    return {"items": rows}

from app.schemas.crypto_return_service import CryptoReturnServiceRequest

@app.post("/crypto_return_service")
async def crypto_return_service(request: CryptoReturnServiceRequest):
    user_input = _pydantic_dump(request)
    result = await anyio.to_thread.run_sync(run_Crypto_Return_Service, user_input)
    serialized = serialize_crypto_return_service_result(result)

    if request.include_explanation:
        serialized["explanation"] = await _build_explanation(
            target="crypto_return_service",
            mode=request.explanation_mode,
            payload=serialized,
        )

    return serialized
    
#-----------------------------------------------------------    

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
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

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

    resp = HorizonResponse(
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
        explanation=None,
    )

    if req.include_explanation:
        payload = _pydantic_dump(resp)
        payload["explanation"] = None
        resp.explanation = await _build_explanation(
            target="forecast",
            mode=req.explanation_mode,
            payload=payload,
        )

    return resp


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

    def _compute_all_sync():
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

            resp = HorizonResponse(
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
                explanation=None,
            )

            results.append(resp)

        return results


    results = await _run_with_timeout(timeout_s, _compute_all_sync)

    if req.include_explanation:
        for resp in results:
            payload = _pydantic_dump(resp)
            payload["explanation"] = None
            resp.explanation = await _build_explanation(
                target="forecast",
                mode=req.explanation_mode,
                payload=payload,
            )

    return MultiHorizonResponse(results=results)


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
        raise HTTPException(
            status_code=400,
            detail="portfolio endpoint supports walkforward_ml | regime_similarity | ensemble only.",
        )

    _guardrails(
        "ensemble" if req.engine == "ensemble" else req.engine,
        req.n_scenarios,
        req.horizon_days,
        symbols_count=len(symbols),
    )

    timeout_s = req.timeout_seconds or DEFAULT_TIMEOUT_MULTI

    def _compute_portfolio():
        print("[portfolio] start")
        engine = str(req.engine).strip().lower()
        print(f"[portfolio] engine={engine} symbols={req.symbols}")

        assets = {}
        for sym in [s.upper().strip() for s in req.symbols]:
            print(f"[portfolio] loading asset data for {sym}")
            price_df = load_price_df(sym)
            features_df = load_features_df(sym)
            print(f"[portfolio] {sym} price_rows={len(price_df)} feature_rows={len(features_df)}")
            assets[sym] = {"price_df": price_df, "features_df": features_df}

        if engine == "ensemble":
            model_types = [MODEL_TYPE_A, MODEL_TYPE_B]
        else:
            mt = ENGINE_TO_MODEL_TYPE.get(engine)
            if mt is None:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid engine for portfolio. Use: walkforward_ml | regime_similarity | ensemble",
                )
            model_types = [mt]

        print(f"[portfolio] model_types={model_types}")

        outs = []
        for mt in model_types:
            print(f"[portfolio] building config for model_type={mt}")
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
            print(f"[portfolio] running pipeline for model_type={mt}")
            out_i = run_portfolio_pipeline(assets=assets, cfg=cfg)
            print(f"[portfolio] pipeline finished for model_type={mt}")
            print(f"[portfolio] out keys={list(out_i.keys())}")
            outs.append(out_i)

        if len(outs) == 1:
            print("[portfolio] single-engine return")
            return outs[0]

        out_a, out_b = outs
        print("[portfolio] merging ensemble risk reports")

        merged_risks: Dict[str, RiskReport] = {}
        for sym in out_a["risks"].keys():
            if sym in out_b["risks"]:
                print(f"[portfolio] merging risk for {sym}")
                merged_risks[sym] = _merge_risk_reports_conservative(out_a["risks"][sym], out_b["risks"][sym])
            else:
                merged_risks[sym] = out_a["risks"][sym]

        merged_portfolio = out_a.get("portfolio")
        print("[portfolio] returning ensemble result")
        return {
            "scenarios": {},
            "risks": merged_risks,
            "portfolio": merged_portfolio,
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

    risks_json = {k: _as_jsonable(v) for k, v in out["risks"].items()}
    portfolio_json = _as_jsonable(out["portfolio"])

    resp = PortfolioResponse(
        assumptions=assumptions,
        risks=risks_json,
        portfolio=portfolio_json,
        explanation=None,
    )

    if req.include_explanation:
        payload = _pydantic_dump(resp)
        payload["explanation"] = None
        resp.explanation = await _build_explanation(
            target="portfolio",
            mode=req.explanation_mode,
            payload=payload,
        )

    return resp


# -----------------------------
# Frontend routes
# -----------------------------
@app.get("/")
def serve_frontend_root():
    if FRONTEND_DIST_DIR.exists():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend build not found. Run `npm run build` in crypto-risk-dashboard."},
    )


@app.get("/{full_path:path}")
def serve_frontend_spa(full_path: str):
    # Do not intercept API/docs/openapi routes
    if (
        full_path.startswith("forecast/")
        or full_path.startswith("portfolio/")
        or full_path.startswith("crypto_return_service")
        or full_path.startswith("health")
    ):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    if full_path in {"docs", "openapi.json", "redoc"}:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    target = FRONTEND_DIST_DIR / full_path
    if target.exists() and target.is_file():
        return FileResponse(target)

    if FRONTEND_DIST_DIR.exists():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend build not found. Run `npm run build` in crypto-risk-dashboard."},
    )
