import os
import pickle
import warnings
from typing import Tuple, List, Optional, Dict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from core.models.regime_autoencoder import RegimeAutoencoder
from core.numpy_compat import setup_numpy_compatibility


FEATURE_COLUMNS = [
    "log_ret_1d",
    "log_ret_5d",
    "log_ret_10d",
    "vol_7d",
    "vol_30d",
    "risk_adj_ret_1d",
    "vol_ratio_7d_30d",
    "drawdown_30d",
]


DEFAULT_ARTIFACTS_DIR = str(Path(__file__).resolve().parents[2] / "artifacts" / "models")


def _load_pickle_with_numpy_compat(path: str):
    """
    Load a pickle after installing NumPy compatibility aliases.

    Some artifacts were produced in environments whose private NumPy module
    paths differ from the deployment runtime. We retry once after reapplying
    compatibility shims so the API can continue using existing artifacts.
    """
    setup_numpy_compatibility()

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except ModuleNotFoundError as exc:
        if getattr(exc, "name", "") and not str(exc.name).startswith("numpy"):
            raise
        setup_numpy_compatibility()
        with open(path, "rb") as f:
            return pickle.load(f)


# ----------------------------------------------------------------------
# Data prep
# ----------------------------------------------------------------------

def load_feature_data(data: pd.DataFrame | str) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        df = pd.read_csv(data)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def scale_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, StandardScaler]:
    scaler = StandardScaler()
    df_scaled = df.copy()
    df_scaled[FEATURE_COLUMNS] = scaler.fit_transform(df[FEATURE_COLUMNS])
    return df_scaled, scaler


def apply_scaler(df: pd.DataFrame, scaler: StandardScaler) -> pd.DataFrame:
    df_scaled = df.copy()
    df_scaled[FEATURE_COLUMNS] = scaler.transform(df_scaled[FEATURE_COLUMNS])
    return df_scaled


def build_rolling_windows(
    df_scaled: pd.DataFrame,
    match_window_days: int,
) -> Tuple[np.ndarray, List[int]]:
    """
    Returns:
      windows: (N, W, F)
      window_end_indices: list of end_idx for each window (end_idx is exclusive, last element is end_idx-1)
    """
    W = match_window_days

    feature_matrix = df_scaled[FEATURE_COLUMNS].values
    n_samples = feature_matrix.shape[0]

    windows: List[np.ndarray] = []
    window_end_indices: List[int] = []

    for end_idx in range(W, n_samples):
        start_idx = end_idx - W
        window = feature_matrix[start_idx:end_idx]

        if np.isnan(window).any():
            continue

        windows.append(window)
        window_end_indices.append(end_idx)

    return np.array(windows), window_end_indices


# ----------------------------------------------------------------------
# Autoencoder training / embeddings
# ----------------------------------------------------------------------

