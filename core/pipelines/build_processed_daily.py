from core.storage.coin_repository import get_coin_repository
from core.storage.market_data_repository import get_market_data_repository


def build_one(symbol: str, yahoo_ticker: str) -> int:
    del yahoo_ticker
    return get_market_data_repository().append_missing_processed(symbol)

def build_all() -> None:
    for coin in get_coin_repository().as_dataframe().to_dict(orient="records"):
        inserted = build_one(coin["symbol"], coin["yahoo_ticker"])
        print(f"[{coin['symbol']}] processed rows inserted: {inserted}")
