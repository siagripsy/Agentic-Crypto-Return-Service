from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from core.models.horizon_scenarios import forecast_horizon
from core.models.model_bundle_loader import load_quantile_model_bundle
from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository

import sys
import numpy as np
import streamlit as st

#st.sidebar.caption(f"Python: {sys.executable}")
#st.sidebar.caption(f"NumPy: {np.__version__}")

# -----------------------------
# App config
# -----------------------------
st.set_page_config(
    page_title="Crypto Risk/Gain Forecast (Prototype)",
    layout="centered",
)

st.title("📈 Probabilistic Crypto Risk/Gain Forecast (Prototype)")
st.caption(
    "This dashboard loads a saved quantile model (joblib) and simulates horizon return scenarios "
    "under a regime-fixed assumption (features held constant over the horizon)."
)

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "artifacts" / "models"


# -----------------------------
# Helpers
# -----------------------------
def log_to_simple(x: float) -> float:
    """Convert log-return to simple return."""
    return float(np.exp(x) - 1.0)


@st.cache_resource  # Loads and caches the saved quantile model bundle (joblib file) for the selected crypto symbol.
def load_bundle(symbol: str):
    ticker = get_coin_repository().get_by_symbol(symbol).yahoo_ticker
    path = MODELS_DIR / ticker / "quantile_model_bundle.joblib"
    obj = load_quantile_model_bundle(path, symbol=symbol, ticker=ticker)
    return obj["bundle"]


@st.cache_data   # # Loads and caches the processed feature dataset for the symbol, parsing and sorting by date.
def load_features(symbol: str) -> pd.DataFrame:
    df = get_market_data_repository().read_features(symbol=symbol)
    if df.empty:
        raise FileNotFoundError(f"Features data not found for symbol={symbol.upper()}")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df

# Formats summary statistics into log returns, simple returns, or both depending on the selected output mode.
def format_summary(summary_log: dict, mode: str) -> dict:
    if mode == "log":
        return {k: float(v) for k, v in summary_log.items()}
    if mode == "simple":
        return {k: log_to_simple(float(v)) for k, v in summary_log.items()}
    # both
    out = {}
    for k, v in summary_log.items():
        out[f"{k}_log"] = float(v)
        out[f"{k}_simple"] = log_to_simple(float(v))
    return out


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Inputs")

symbol = st.sidebar.selectbox("Symbol", get_coin_repository().list_symbols())

try:
    features_df = load_features(symbol)
    bundle = load_bundle(symbol)
except Exception as e:
    st.error(str(e))
    st.stop()

available_min = features_df["date"].min().date()
available_max = features_df["date"].max().date()

st.sidebar.caption(f"Data available: {available_min} → {available_max}")

start_date = st.sidebar.date_input(
    "Start date",
    value=available_max,
    min_value=available_min,
    max_value=available_max,
)

mode = st.sidebar.radio("Horizon input type", ["horizon_days", "end_date"])

horizon_days: Optional[int] = None
end_date: Optional[str] = None

if mode == "horizon_days":
    horizon_days = st.sidebar.number_input("Horizon (trading days)", min_value=1, max_value=3000, value=10, step=1)
else:
    # allow user to choose an end date in the future (even beyond data)
    end_d = st.sidebar.date_input(
        "End date",
        value=pd.Timestamp(start_date) + pd.Timedelta(days=30),
        min_value=start_date,
    )
    end_date = str(end_d)

n_scenarios = st.sidebar.slider("Number of scenarios", min_value=500, max_value=20000, value=5000, step=500)
alpha = st.sidebar.slider("Risk level (alpha)", min_value=0.01, max_value=0.20, value=0.05, step=0.01)
seed = st.sidebar.number_input("Random seed", min_value=0, max_value=10_000_000, value=42, step=1)
return_format = st.sidebar.selectbox("Return format", ["both", "simple", "log"], index=0)


# -----------------------------
# Run button
# -----------------------------
run = st.button("Run forecast")

if run:
    with st.spinner("Running simulation..."):
        out = forecast_horizon(
            bundle=bundle,
            features_df=features_df,
            start_date=str(start_date),
            end_date=end_date,
            horizon_days=horizon_days,
            n_scenarios=int(n_scenarios),
            alpha=float(alpha),
            seed=int(seed),
        )

        summary = format_summary(out.summary, return_format)

    st.subheader("Summary metrics")
    st.json({
        "symbol": symbol,
        "start_date": str(out.start_date.date()),
        "end_date": str(out.end_date.date()),
        "horizon_days": out.horizon_days,
        "n_scenarios": out.n_scenarios,
        "alpha": out.alpha,
        "assumptions": {
            "regime_fixed": True,
            "features_constant_over_horizon": True,
        },
        "summary": summary,
    })

    # -----------------------------
    # Plot histogram (visualizes scenarios)
    # -----------------------------
    st.subheader("Scenario distribution (simulated cumulative horizon returns)")

    # Use samples in log-return space; for plotting we can show simple returns too
    samples_log = out.samples
    show_simple = st.checkbox("Plot as simple returns (%)", value=True)

    if show_simple:
        samples_plot = (np.exp(samples_log) - 1.0) * 100.0
        xlab = "Cumulative return over horizon (%)"
    else:
        samples_plot = samples_log
        xlab = "Cumulative log return over horizon"

    fig = plt.figure()
    plt.hist(samples_plot, bins=60)
    plt.xlabel(xlab)
    plt.ylabel("Frequency")
    st.pyplot(fig)

    st.caption(
        "Histogram shows the distribution of simulated horizon outcomes. "
        "VaR/CVaR describe the left tail (worst-case region)."
    )
