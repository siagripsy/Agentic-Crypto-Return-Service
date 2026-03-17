from dataclasses import dataclass

@dataclass(frozen=True)
class IngestionConfig:
    interval: str = "1d"
    coingecko_default_days: str = "365"
