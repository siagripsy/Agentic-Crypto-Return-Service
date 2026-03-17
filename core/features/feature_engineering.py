from __future__ import annotations
import pandas as pd
import numpy as np

DECIMAL_28_12_MAX = 9999999999999999.999999999999
DECIMAL_28_12_MIN = -DECIMAL_28_12_MAX
VOLATILITY_EPSILON = 1e-6
RISK_ADJ_RET_CLIP = 1_000_000.0
VOL_RATIO_CLIP = 1_000_000.0


def _clip_to_decimal_28_12(series: pd.Series) -> pd.Series:
    return series.clip(lower=DECIMAL_28_12_MIN, upper=DECIMAL_28_12_MAX)


def add_log_return_1d(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    """
    Adds 1-day log return:
        log_ret_1d[t] = ln(price[t] / price[t-1])

    Why log return?
    - It measures *percent-like* change but behaves nicely mathematically.
    - Log returns add across time (useful for horizons and modeling).
    - Common in finance ML because it stabilizes scale.
    """
    out = df.copy()

    # Ensure sorted by date so returns are correct
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    # Compute log return; first row becomes NaN (no previous day)
    out["log_ret_1d"] = np.log(out[price_col] / out[price_col].shift(1))

    # Convert date back to ISO string for consistent storage/merging
    out["date"] = out["date"].dt.date.astype(str)

    return out


def add_log_return_nd(df: pd.DataFrame, n: int, price_col: str = "close") -> pd.DataFrame:
    """
    Adds n-day log return:
        log_ret_{n}d[t] = ln(price[t] / price[t-n])

    Interpretation (simple):
    - 1d: today's change vs yesterday
    - 5d: today's change vs ~1 trading week ago
    - 10d: today's change vs ~2 weeks ago
    """
    out = df.copy()

    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    out[f"log_ret_{n}d"] = np.log(out[price_col] / out[price_col].shift(n))

    out["date"] = out["date"].dt.date.astype(str)
    return out


def add_rolling_volatility(df: pd.DataFrame, window: int, ret_col: str = "log_ret_1d") -> pd.DataFrame:
    """
    Adds rolling volatility = std of daily returns over a window:
        vol_{window}d[t] = std( log_ret_1d over last 'window' days )

    Why volatility matters:
    - It's basically "how stormy has the market been lately?"
    - High volatility regimes behave differently than low volatility regimes.
    """
    out = df.copy()

    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    out[f"vol_{window}d"] = out[ret_col].rolling(window=window).std()

    out["date"] = out["date"].dt.date.astype(str)
    return out

def add_risk_adjusted_return(df: pd.DataFrame,
                            ret_col: str = "log_ret_1d",
                            vol_col: str = "vol_30d") -> pd.DataFrame:
    """
    risk_adj_ret_1d = log_ret_1d / vol_30d

    Intuition:
    - normalizes today's move by "typical" recent volatility.
    - makes moves comparable across calm vs chaotic periods.
    """
    out = df.copy()
    denom = pd.to_numeric(out[vol_col], errors="coerce").abs().clip(lower=VOLATILITY_EPSILON)
    values = pd.to_numeric(out[ret_col], errors="coerce") / denom
    out["risk_adj_ret_1d"] = _clip_to_decimal_28_12(values.clip(lower=-RISK_ADJ_RET_CLIP, upper=RISK_ADJ_RET_CLIP))
    return out


def add_vol_ratio(df: pd.DataFrame,
                  short_vol_col: str = "vol_7d",
                  long_vol_col: str = "vol_30d") -> pd.DataFrame:
    """
    vol_ratio_7d_30d = vol_7d / vol_30d

    Intuition:
    - > 1 means volatility is higher recently than usual (spike).
    - < 1 means market is calming down.
    """
    out = df.copy()
    denom = pd.to_numeric(out[long_vol_col], errors="coerce").abs().clip(lower=VOLATILITY_EPSILON)
    numer = pd.to_numeric(out[short_vol_col], errors="coerce").abs()
    values = numer / denom
    out["vol_ratio_7d_30d"] = _clip_to_decimal_28_12(values.clip(lower=0.0, upper=VOL_RATIO_CLIP))
    return out


def add_drawdown(df: pd.DataFrame, window: int = 30, price_col: str = "close") -> pd.DataFrame:
    """
    drawdown_30d = close / rolling_max_30d(close) - 1

    Intuition:
    - 0 means we're at the recent peak.
    - -0.10 means we're 10% below the recent peak.
    """
    out = df.copy()

    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    rolling_max = out[price_col].rolling(window=window).max()
    out[f"drawdown_{window}d"] = (out[price_col] / rolling_max) - 1.0

    out["date"] = out["date"].dt.date.astype(str)
    return out


def drop_na_features(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """
    Drops rows where any required feature is NaN.
    This is safe for rolling-window features.
    """
    return df.dropna(subset=feature_cols).reset_index(drop=True)



def build_features_basic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Basic feature set v1 (ML-ready).
    Features we include:
    - log_ret_1d: daily change signal (core)
    - log_ret_5d: 1-week-ish momentum
    - log_ret_10d: 2-week-ish momentum
    - vol_7d: short-term risk / regime indicator
    - vol_30d: longer-term risk / regime indicator
    - creative features:
        risk_adj_ret_1d
        vol_ratio_7d_30d
        drawdown_30d
    """
    out = df.copy()

    # Returns (signals)
    out = add_log_return_1d(out, price_col="close")
    out = add_log_return_nd(out, n=5, price_col="close")
    out = add_log_return_nd(out, n=10, price_col="close")

    # Volatility (risk / regime)
    out = add_rolling_volatility(out, window=7, ret_col="log_ret_1d")
    out = add_rolling_volatility(out, window=30, ret_col="log_ret_1d")

    # New features
    out = add_risk_adjusted_return(out, ret_col="log_ret_1d", vol_col="vol_30d")
    out = add_vol_ratio(out, short_vol_col="vol_7d", long_vol_col="vol_30d")
    out = add_drawdown(out, window=30, price_col="close")

    # Clean rows that can't have these features yet (due to rolling windows)
    required = [
        "log_ret_1d", "log_ret_5d", "log_ret_10d",
        "vol_7d", "vol_30d",
        "risk_adj_ret_1d", "vol_ratio_7d_30d", "drawdown_30d"
    ]
    numeric_cols = [
        "open", "high", "low", "close", "volume", "market_cap",
        "log_ret_1d", "log_ret_5d", "log_ret_10d",
        "vol_7d", "vol_30d", "risk_adj_ret_1d", "vol_ratio_7d_30d", "drawdown_30d",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = _clip_to_decimal_28_12(pd.to_numeric(out[col], errors="coerce"))
    out = drop_na_features(out, required)

    return out



