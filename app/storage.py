import os
import re
import uuid
from pathlib import PurePath

MAX_UPLOAD_BYTES = int(os.getenv("UPLOADS_MAX_BYTES", str(512 * 1024)))
ALLOWED_SUFFIXES = {".log", ".txt", ".json", ".out", ".err", ""}


def uploads_s3_bucket() -> str | None:
    value = os.getenv("UPLOADS_S3_BUCKET", "").strip()
    return value or None


def uploads_local_dir() -> str:
    return os.getenv("UPLOADS_LOCAL_DIR", "/tmp/debugpilot-uploads")


def storage_backend() -> str:
    if uploads_s3_bucket():
        return "s3"
    return "local"


def sanitize_filename(name: str) -> str:
    base = PurePath(name).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return cleaned[:200] or "upload.log"


def validate_upload(filename: str, size: int) -> None:
    if size <= 0:
        raise ValueError("Empty file")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(f"File too large (max {MAX_UPLOAD_BYTES // 1024} KB)")
    suffix = PurePath(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Allowed types: .log, .txt, .json, .out, .err")


def build_storage_key(user_id: int, filename: str) -> str:
    safe = sanitize_filename(filename)
    return f"users/{user_id}/{uuid.uuid4().hex}/{safe}"


def put_object(key: str, data: bytes, content_type: str) -> None:
    bucket = uploads_s3_bucket()
    if bucket:
        import boto3

        region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        client = boto3.client("s3", region_name=region)
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type or "text/plain",
        )
        return

    path = os.path.join(uploads_local_dir(), key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def get_object_bytes(key: str) -> bytes:
    bucket = uploads_s3_bucket()
    if bucket:
        import boto3

        region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        client = boto3.client("s3", region_name=region)
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    path = os.path.join(uploads_local_dir(), key)
    with open(path, "rb") as handle:
        return handle.read()


def decode_log_bytes(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    return text.strip()
