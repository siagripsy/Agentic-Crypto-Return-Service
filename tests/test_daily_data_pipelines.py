import pandas as pd

from core.pipelines import build_processed_daily, daily_ohlcv_pipeline, features_pipeline


class _FakeMarketRepository:
    def __init__(self) -> None:
        self.saved = []
        self.processed_calls = []
        self.feature_calls = []

    def get_last_ohlcv_date(self, ticker: str) -> str | None:
        assert ticker == "BTC-USD"
        return "2024-01-02"

    def save_ohlcv(self, ticker: str, df: pd.DataFrame) -> int:
        self.saved.append((ticker, df.copy()))
        return len(df)

    def append_missing_processed(self, symbol: str) -> int:
        self.processed_calls.append(symbol)
        return 3

    def append_missing_features(self, symbol: str) -> int:
        self.feature_calls.append(symbol)
        return 2


class _FakeCoinRepository:
    def list_yahoo_tickers(self):
        return ["BTC-USD"]

    def list_symbols(self):
        return ["BTC", "ETH"]

    def as_dataframe(self):
        return pd.DataFrame(
            [
                {"symbol": "BTC", "yahoo_ticker": "BTC-USD"},
                {"symbol": "ETH", "yahoo_ticker": "ETH-USD"},
            ]
        )


def test_daily_ohlcv_pipeline_fetches_from_next_day(monkeypatch):
    repository = _FakeMarketRepository()

    def fake_fetch_daily_ohlcv(ticker: str, start: str | None = None):
        assert ticker == "BTC-USD"
        assert start == "2024-01-03"
        return pd.DataFrame(
            {
                "date": ["2024-01-03", "2024-01-04"],
                "open": [1.0, 2.0],
                "high": [1.5, 2.5],
                "low": [0.8, 1.8],
                "close": [1.2, 2.2],
                "volume": [100.0, 200.0],
                "ticker": ["BTC-USD", "BTC-USD"],
            }
        )

    monkeypatch.setattr(daily_ohlcv_pipeline, "get_market_data_repository", lambda: repository)
    monkeypatch.setattr(daily_ohlcv_pipeline, "fetch_daily_ohlcv", fake_fetch_daily_ohlcv)

    inserted = daily_ohlcv_pipeline.run_one_ticker("BTC-USD")

    assert inserted == 2
    assert repository.saved[0][0] == "BTC-USD"


def test_build_processed_daily_runs_for_all_symbols(monkeypatch):
    repository = _FakeMarketRepository()
    coin_repository = _FakeCoinRepository()

    monkeypatch.setattr(build_processed_daily, "get_market_data_repository", lambda: repository)
    monkeypatch.setattr(build_processed_daily, "get_coin_repository", lambda: coin_repository)

    build_processed_daily.build_all()

    assert repository.processed_calls == ["BTC", "ETH"]


def test_features_pipeline_runs_for_all_symbols(monkeypatch):
    repository = _FakeMarketRepository()
    coin_repository = _FakeCoinRepository()

    monkeypatch.setattr(features_pipeline, "get_market_data_repository", lambda: repository)
    monkeypatch.setattr(features_pipeline, "get_coin_repository", lambda: coin_repository)

    features_pipeline.run_all()

    assert repository.feature_calls == ["BTC", "ETH"]
