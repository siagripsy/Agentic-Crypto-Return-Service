import numpy as np
import pandas as pd

from core.features.feature_engineering import (
    RISK_ADJ_RET_CLIP,
    VOL_RATIO_CLIP,
    add_risk_adjusted_return,
    add_vol_ratio,
)


def test_risk_adjusted_return_uses_floor_and_clip():
    df = pd.DataFrame(
        {
            "log_ret_1d": [10.0, -10.0],
            "vol_30d": [0.0, 1e-12],
        }
    )
    out = add_risk_adjusted_return(df)
    assert np.isfinite(out["risk_adj_ret_1d"]).all()
    assert out["risk_adj_ret_1d"].abs().max() <= RISK_ADJ_RET_CLIP


def test_vol_ratio_uses_floor_and_clip():
    df = pd.DataFrame(
        {
            "vol_7d": [100.0, 50.0],
            "vol_30d": [0.0, 1e-12],
        }
    )
    out = add_vol_ratio(df)
    assert np.isfinite(out["vol_ratio_7d_30d"]).all()
    assert out["vol_ratio_7d_30d"].max() <= VOL_RATIO_CLIP
