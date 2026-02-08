from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class IngestionConfig:
    # where the coin list lives (later we can move this to core/config/data)
    coins_metadata_path: Path = Path("data/raw/metadata/coins.json")

    # storage roots
    raw_root: Path = Path("data/raw")
    processed_root: Path = Path("data/processed")

    # data settings
    interval: str = "1d"         # daily candles
    # CoinGecko settings
    coingecko_default_days: str = "365"
