from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from core.storage.database import get_engine


@dataclass(frozen=True)
class CoinRecord:
    coin_id: int
    symbol: str
    coingecko_id: str
    yahoo_ticker: str
    start_year: int


class CoinRepository:
    def __init__(self, cache_ttl_hours: int = 24) -> None:
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cache_loaded_at: datetime | None = None
        self._by_symbol: dict[str, CoinRecord] = {}
        self._by_ticker: dict[str, CoinRecord] = {}
        self._by_coingecko_id: dict[str, CoinRecord] = {}

    def refresh_cache(self, force: bool = False) -> None:
        now = datetime.utcnow()
        if (
            not force
            and self._cache_loaded_at is not None
            and now - self._cache_loaded_at < self.cache_ttl
            and self._by_symbol
        ):
            return

        query = """
            SELECT CoinID, symbol, coingecko_id, yahoo_ticker, start_year
            FROM Coins
        """
        df = pd.read_sql_query(query, get_engine())

        by_symbol: dict[str, CoinRecord] = {}
        by_ticker: dict[str, CoinRecord] = {}
        by_coingecko_id: dict[str, CoinRecord] = {}
        for row in df.to_dict(orient="records"):
            coin = CoinRecord(
                coin_id=int(row["CoinID"]),
                symbol=str(row["symbol"]).upper(),
                coingecko_id=str(row["coingecko_id"]).strip(),
                yahoo_ticker=str(row["yahoo_ticker"]).upper(),
                start_year=int(row["start_year"]),
            )
            by_symbol[coin.symbol] = coin
            by_ticker[coin.yahoo_ticker] = coin
            by_coingecko_id[coin.coingecko_id] = coin

        self._by_symbol = by_symbol
        self._by_ticker = by_ticker
        self._by_coingecko_id = by_coingecko_id
        self._cache_loaded_at = now

    def list_symbols(self) -> list[str]:
        self.refresh_cache()
        return list(self._by_symbol.keys())

    def list_yahoo_tickers(self) -> list[str]:
        self.refresh_cache()
        return list(self._by_ticker.keys())

    def get_by_symbol(self, symbol: str) -> CoinRecord:
        self.refresh_cache()
        key = symbol.upper().strip()
        if key not in self._by_symbol:
            raise KeyError(f"Unknown symbol: {symbol}")
        return self._by_symbol[key]

    def get_by_ticker(self, yahoo_ticker: str) -> CoinRecord:
        self.refresh_cache()
        key = yahoo_ticker.upper().strip()
        if key not in self._by_ticker:
            raise KeyError(f"Unknown yahoo_ticker: {yahoo_ticker}")
        return self._by_ticker[key]

    def get_by_identifier(self, *, symbol: str | None = None, yahoo_ticker: str | None = None) -> CoinRecord:
        if symbol:
            return self.get_by_symbol(symbol)
        if yahoo_ticker:
            return self.get_by_ticker(yahoo_ticker)
        raise ValueError("One of symbol or yahoo_ticker must be provided.")

    def get_symbol_to_ticker_map(self) -> dict[str, str]:
        self.refresh_cache()
        return {symbol: coin.yahoo_ticker for symbol, coin in self._by_symbol.items()}

    def get_ticker_to_symbol_map(self) -> dict[str, str]:
        self.refresh_cache()
        return {ticker: coin.symbol for ticker, coin in self._by_ticker.items()}

    def as_dataframe(self) -> pd.DataFrame:
        self.refresh_cache()
        rows: list[dict[str, Any]] = []
        for coin in self._by_symbol.values():
            rows.append(
                {
                    "CoinID": coin.coin_id,
                    "symbol": coin.symbol,
                    "coingecko_id": coin.coingecko_id,
                    "yahoo_ticker": coin.yahoo_ticker,
                    "start_year": coin.start_year,
                }
            )
        return pd.DataFrame(rows)


_COIN_REPOSITORY: CoinRepository | None = None


def get_coin_repository() -> CoinRepository:
    global _COIN_REPOSITORY
    if _COIN_REPOSITORY is None:
        _COIN_REPOSITORY = CoinRepository()
    return _COIN_REPOSITORY


def set_coin_repository(repository: CoinRepository | None) -> None:
    global _COIN_REPOSITORY
    _COIN_REPOSITORY = repository

