import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

def load_coins_metadata(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def extract_yahoo_tickers(coins_metadata: Any) -> List[str]:
    """
    Tries to extract Yahoo tickers from different possible JSON shapes.
    Returns a list of strings like: ["BTC-USD", "ETH-USD"]
    """
    tickers: List[str] = []

    # case 1: list of dicts
    if isinstance(coins_metadata, list):
        for item in coins_metadata:
            if isinstance(item, dict):
                # common possibilities
                for key in ["yahoo_ticker", "ticker", "symbol_yahoo", "yahoo"]:
                    if key in item and isinstance(item[key], str) and item[key].strip():
                        tickers.append(item[key].strip())
                        break

    # case 2: dict with a list under some key
    elif isinstance(coins_metadata, dict):
        for key in ["coins", "assets", "data", "list"]:
            if key in coins_metadata and isinstance(coins_metadata[key], list):
                tickers.extend(extract_yahoo_tickers(coins_metadata[key]))
                break

        # case 3: dict of coins keyed by symbol
        if not tickers:
            for _, item in coins_metadata.items():
                if isinstance(item, dict):
                    for k in ["yahoo_ticker", "ticker", "symbol_yahoo", "yahoo"]:
                        if k in item and isinstance(item[k], str) and item[k].strip():
                            tickers.append(item[k].strip())
                            break

    # de-duplicate while preserving order
    seen = set()
    unique = []
    for t in tickers:
        if t not in seen:
            unique.append(t)
            seen.add(t)
    return unique



def extract_coingecko_map(coins_metadata: Any) -> list[tuple[str, str]]:
    """
    Returns list of (symbol, coingecko_id)
    Example: [("BTC","bitcoin"), ("ETH","ethereum")]
    """
    pairs = []

    if isinstance(coins_metadata, dict) and "coins" in coins_metadata and isinstance(coins_metadata["coins"], list):
        items = coins_metadata["coins"]
    else:
        items = coins_metadata if isinstance(coins_metadata, list) else []

    for item in items:
        if isinstance(item, dict):
            sym = item.get("symbol")
            cg = item.get("coingecko_id")
            if isinstance(sym, str) and isinstance(cg, str) and sym and cg:
                pairs.append((sym.strip(), cg.strip()))

    # dedupe
    seen = set()
    out = []
    for sym, cg in pairs:
        if sym not in seen:
            out.append((sym, cg))
            seen.add(sym)
    return out


def extract_symbols(coins_metadata: Any) -> List[str]:
    """
    Extract symbols from different possible JSON shapes.
    Returns a list like: ["BTC", "ETH"]
    """
    symbols: List[str] = []

    # case 1: list of dicts
    if isinstance(coins_metadata, list):
        for item in coins_metadata:
            if isinstance(item, dict):
                sym = item.get("symbol")
                if isinstance(sym, str) and sym.strip():
                    symbols.append(sym.strip())

    # case 2: dict with a list under some key (your current coins.json is this case)
    elif isinstance(coins_metadata, dict):
        for key in ["coins", "assets", "data", "list"]:
            if key in coins_metadata and isinstance(coins_metadata[key], list):
                symbols.extend(extract_symbols(coins_metadata[key]))
                break

        # case 3: dict of coins keyed by symbol
        if not symbols:
            for k, item in coins_metadata.items():
                if isinstance(item, dict):
                    sym = item.get("symbol")
                    if isinstance(sym, str) and sym.strip():
                        symbols.append(sym.strip())
                elif isinstance(k, str) and k.strip():
                    # if it's keyed by symbol (fallback)
                    symbols.append(k.strip())

    # de-duplicate while preserving order
    seen = set()
    out = []
    for s in symbols:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out

