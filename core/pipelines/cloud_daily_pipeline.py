import os

from core.pipelines.daily_ohlcv_pipeline import run_all as run_ohlcv
from core.pipelines.marketcap_pipeline import run_all as run_marketcap
from core.pipelines.build_processed_daily import build_all
from core.pipelines.features_pipeline import run_all as run_features
from core.storage.gcs_upload import upload_directory_to_gcs

BUCKET_NAME = "probabilistic-crypto-return-data"


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

    print("[5/6] Uploading raw data to GCS...")
    upload_directory_to_gcs("data/raw", BUCKET_NAME, prefix="data/raw")

    print("[6/6] Uploading processed data to GCS...")
    upload_directory_to_gcs("data/processed", BUCKET_NAME, prefix="data/processed")

    print("[DONE] Cloud daily pipeline completed.")


if __name__ == "__main__":
    run_all()