"""
Baseline probabilistic scenario engine.

W5 deliverable:
- Load historical OHLCV
- Compute returns
- Fit baseline distribution
- Run Monte Carlo simulations
"""

from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class ScenarioConfig:
    asset: str
    horizon_days: int
    n_scenarios: int = 10_000


class ScenarioEngine:

    def __init__(self, price_df: pd.DataFrame):
        """
        price_df must contain:
        - date
        - close
        """
        self.price_df = price_df.copy()

    def compute_returns(self) -> pd.Series:
        raise NotImplementedError

    def fit_distribution(self, returns: pd.Series):
        raise NotImplementedError

    def simulate_paths(self, params):
        raise NotImplementedError

    def run(self, config: ScenarioConfig) -> dict:
        raise NotImplementedError