def train_autoencoder(
    windows: np.ndarray,
    latent_dim: int = 16,
    epochs: int = 40,
    batch_size: int = 64,
    lr: float = 1e-3,
    seed: int = 42,
) -> Tuple[torch.nn.Module, np.ndarray]:
    """
    windows: shape (N, W, F) scaled windows
    returns: trained model, embeddings (N, latent_dim)
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    device = torch.device("cpu")

    N, W, F = windows.shape
    X = windows.reshape(N, W * F).astype(np.float32)

    X_tensor = torch.from_numpy(X)
    ds = TensorDataset(X_tensor)
    dl = DataLoader(ds, batch_size=batch_size, shuffle=True, drop_last=False)

    model = RegimeAutoencoder(input_dim=W * F, latent_dim=latent_dim).to(device)
    optim = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = torch.nn.MSELoss()

    model.train()
    for epoch in range(epochs):
        total = 0.0
        count = 0

        for (xb,) in dl:
            xb = xb.to(device)
            recon = model(xb)
            loss = loss_fn(recon, xb)

            optim.zero_grad()
            loss.backward()
            optim.step()

            total += loss.item() * xb.size(0)
            count += xb.size(0)

        avg = total / max(count, 1)
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"[AE] epoch {epoch+1}/{epochs} loss={avg:.6f}")

    model.eval()
    with torch.no_grad():
        Z = model.encode(X_tensor.to(device)).cpu().numpy()

    return model, Z


def compute_embeddings(model: torch.nn.Module, windows: np.ndarray) -> np.ndarray:
    """
    Compute embeddings for all windows using an already-loaded model.
    """
    N, W, F = windows.shape
    X = windows.reshape(N, W * F).astype(np.float32)

    model.eval()
    with torch.no_grad():
        Z = model.encode(torch.from_numpy(X)).cpu().numpy()

    return Z


# ----------------------------------------------------------------------
# Artifacts (model/scaler/train_config)
# ----------------------------------------------------------------------

def save_regime_artifacts(
    ticker: str,
    model: torch.nn.Module,
    scaler: StandardScaler,
    train_config: Dict,
    out_dir: str = DEFAULT_ARTIFACTS_DIR,
) -> Tuple[str, str, str]:
    """
    Saves regime artifacts under:
      artifacts/models/<ticker>/
        - regime_ae.pt
        - regime_scaler.pkl
        - regime_train_config.pkl
    """
    coin_dir = os.path.join(out_dir, ticker)
    os.makedirs(coin_dir, exist_ok=True)

    model_path = os.path.join(coin_dir, "regime_ae.pt")
    scaler_path = os.path.join(coin_dir, "regime_scaler.pkl")
    cfg_path = os.path.join(coin_dir, "regime_train_config.pkl")

    torch.save(model.state_dict(), model_path)

    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    with open(cfg_path, "wb") as f:
        pickle.dump(train_config, f)

    return model_path, scaler_path, cfg_path


def load_regime_artifacts(
    ticker: str,
    match_window_days: int,
    latent_dim: int = 16,
    out_dir: str = DEFAULT_ARTIFACTS_DIR,
) -> Optional[Dict]:
    """
    Loads:
      - model weights
      - scaler
      - saved train config dict
    """
    coin_dir = os.path.join(out_dir, ticker)
    model_path = os.path.join(coin_dir, "regime_ae.pt")
    scaler_path = os.path.join(coin_dir, "regime_scaler.pkl")
    cfg_path = os.path.join(coin_dir, "regime_train_config.pkl")

    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(cfg_path)):
        return None

    try:
        scaler = _load_pickle_with_numpy_compat(scaler_path)
        saved_train_cfg = _load_pickle_with_numpy_compat(cfg_path)
    except Exception as exc:
        warnings.warn(
            (
                f"Failed to load cached regime artifacts for {ticker}; "
                f"falling back to retraining. Original error: {exc}"
            ),
            RuntimeWarning,
            stacklevel=2,
        )
        return None

    input_dim = match_window_days * len(FEATURE_COLUMNS)
    model = RegimeAutoencoder(input_dim=input_dim, latent_dim=latent_dim)
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()

    return {"model": model, "scaler": scaler, "train_config": saved_train_cfg}


# ----------------------------------------------------------------------
# Similarity search (top-n)
# ----------------------------------------------------------------------

def find_top_n_similar_windows(
    embeddings: np.ndarray,
    window_end_indices: List[int],
    top_n: int,
    similarity_metric: str = "cosine",
    embargo_days: int = 5,
) -> List[dict]:
    """
    Find top_n most similar historical windows to the CURRENT window (last one),
    using distances in the autoencoder latent space.
    - similarity_metric: 'cosine' or 'euclidean'
    """
    if top_n <= 0:
        raise ValueError("top_n must be > 0")

    current_idx = embeddings.shape[0] - 1
    current_vec = embeddings[current_idx].reshape(1, -1)

    # exclude last embargo windows (and itself) to avoid near-duplicates
    max_candidate = max(0, embeddings.shape[0] - 1 - embargo_days)
    candidate_embeddings = embeddings[:max_candidate]
    candidate_end_indices = window_end_indices[:max_candidate]

    if candidate_embeddings.shape[0] < top_n:
        raise ValueError("Not enough historical windows to select top_n. Reduce top_n or embargo_days.")

    metric = "cosine" if similarity_metric == "cosine" else "euclidean"

    nn = NearestNeighbors(n_neighbors=top_n, metric=metric)
    nn.fit(candidate_embeddings)

    distances, indices = nn.kneighbors(current_vec, return_distance=True)

    top_matches = []
    for rank, (i, d) in enumerate(zip(indices[0], distances[0]), start=1):
        top_matches.append(
            {
                "rank": rank,
                "candidate_window_idx": int(i),
                "window_end_index": int(candidate_end_indices[i]),
                "distance": float(d),
                # convenience: convert cosine distance to similarity in [0,1] when using cosine
                "similarity": float(1.0 - d) if metric == "cosine" else None,
            }
        )

    return top_matches


# ----------------------------------------------------------------------
# Outcome evaluation (depends on horizon_days, not on the model)
# ----------------------------------------------------------------------

def _max_drawdown(prices: np.ndarray) -> float:
    peak = prices[0]
    mdd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (p / peak) - 1.0
        if dd < mdd:
            mdd = dd
    return float(mdd)


def evaluate_forward_outcomes(
    df_raw: pd.DataFrame,
    matches: List[dict],
    match_window_days: int,
    horizon_days: int,
) -> List[dict]:
    """
    For each matched window, compute forward profit% and max drawdown% over horizon_days.
    Uses df_raw['close'] and df_raw['date'].
    """
    H = horizon_days
    closes = df_raw["close"].values
    n = len(closes)

    evaluated = []
    for m in matches:
        end_idx = int(m["window_end_index"])      # exclusive end index from window builder
        last_in_window = end_idx - 1              # inclusive last index in the window

        start_forward = end_idx
        end_forward = end_idx + H                 # exclusive

        # need full horizon
        if end_forward >= n:
            continue

        start_price = closes[last_in_window]
        horizon_prices = closes[start_forward:end_forward]
        end_price = horizon_prices[-1]

        profit_pct = (end_price / start_price) - 1.0
        mdd = _max_drawdown(horizon_prices)

        out = dict(m)
        out.update(
            {
                "window_start_index": end_idx - match_window_days,
                "window_end_index_inclusive": last_in_window,
                "window_start_date": str(df_raw.loc[end_idx - match_window_days, "date"]),
                "window_end_date": str(df_raw.loc[last_in_window, "date"]),
                "forward_end_index": end_forward - 1,
                "forward_end_date": str(df_raw.loc[end_forward - 1, "date"]),
                "horizon_days": int(horizon_days),
                "profit_pct": float(profit_pct),
                "max_drawdown_pct": float(mdd),
            }
        )
        evaluated.append(out)

    return evaluated


def summarize_outcomes(evaluated: List[dict]) -> dict:
    profits = [e["profit_pct"] for e in evaluated if e["profit_pct"] > 0]
    losses = [e["profit_pct"] for e in evaluated if e["profit_pct"] <= 0]
    mdds = [e["max_drawdown_pct"] for e in evaluated]

    total = len(evaluated)
    prob_profit = (len(profits) / total) if total > 0 else 0.0

    return {
        "n_evaluated": total,
        "prob_profit": prob_profit,
        "profit_analysis": {
            "count": len(profits),
            "mean_profit": float(np.mean(profits)) if profits else None,
            "max_profit": float(np.max(profits)) if profits else None,
            "min_profit": float(np.min(profits)) if profits else None,
        },
        "loss_analysis": {
            "count": len(losses),
            "mean_loss": float(np.mean(losses)) if losses else None,
            "worst_loss": float(np.min(losses)) if losses else None,
            "smallest_loss": float(np.max(losses)) if losses else None,
        },
        "drawdown_analysis": {
            "mean_max_drawdown": float(np.mean(mdds)) if mdds else None,
            "worst_max_drawdown": float(np.min(mdds)) if mdds else None,
        },
    }
