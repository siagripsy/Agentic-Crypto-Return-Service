from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text

from core.features.feature_engineering import build_features_basic
from core.storage.coin_repository import CoinRepository, get_coin_repository
from core.storage.database import get_engine

DECIMAL_28_12_MAX = 9999999999999999.999999999999
DECIMAL_28_12_MIN = -DECIMAL_28_12_MAX

DB_TO_FRAME_COLUMNS = {
    "price_date": "date",
    "open_price": "open",
    "high_price": "high",
    "low_price": "low",
    "close_price": "close",
}

FRAME_TO_DB_COLUMNS = {value: key for key, value in DB_TO_FRAME_COLUMNS.items()}


def _to_date_strings(values: Iterable[Any]) -> list[str]:
    series = pd.to_datetime(pd.Series(list(values)), errors="coerce").dropna()
    return series.dt.strftime("%Y-%m-%d").tolist()


def _rename_db_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns=DB_TO_FRAME_COLUMNS).copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def _rename_frame_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns=FRAME_TO_DB_COLUMNS).copy()
    if "price_date" in out.columns:
        out["price_date"] = pd.to_datetime(out["price_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def _dedupe_by_date(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col])
    out = out.sort_values(date_col).drop_duplicates(subset=[date_col], keep="last")
    out[date_col] = out[date_col].dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)


def _replace_nan_with_none(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().astype(object)
    return out.where(pd.notna(out), None)


def _sanitize_numeric_for_sql(df: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in numeric_columns:
        if col not in out.columns:
            continue
        series = pd.to_numeric(out[col], errors="coerce")
        series = series.replace(np.inf, DECIMAL_28_12_MAX)
        series = series.replace(-np.inf, DECIMAL_28_12_MIN)
        series = series.clip(lower=DECIMAL_28_12_MIN, upper=DECIMAL_28_12_MAX)
        out[col] = series
    return out


class MarketDataRepository:
    def __init__(self, coin_repository: CoinRepository | None = None) -> None:
        self.coin_repository = coin_repository or get_coin_repository()

    def get_last_ohlcv_date(self, yahoo_ticker: str) -> str | None:
        coin = self.coin_repository.get_by_ticker(yahoo_ticker)
        return self._get_last_date("ohlcv", coin.coin_id)

    def get_last_market_cap_date(self, symbol: str) -> str | None:
        coin = self.coin_repository.get_by_symbol(symbol)
        return self._get_last_date("MarketCap", coin.coin_id)

    def get_last_processed_date(self, symbol: str) -> str | None:
        coin = self.coin_repository.get_by_symbol(symbol)
        return self._get_last_date("Processed", coin.coin_id)

    def get_last_feature_date(self, symbol: str) -> str | None:
        coin = self.coin_repository.get_by_symbol(symbol)
        return self._get_last_date("Features", coin.coin_id)

    def read_ohlcv(
        self,
        *,
        symbol: str | None = None,
        yahoo_ticker: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        coin = self.coin_repository.get_by_identifier(symbol=symbol, yahoo_ticker=yahoo_ticker)
        query = """
            SELECT price_date, open_price, high_price, low_price, close_price, volume
            FROM ohlcv
            WHERE CoinID = :coin_id
              AND (:start_date IS NULL OR price_date >= :start_date)
              AND (:end_date IS NULL OR price_date <= :end_date)
            ORDER BY price_date
        """
        df = pd.read_sql_query(
            text(query),
            get_engine(),
            params={"coin_id": coin.coin_id, "start_date": start_date, "end_date": end_date},
        )
        df = _rename_db_columns(df)
        df["ticker"] = coin.yahoo_ticker
        return df

    def read_market_cap(
        self,
        *,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        coin = self.coin_repository.get_by_symbol(symbol)
        query = """
            SELECT price_date, market_cap
            FROM MarketCap
            WHERE CoinID = :coin_id
              AND (:start_date IS NULL OR price_date >= :start_date)
              AND (:end_date IS NULL OR price_date <= :end_date)
            ORDER BY price_date
        """
        df = pd.read_sql_query(
            text(query),
            get_engine(),
            params={"coin_id": coin.coin_id, "start_date": start_date, "end_date": end_date},
        )
        df = _rename_db_columns(df)
        df["coingecko_id"] = coin.coingecko_id
        df["symbol"] = coin.symbol
        return df

    def read_processed(
        self,
        *,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        coin = self.coin_repository.get_by_symbol(symbol)
        query = """
            SELECT price_date, open_price, high_price, low_price, close_price, volume, market_cap
            FROM Processed
            WHERE CoinID = :coin_id
              AND (:start_date IS NULL OR price_date >= :start_date)
              AND (:end_date IS NULL OR price_date <= :end_date)
            ORDER BY price_date
        """
        df = pd.read_sql_query(
            text(query),
            get_engine(),
            params={"coin_id": coin.coin_id, "start_date": start_date, "end_date": end_date},
        )
        df = _rename_db_columns(df)
        df["ticker"] = coin.yahoo_ticker
        return df

    def read_features(
        self,
        *,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        coin = self.coin_repository.get_by_symbol(symbol)
        query = """
            SELECT
                price_date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                market_cap,
                log_ret_1d,
                log_ret_5d,
                log_ret_10d,
                vol_7d,
                vol_30d,
                risk_adj_ret_1d,
                vol_ratio_7d_30d,
                drawdown_30d
            FROM Features
            WHERE CoinID = :coin_id
              AND (:start_date IS NULL OR price_date >= :start_date)
              AND (:end_date IS NULL OR price_date <= :end_date)
            ORDER BY price_date
        """
        df = pd.read_sql_query(
            text(query),
            get_engine(),
            params={"coin_id": coin.coin_id, "start_date": start_date, "end_date": end_date},
        )
        df = _rename_db_columns(df)
        df["ticker"] = coin.yahoo_ticker
        return df

    def save_ohlcv(self, yahoo_ticker: str, df: pd.DataFrame) -> int:
        coin = self.coin_repository.get_by_ticker(yahoo_ticker)
        prepared = self._prepare_ohlcv_frame(df, coin.coin_id)
        return self._insert_only_new(
            table_name="ohlcv",
            insert_columns=["CoinID", "price_date", "open_price", "high_price", "low_price", "close_price", "volume"],
            rows=prepared.to_dict(orient="records"),
        )

    def save_market_cap(self, symbol: str, df: pd.DataFrame) -> int:
        coin = self.coin_repository.get_by_symbol(symbol)
        prepared = self._prepare_market_cap_frame(df, coin.coin_id)
        return self._insert_only_new(
            table_name="MarketCap",
            insert_columns=["CoinID", "price_date", "market_cap"],
            rows=prepared.to_dict(orient="records"),
        )

    def save_processed(self, symbol: str, df: pd.DataFrame) -> int:
        coin = self.coin_repository.get_by_symbol(symbol)
        prepared = self._prepare_processed_frame(df, coin.coin_id)
        return self._insert_only_new(
            table_name="Processed",
            insert_columns=["CoinID", "price_date", "open_price", "high_price", "low_price", "close_price", "volume", "market_cap"],
            rows=prepared.to_dict(orient="records"),
        )

    def save_features(self, symbol: str, df: pd.DataFrame) -> int:
        coin = self.coin_repository.get_by_symbol(symbol)
        prepared = self._prepare_features_frame(df, coin.coin_id)
        return self._insert_only_new(
            table_name="Features",
            insert_columns=[
                "CoinID",
                "price_date",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
                "market_cap",
                "log_ret_1d",
                "log_ret_5d",
                "log_ret_10d",
                "vol_7d",
                "vol_30d",
                "risk_adj_ret_1d",
                "vol_ratio_7d_30d",
                "drawdown_30d",
            ],
            rows=prepared.to_dict(orient="records"),
        )

    def append_missing_processed(self, symbol: str) -> int:
        coin = self.coin_repository.get_by_symbol(symbol)
        query = """
            SELECT
                o.price_date,
                o.open_price,
                o.high_price,
                o.low_price,
                o.close_price,
                o.volume,
                m.market_cap
            FROM ohlcv AS o
            LEFT JOIN MarketCap AS m
                ON o.CoinID = m.CoinID
               AND o.price_date = m.price_date
            LEFT JOIN Processed AS p
                ON p.CoinID = o.CoinID
               AND p.price_date = o.price_date
            WHERE o.CoinID = :coin_id
              AND p.ProcessedId IS NULL
            ORDER BY o.price_date
        """
        df = pd.read_sql_query(text(query), get_engine(), params={"coin_id": coin.coin_id})
        if df.empty:
            return 0
        df = _rename_db_columns(df)
        df["ticker"] = coin.yahoo_ticker
        return self.save_processed(coin.symbol, df)

    def append_missing_features(self, symbol: str) -> int:
        coin = self.coin_repository.get_by_symbol(symbol)
        missing_dates = self._read_missing_feature_dates(coin.coin_id)
        if not missing_dates:
            return 0

        processed_df = self.read_processed(symbol=coin.symbol)
        if processed_df.empty:
            return 0

        features_df = build_features_basic(processed_df)
        features_df = features_df[features_df["date"].isin(missing_dates)].reset_index(drop=True)
        if features_df.empty:
            return 0
        return self.save_features(coin.symbol, features_df)

    def _read_missing_feature_dates(self, coin_id: int) -> list[str]:
        query = """
            SELECT p.price_date
            FROM Processed AS p
            LEFT JOIN Features AS f
                ON f.CoinID = p.CoinID
               AND f.price_date = p.price_date
            WHERE p.CoinID = :coin_id
              AND f.FeatureID IS NULL
            ORDER BY p.price_date
        """
        df = pd.read_sql_query(text(query), get_engine(), params={"coin_id": coin_id})
        if df.empty:
            return []
        return _to_date_strings(df["price_date"].tolist())

    def _get_last_date(self, table_name: str, coin_id: int) -> str | None:
        query = text(f"SELECT MAX(price_date) AS last_date FROM {table_name} WHERE CoinID = :coin_id")
        with get_engine().begin() as connection:
            row = connection.execute(query, {"coin_id": coin_id}).mappings().first()
        if not row or row["last_date"] is None:
            return None
        return pd.to_datetime(row["last_date"]).strftime("%Y-%m-%d")

    def _prepare_ohlcv_frame(self, df: pd.DataFrame, coin_id: int) -> pd.DataFrame:
        prepared = _rename_frame_columns(df)
        prepared = _dedupe_by_date(prepared, "price_date")
        prepared["CoinID"] = coin_id
        required = ["CoinID", "price_date", "open_price", "high_price", "low_price", "close_price", "volume"]
        prepared = _sanitize_numeric_for_sql(
            prepared[required],
            ["open_price", "high_price", "low_price", "close_price", "volume"],
        )
        return _replace_nan_with_none(prepared)

    def _prepare_market_cap_frame(self, df: pd.DataFrame, coin_id: int) -> pd.DataFrame:
        prepared = _rename_frame_columns(df)
        prepared = _dedupe_by_date(prepared, "price_date")
        prepared["CoinID"] = coin_id
        required = ["CoinID", "price_date", "market_cap"]
        prepared = _sanitize_numeric_for_sql(prepared[required], ["market_cap"])
        return _replace_nan_with_none(prepared)

    def _prepare_processed_frame(self, df: pd.DataFrame, coin_id: int) -> pd.DataFrame:
        prepared = _rename_frame_columns(df)
        prepared = _dedupe_by_date(prepared, "price_date")
        prepared["CoinID"] = coin_id
        required = ["CoinID", "price_date", "open_price", "high_price", "low_price", "close_price", "volume", "market_cap"]
        prepared = _sanitize_numeric_for_sql(
            prepared[required],
            ["open_price", "high_price", "low_price", "close_price", "volume", "market_cap"],
        )
        return _replace_nan_with_none(prepared)

    def _prepare_features_frame(self, df: pd.DataFrame, coin_id: int) -> pd.DataFrame:
        prepared = _rename_frame_columns(df)
        prepared = _dedupe_by_date(prepared, "price_date")
        prepared["CoinID"] = coin_id
        required = [
            "CoinID",
            "price_date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "market_cap",
            "log_ret_1d",
            "log_ret_5d",
            "log_ret_10d",
            "vol_7d",
            "vol_30d",
            "risk_adj_ret_1d",
            "vol_ratio_7d_30d",
            "drawdown_30d",
        ]
        prepared = _sanitize_numeric_for_sql(
            prepared[required],
            [
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
                "market_cap",
                "log_ret_1d",
                "log_ret_5d",
                "log_ret_10d",
                "vol_7d",
                "vol_30d",
                "risk_adj_ret_1d",
                "vol_ratio_7d_30d",
                "drawdown_30d",
            ],
        )
        return _replace_nan_with_none(prepared)

    def _insert_only_new(
        self,
        *,
        table_name: str,
        insert_columns: list[str],
        rows: list[dict[str, Any]],
    ) -> int:
        if not rows:
            return 0
        columns_sql = ", ".join(insert_columns)
        value_sql = ", ".join(f":{column}" for column in insert_columns)
        insert_sql = text(
            f"""
            INSERT INTO {table_name} ({columns_sql})
            SELECT {value_sql}
            WHERE NOT EXISTS (
                SELECT 1
                FROM {table_name}
                WHERE CoinID = :CoinID
                  AND price_date = :price_date
            )
            """
        )
        with get_engine().begin() as connection:
            result = connection.execute(insert_sql, rows)
        return int(result.rowcount or 0)


_MARKET_DATA_REPOSITORY: MarketDataRepository | None = None


def get_market_data_repository() -> MarketDataRepository:
    global _MARKET_DATA_REPOSITORY
    if _MARKET_DATA_REPOSITORY is None:
        _MARKET_DATA_REPOSITORY = MarketDataRepository()
    return _MARKET_DATA_REPOSITORY


def set_market_data_repository(repository: MarketDataRepository | None) -> None:
    global _MARKET_DATA_REPOSITORY
    _MARKET_DATA_REPOSITORY = repository
