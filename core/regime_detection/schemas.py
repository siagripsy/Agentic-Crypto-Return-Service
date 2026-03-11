from dataclasses import dataclass
from typing import Literal

SimilarityMetric = Literal["cosine", "euclidean"]


@dataclass(frozen=True)
class RegimeTrainConfig:
    # affects window construction and model input_dim
    match_window_days: int = 30

    # affects similarity search space
    similarity_metric: SimilarityMetric = "cosine"

    # exclude last N windows from candidate pool to avoid near-duplicates
    embargo_days: int = 5


@dataclass(frozen=True)
class RegimeQueryConfig:
    # number of similar windows to return
    top_n: int = 10

    # horizon to evaluate outcomes (user input)
    horizon_days: int = 20