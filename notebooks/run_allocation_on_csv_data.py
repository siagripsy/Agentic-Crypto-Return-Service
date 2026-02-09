import json
import sys
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.portfolio.allocation_rules import (
    AssetRiskMetrics,
    AllocationConstraints,
    RiskTolerance,
    allocate_weights,
)


def load_coin_symbols(coins_json_path: Path) -> List[str]:
    data: Any = json.loads(coins_json_path.read_text(encoding="utf-8"))

    # Your real structure:
    # {"vs_currency":"usd", "coins":[{"symbol":"BTC", ...}, ...]}
    if isinstance(data, dict) and "coins" in data and isinstance(data["coins"], list):
        out: List[str] = []
        for item in data["coins"]:
            if isinstance(item, dict):
                sym = item.get("symbol") or item.get("Symbol")
                if sym:
                    out.append(str(sym).strip().upper())
        if not out:
            raise ValueError(f"No symbols found under data['coins'] in {coins_json_path}")
        return out

    # fallback: older shapes
    if isinstance(data, list):
        if all(isinstance(x, str) for x in data):
            return [x.strip().upper() for x in data]
        if all(isinstance(x, dict) for x in data):
            out = []
            for x in data:
                sym = x.get("symbol") or x.get("Symbol")
                if sym:
                    out.append(str(sym).strip().upper())
            return out

    raise ValueError(f"Unsupported coins.json structure: {coins_json_path}")

    """
    Supports common shapes:
    1) ["BTC","ETH",...]
    2) [{"symbol":"BTC"}, {"symbol":"ETH"}, ...]
    3) {"coins":[{"symbol":"BTC"}, ...]}
    4) {"symbols":["BTC","ETH",...]}
    """
    data: Any = json.loads(coins_json_path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        if all(isinstance(x, str) for x in data):
            return [x.strip().upper() for x in data]
        if all(isinstance(x, dict) for x in data):
            out = []
            for x in data:
                sym = x.get("symbol") or x.get("Symbol")
                if sym:
                    out.append(str(sym).strip().upper())
            return out

   

    raise ValueError(f"Unsupported coins.json structure: {coins_json_path}")


def compute_metrics_from_close(symbol: str, csv_path: Path) -> AssetRiskMetrics:
    df = pd.read_csv(csv_path)

    if "close" not in df.columns:
        raise ValueError(f"{csv_path} must contain a close column")

    close = pd.to_numeric(df["close"], errors="coerce").dropna()

    # Remove non positive or obviously invalid values
    close = close[close > 0]

    if len(close) < 60:
        raise ValueError(f"Not enough valid close data in {csv_path} to compute metrics")

    rets = close.pct_change()

    # clean returns: remove inf and nan
    rets = rets.replace([float("inf"), float("-inf")], pd.NA).dropna()

    if len(rets) < 30:
        raise ValueError(f"Not enough valid returns in {csv_path} to compute metrics")

    volatility = float(rets.std())
    expected_return = float(rets.mean())

    equity = (1.0 + rets).cumprod()
    peak = equity.cummax()
    drawdown = (equity / peak) - 1.0
    max_drawdown = float(drawdown.min())

    # Hard validation: skip asset if any metric is NaN
    if not (pd.notna(volatility) and pd.notna(expected_return) and pd.notna(max_drawdown)):
        raise ValueError(
            f"NaN metrics for {symbol}: vol={volatility}, er={expected_return}, mdd={max_drawdown}"
        )

    return AssetRiskMetrics(
        symbol=symbol,
        volatility=volatility,
        max_drawdown=max_drawdown,
        expected_return=expected_return,
    )

    df = pd.read_csv(csv_path)
    if "close" not in df.columns:
        raise ValueError(f"{csv_path} must contain a close column")

    close = df["close"].astype(float).dropna()
    if len(close) < 30:
        raise ValueError(f"Not enough data in {csv_path} to compute metrics")

    rets = close.pct_change().dropna()

    volatility = float(rets.std())          # daily volatility
    expected_return = float(rets.mean())    # daily mean return

    equity = (1.0 + rets).cumprod()
    peak = equity.cummax()
    drawdown = (equity / peak) - 1.0
    max_drawdown = float(drawdown.min())    # negative

    return AssetRiskMetrics(
        symbol=symbol,
        volatility=volatility,
        max_drawdown=max_drawdown,
        expected_return=expected_return,
    )


def find_csv_for_symbol(symbol: str, daily_dir: Path) -> Path | None:
    p = daily_dir / f"{symbol}_daily.csv"
    return p if p.exists() else None

    


if __name__ == "__main__":
    # Adjust if your file name is different
    coins_json_path = PROJECT_ROOT / "data/raw/metadata/coins.json"
    
    daily_dir = PROJECT_ROOT / "data" / "processed" / "daily"

    symbols = load_coin_symbols(coins_json_path)

    assets: List[AssetRiskMetrics] = []
    skipped: Dict[str, str] = {}

    for sym in symbols:
        csv_path = find_csv_for_symbol(sym, daily_dir)
        if csv_path is None:
            skipped[sym] = "CSV not found"
            continue

        try:
            assets.append(compute_metrics_from_close(sym, csv_path))
        except Exception as e:
            skipped[sym] = f"metrics error: {e}"

    if not assets:
        raise RuntimeError("No valid assets found. Check coins.json and daily CSV files.")

    constraints = AllocationConstraints(
        max_positions=None,
        max_weight_per_asset=0.60,
        min_weight_per_asset=0.00,
    )

    print(f"Loaded symbols: {symbols}")
    print(f"Usable assets: {[a.symbol for a in assets]}")
    if skipped:
        print("\nSkipped:")
        for k in sorted(skipped.keys()):
            print(f"  {k}: {skipped[k]}")

    for tol in [RiskTolerance.CONSERVATIVE, RiskTolerance.MODERATE, RiskTolerance.AGGRESSIVE]:
        w = allocate_weights(tol, assets, constraints=constraints)
        print(f"\nRiskTolerance = {tol.value}")
        for k, v in w.items():
            print(f"  {k}: {v:.6f}")
        print(f"  SUM: {sum(w.values()):.6f}")
