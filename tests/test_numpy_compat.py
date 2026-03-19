import sys
from pathlib import Path

from core.numpy_compat import setup_numpy_compatibility
from core.regime_detection.historical_matching import load_regime_artifacts


def test_setup_numpy_compatibility_registers_core_aliases():
    sys.modules.pop("numpy._core", None)
    sys.modules.pop("numpy._core.multiarray", None)

    setup_numpy_compatibility()

    assert "numpy._core" in sys.modules
    assert "numpy._core.multiarray" in sys.modules


def test_load_regime_artifacts_falls_back_when_pickle_is_incompatible(monkeypatch):
    base_dir = Path("tests/.tmp/regime-artifacts/artifacts/models/BTC-USD")
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "regime_ae.pt").write_bytes(b"weights")
    (base_dir / "regime_scaler.pkl").write_bytes(b"scaler")
    (base_dir / "regime_train_config.pkl").write_bytes(b"cfg")

    def fake_pickle_loader(path):
        raise ModuleNotFoundError("No module named 'numpy._core'", name="numpy._core")

    monkeypatch.setattr(
        "core.regime_detection.historical_matching._load_pickle_with_numpy_compat",
        fake_pickle_loader,
    )

    result = load_regime_artifacts(
        ticker="BTC-USD",
        match_window_days=30,
        latent_dim=16,
        out_dir=str(base_dir.parent),
    )

    assert result is None
