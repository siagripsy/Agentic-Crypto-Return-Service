from __future__ import annotations

import shutil
from pathlib import Path

from core.storage import model_artifact_store


def test_get_models_root_path_prefers_local_default_outside_cloud(monkeypatch):
    base_dir = Path("tests/.tmp/model-artifact-store/local-default")
    shutil.rmtree(base_dir, ignore_errors=True)
    local_root = base_dir / "artifacts" / "models"
    local_root.mkdir(parents=True)

    monkeypatch.setattr(model_artifact_store, "DEFAULT_LOCAL_MODELS_DIR", local_root)
    monkeypatch.delenv("MODEL_ROOT", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    resolved = model_artifact_store.get_models_root_path()

    assert resolved == local_root


def test_get_models_root_path_syncs_gcs_prefix_on_cloud(monkeypatch):
    base_dir = Path("tests/.tmp/model-artifact-store/cloud-sync")
    shutil.rmtree(base_dir, ignore_errors=True)
    cache_root = base_dir / "cache"
    monkeypatch.setattr(model_artifact_store, "DEFAULT_CACHE_ROOT", cache_root)
    monkeypatch.setattr(model_artifact_store, "DEFAULT_LOCAL_MODELS_DIR", base_dir / "local-models")
    model_artifact_store._SYNCED_TARGETS.clear()

    monkeypatch.setenv("K_SERVICE", "apcras-api")
    monkeypatch.setenv("MODEL_ROOT", "apcras-models-493310/models")

    downloads: list[Path] = []

    class FakeBlob:
        def __init__(self, name: str):
            self.name = name

        def download_to_filename(self, filename: str) -> None:
            path = Path(filename)
            path.write_text(self.name, encoding="utf-8")
            downloads.append(path)

    class FakeClient:
        def bucket(self, name: str) -> str:
            return name

        def list_blobs(self, bucket: str, prefix: str):
            assert bucket == "apcras-models-493310"
            assert prefix == "models/"
            return [
                FakeBlob("models/BTC-USD/quantile_model_bundle.joblib"),
                FakeBlob("models/BTC-USD/regime_ae.pt"),
            ]

    monkeypatch.setattr(model_artifact_store.storage, "Client", lambda: FakeClient())

    resolved = model_artifact_store.get_models_root_path()

    assert resolved == cache_root / "apcras-models-493310" / "models"
    assert (resolved / "BTC-USD" / "quantile_model_bundle.joblib").exists()
    assert (resolved / "BTC-USD" / "regime_ae.pt").exists()
    assert len(downloads) == 2
