from pydantic import BaseModel, Field
from typing import Dict


class CryptoReturnServiceRequest(BaseModel):

    capital: float = Field(
        default=1000,
        example=1000,
        description="Total capital available for investment"
    )

    assets: Dict[str, float] = Field(
        default={
            "BTC-USD": 0.40,
            "ETH-USD": 0.35,
            "ADA-USD": 0.25
        },
        example={
            "BTC-USD": 0.40,
            "ETH-USD": 0.35,
            "ADA-USD": 0.25
        }
    )

    horizon_days: int = Field(
        default=20,
        example=20
    )

    n_scenarios: int = Field(
        default=100,
        example=100
    )

    risk_tolerance: float = Field(
        default=0.10,
        example=0.10
    )