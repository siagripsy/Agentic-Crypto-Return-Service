import os

from core.pipelines.daily_ohlcv_pipeline import run_all as run_ohlcv
from core.pipelines.marketcap_pipeline import run_all as run_marketcap
from core.pipelines.build_processed_daily import build_all
from core.pipelines.features_pipeline import run_all as run_features


def run_all() -> None:
    api_key = os.getenv("COINGECKO_API_KEY")

    print("[1/6] Running OHLCV pipeline...")
    run_ohlcv()

    print("[2/6] Running market cap pipeline...")
    run_marketcap(api_key=api_key)

    print("[3/6] Building processed daily data...")
    build_all()

    print("[4/6] Running features pipeline...")
    run_features()

    print("[DONE] Cloud daily pipeline completed.")


if __name__ == "__main__":
    run_all()
