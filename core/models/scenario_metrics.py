from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

import numpy as np


@dataclass
class MetricsConfig:
    alpha: float = 0.05
    use_log_returns: bool = True


def _var_cvar(x: np.ndarray, alpha: float) -> Dict[str, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"VaR": float("nan"), "CVaR": float("nan")}

    var = float(np.quantile(x, alpha))
    tail = x[x <= var]
    cvar = float(tail.mean()) if len(tail) > 0 else var
    return {"VaR": var, "CVaR": cvar}


# computes running peak, computes drawdown = price/peak - 1, returns the most negative drawdown (worst peak-to-trough decline
def _max_drawdown_from_prices(prices: np.ndarray) -> float:
    prices = np.asarray(prices, dtype=float)
    if len(prices) < 2 or not np.all(np.isfinite(prices)):
        return float("nan")

    peak = np.maximum.accumulate(prices)
    dd = (prices / peak) - 1.0
    return float(np.min(dd))


def compute_scenario_metrics(
    paths: np.ndarray,
    *,
    cfg: Optional[MetricsConfig] = None,
) -> Dict[str, Any]:

    cfg = cfg or MetricsConfig()
    alpha = float(cfg.alpha)

    paths = np.asarray(paths, dtype=float)
    if paths.ndim != 2 or paths.shape[1] < 2:
        raise ValueError("paths must be 2D with shape (n_scenarios, horizon_days+1)")

    start = paths[:, 0]
    terminal = paths[:, -1]

    # ===============================
    # Horizon Returns
    # ===============================

    if cfg.use_log_returns:
        horizon_ret = np.log(terminal / start)
    else:
        horizon_ret = (terminal / start) - 1.0

    def q(a: np.ndarray, p: float) -> float:
        a = a[np.isfinite(a)]
        return float(np.quantile(a, p)) if len(a) else float("nan")

    # ===============================
    # Terminal summaries
    # ===============================

    terminal_price_summary = {
        "mean": float(np.nanmean(terminal)),
        "median": q(terminal, 0.50),
        "p05": q(terminal, 0.05),
        "p95": q(terminal, 0.95),
    }

    horizon_return_summary = {
        "mean": float(np.nanmean(horizon_ret)),
        "median": q(horizon_ret, 0.50),
        "p05": q(horizon_ret, 0.05),
        "p95": q(horizon_ret, 0.95),
    }

    # ===============================
    # Probabilities: “Out of all simulated futures, what fraction end up positive vs negative?”
    # ===============================

    prob_profit = float(np.mean(horizon_ret > 0))
    prob_loss = float(np.mean(horizon_ret < 0))

    # ===============================
    # VaR / CVaR on Horizon Return
    # ===============================

    risk_horizon = _var_cvar(horizon_ret, alpha=alpha)

    # ===============================
    # Max Drawdown per path, then summarize across paths. VaR/CVaR on max drawdown too
    #So you get both:end-of-horizon loss risk and in-horizon crash risk
    # ===============================

    mdd = np.array([_max_drawdown_from_prices(p) for p in paths], dtype=float)

    mdd_summary = {
        "mean": float(np.nanmean(mdd)),
        "median": q(mdd, 0.50),
        "p05": q(mdd, 0.05),
        "p95": q(mdd, 0.95),
    }

    risk_mdd = _var_cvar(mdd, alpha=alpha)

    # ===============================
    # Profit / Loss Decomposition
    # ===============================

    profit_mask = horizon_ret > 0
    loss_mask = horizon_ret < 0

    profit_returns = horizon_ret[profit_mask]
    loss_returns = horizon_ret[loss_mask]

    profit_mdd = mdd[profit_mask]
    loss_mdd = mdd[loss_mask]

    profit_stats = {}
    loss_stats = {}

    if len(profit_returns) > 0:
        profit_stats = {
            "count": int(len(profit_returns)),
            "mean_profit": float(np.mean(profit_returns)),
            "max_profit": float(np.max(profit_returns)),
            "min_profit": float(np.min(profit_returns)),
            "mean_max_drawdown": float(np.mean(profit_mdd)),
        }

    if len(loss_returns) > 0:
        loss_stats = {
            "count": int(len(loss_returns)),
            "mean_loss": float(np.mean(loss_returns)),
            "worst_loss": float(np.min(loss_returns)),   # most negative
            "smallest_loss": float(np.max(loss_returns)),
        }

    # ===============================
    # Final Output
    # ===============================

    return {
        "n_scenarios": int(paths.shape[0]),
        "horizon_days": int(paths.shape[1] - 1),

        "terminal_price_summary": terminal_price_summary,
        "horizon_return_summary": horizon_return_summary,

        "prob_profit": prob_profit,
        "prob_loss": prob_loss,

        "VaR_CVaR_horizon_return": risk_horizon,

        "max_drawdown_summary": mdd_summary,
        "VaR_CVaR_max_drawdown": risk_mdd,

        "profit_analysis": profit_stats,
        "loss_analysis": loss_stats,
    }