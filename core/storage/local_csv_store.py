from pathlib import Path
import pandas as pd
from typing import Optional

def save_dataframe_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def raw_ohlcv_path(raw_root: Path, ticker: str) -> Path:
    safe_ticker = ticker.replace("/", "-")
    return raw_root / "ohlcv" / f"{safe_ticker}_daily.csv"

def raw_marketcap_path(raw_root: Path, symbol: str) -> Path:
    safe_symbol = symbol.replace("/", "-")
    return raw_root / "market_cap" / f"{safe_symbol}_daily.csv"



def read_last_date(path: Path, date_col: str = "date") -> Optional[str]:
    if not path.exists():
        return None

    df = pd.read_csv(path)
    if df.empty or date_col not in df.columns:
        return None

    return str(df[date_col].max())
