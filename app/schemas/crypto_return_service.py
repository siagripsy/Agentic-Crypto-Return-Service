from __future__ import annotations

from typing import Dict, Literal

from pydantic import BaseModel, Field, model_validator


class CryptoReturnServiceRequest(BaseModel):
    capital: float = Field(
        default=1000,
        gt=0,
        example=1000,
        description="Total capital available for investment.",
    )

    assets: Dict[str, float] = Field(
        default={
            "BTC-USD": 0.40,
            "ETH-USD": 0.35,
            "ADA-USD": 0.25,
        },
        example={"BTC-USD": 0.40, "ETH-USD": 0.35, "ADA-USD": 0.25},
        description="Mapping of yahoo_ticker to decimal portfolio weight.",
    )

    horizon_days: int = Field(default=20, gt=1, example=20)
    n_scenarios: int = Field(default=100, gt=5, example=100)
    risk_tolerance: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        example=0.10,
        description="User risk tolerance in decimal form between 0.0 and 1.0.",
    )

    include_explanation: bool = Field(
        default=True,
        description="If true, attach a combined explanation payload to the response.",
    )
    explanation_mode: Literal["fallback", "llm"] = Field(
        default="llm",
        description="Explanation mode: fallback (deterministic) or llm (if configured).",
    )

    @model_validator(mode="after")
    def validate_assets(self) -> "CryptoReturnServiceRequest":
        assets = self.assets
        if not isinstance(assets, dict) or not assets:
            raise ValueError("At least one asset weight is required.")

        total = 0.0
        normalized: Dict[str, float] = {}
        for ticker, weight in assets.items():
            key = str(ticker).strip().upper()
            if not key:
                raise ValueError("Asset ticker keys must be non-empty.")
            if float(weight) < 0:
                raise ValueError(f"Asset weight for {key} must be non-negative.")
            normalized[key] = float(weight)
            total += float(weight)

        if abs(total - 1.0) > 1e-6:
            raise ValueError("Asset weights must sum to 1.0.")

        self.assets = normalized
        return self
