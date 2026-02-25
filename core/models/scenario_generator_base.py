from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass
class ScenarioResult:
    """
    Standard output of any scenario generator.
    scenarios: price paths with shape (n_scenarios, horizon_days + 1)
    metadata: optional diagnostics (params, seed, etc.)
    """
    scenarios: np.ndarray
    metadata: Dict[str, Any]


class BaseScenarioGenerator:
    """
    All scenario generators must implement generate().
    """

    def generate(
        self,
        price_df,
        *,
        horizon_days: int,
        n_scenarios: int,
        seed: int = 42,
        **kwargs,
    ) -> ScenarioResult:
        raise NotImplementedError