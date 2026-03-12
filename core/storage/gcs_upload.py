from pathlib import Path
from google.cloud import storage


def upload_directory_to_gcs(local_dir: str, bucket_name: str, prefix: str = "") -> None:
    """
    Upload all files under local_dir to a GCS bucket, preserving relative paths.

    Example:
        local_dir = "data/raw"
        bucket_name = "probabilistic-crypto-return-data"
        prefix = "data/raw"
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    base_path = Path(local_dir)
    if not base_path.exists():
        print(f"[WARN] Local directory does not exist: {local_dir}")
        return

    for file_path in base_path.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(base_path).as_posix()
            blob_path = f"{prefix}/{relative_path}" if prefix else relative_path
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(file_path))
            print(f"[OK] Uploaded: {file_path} -> gs://{bucket_name}/{blob_path}")