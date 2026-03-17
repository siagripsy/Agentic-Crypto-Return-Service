import pandas as pd

from core.storage.market_data_repository import (
    DECIMAL_28_12_MAX,
    DECIMAL_28_12_MIN,
    MarketDataRepository,
    _dedupe_by_date,
    _replace_nan_with_none,
    _sanitize_numeric_for_sql,
    _rename_db_columns,
    _rename_frame_columns,
)


def test_column_renames_match_legacy_csv_shape():
    raw = pd.DataFrame(
        {
            "price_date": ["2024-01-01"],
            "open_price": [1.0],
            "high_price": [2.0],
            "low_price": [0.5],
            "close_price": [1.5],
        }
    )
    restored = _rename_db_columns(raw)
    assert list(restored.columns) == ["date", "open", "high", "low", "close"]

    db_ready = _rename_frame_columns(restored)
    assert list(db_ready.columns) == ["price_date", "open_price", "high_price", "low_price", "close_price"]


def test_dedupe_by_date_keeps_latest_row():
    df = pd.DataFrame(
        {
            "price_date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "close_price": [10.0, 11.0, 12.0],
        }
    )
    out = _dedupe_by_date(df, "price_date")
    assert out["price_date"].tolist() == ["2024-01-01", "2024-01-02"]
    assert out["close_price"].tolist() == [11.0, 12.0]


def test_replace_nan_with_none_for_nullable_sql_columns():
    df = pd.DataFrame({"market_cap": [1.0, float("nan")]})
    out = _replace_nan_with_none(df)
    assert out["market_cap"].dtype == object
    assert out.iloc[0]["market_cap"] == 1.0
    assert out.iloc[1]["market_cap"] is None


def test_sanitize_numeric_for_sql_replaces_inf_and_clips_values():
    df = pd.DataFrame(
        {
            "a": [float("inf"), float("-inf"), 5.0],
            "b": [DECIMAL_28_12_MAX * 10, DECIMAL_28_12_MIN * 10, 1.0],
        }
    )
    out = _sanitize_numeric_for_sql(df, ["a", "b"])
    assert out.iloc[0]["a"] == DECIMAL_28_12_MAX
    assert out.iloc[1]["a"] == DECIMAL_28_12_MIN
    assert out.iloc[0]["b"] == DECIMAL_28_12_MAX
    assert out.iloc[1]["b"] == DECIMAL_28_12_MIN


class _FakeCoinRepository:
    class Coin:
        coin_id = 1
        symbol = "BTC"
        yahoo_ticker = "BTC-USD"
        coingecko_id = "bitcoin"

    def get_by_symbol(self, symbol: str):
        assert symbol == "BTC"
        return self.Coin()


class _FeatureAppendRepository(MarketDataRepository):
    def __init__(self, processed_df: pd.DataFrame) -> None:
        super().__init__(coin_repository=_FakeCoinRepository())
        self.processed_df = processed_df
        self.saved_df: pd.DataFrame | None = None

    def _read_missing_feature_dates(self, coin_id: int) -> list[str]:
        assert coin_id == 1
        return ["2024-02-10", "2024-02-11"]

    def read_processed(self, *, symbol: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
        assert symbol == "BTC"
        return self.processed_df.copy()

    def save_features(self, symbol: str, df: pd.DataFrame) -> int:
        assert symbol == "BTC"
        self.saved_df = df.copy()
        return len(df)


def test_append_missing_features_only_persists_missing_dates():
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    processed_df = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "open": range(100, 150),
            "high": range(101, 151),
            "low": range(99, 149),
            "close": range(100, 150),
            "volume": [1000.0] * 50,
            "market_cap": [100000.0] * 50,
            "ticker": ["BTC-USD"] * 50,
        }
    )
    repository = _FeatureAppendRepository(processed_df)

    inserted = repository.append_missing_features("BTC")

    assert inserted == 2
    assert repository.saved_df is not None
    assert repository.saved_df["date"].tolist() == ["2024-02-10", "2024-02-11"]
