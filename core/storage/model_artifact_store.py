from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Tuple

from google.cloud import storage


DEFAULT_LOCAL_MODELS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "models"
DEFAULT_CACHE_ROOT = Path("/tmp/apcras-model_cache")

_SYNC_LOCK = threading.Lock()
_SYNCED_TARGETS: set[str] = set()


def get_models_root_path() -> Path:
    model_root = os.getenv("MODEL_ROOT", "").strip()

    if not model_root:
        return DEFAULT_LOCAL_MODELS_DIR

    if _looks_like_local_path(model_root):
        return Path(model_root).expanduser().resolve()

    if not _is_running_in_cloud():
        return DEFAULT_LOCAL_MODELS_DIR

    bucket_name, prefix = _parse_gcs_model_root(model_root)
    local_root = DEFAULT_CACHE_ROOT / bucket_name / prefix
    _sync_gcs_prefix_to_local(bucket_name=bucket_name, prefix=prefix, destination=local_root)
    return local_root


def _is_running_in_cloud() -> bool:
    return bool(
        os.getenv("K_SERVICE")
        or os.getenv("K_REVISION")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    )


def _looks_like_local_path(value: str) -> bool:
    if value.startswith("gs://"):
        return False
    if value.startswith(("/", "\\", ".")):
        return True
    drive, _ = os.path.splitdrive(value)
    return bool(drive)


def _parse_gcs_model_root(value: str) -> Tuple[str, str]:
    normalized = value.strip().removeprefix("gs://").strip("/")
    if not normalized:
        raise ValueError("MODEL_ROOT is empty.")

    parts = [part for part in normalized.split("/") if part]
    if not parts:
        raise ValueError("MODEL_ROOT must include at least a bucket name.")

    bucket_name = parts[0]
    prefix = "/".join(parts[1:])
    return bucket_name, prefix


def _sync_gcs_prefix_to_local(*, bucket_name: str, prefix: str, destination: Path) -> None:
    cache_key = f"{bucket_name}/{prefix}"
    with _SYNC_LOCK:
        if cache_key in _SYNCED_TARGETS and destination.exists():
            return

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        prefix_with_slash = f"{prefix.rstrip('/')}/" if prefix else ""
        blobs = list(client.list_blobs(bucket, prefix=prefix_with_slash))

        if not blobs:
            raise FileNotFoundError(
                f"No model artifacts found in GCS at gs://{bucket_name}/{prefix_with_slash}"
            )

        downloaded_files = 0
        for blob in blobs:
            blob_name = blob.name.rstrip("/")
            if not blob_name:
                continue
            if blob_name.endswith("/"):
                continue

            relative_name = blob_name[len(prefix_with_slash):] if prefix_with_slash else blob_name
            if not relative_name:
                continue

            local_path = destination / relative_name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(local_path)
            downloaded_files += 1

        if downloaded_files == 0:
            raise FileNotFoundError(
                f"No downloadable model files found in GCS at gs://{bucket_name}/{prefix_with_slash}"
            )

        _SYNCED_TARGETS.add(cache_key)
