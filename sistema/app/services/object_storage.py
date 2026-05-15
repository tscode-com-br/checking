"""Object storage service — DigitalOcean Spaces (S3-compatible) with local-disk fallback.

In development (no DO_SPACES_BUCKET env var), files are written under
`{event_archives_dir}/accidents_local_storage/` and URLs are served by the
local-asset endpoint in admin.py.

In production, boto3 uploads/downloads to Spaces.
"""

from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from typing import IO

from fastapi import HTTPException

from ..core.config import settings


class ObjectStorageError(RuntimeError):
    pass


def _use_remote() -> bool:
    return bool(
        settings.do_spaces_bucket
        and settings.do_spaces_access_key
        and settings.do_spaces_secret_key
    )


def _local_root() -> Path:
    root = Path(settings.event_archives_dir) / "accidents_local_storage"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_boto3_client():
    import boto3  # lazy import — not installed in all envs

    return boto3.client(
        "s3",
        endpoint_url=settings.do_spaces_endpoint_url,
        region_name=settings.do_spaces_region,
        aws_access_key_id=settings.do_spaces_access_key,
        aws_secret_access_key=settings.do_spaces_secret_key,
    )


def upload_stream(
    *,
    object_key: str,
    stream: IO[bytes],
    content_type: str,
    cache_control: str = "private, max-age=0",
) -> str:
    """Upload a binary stream. Returns the public URL."""
    if _use_remote():
        client = _make_boto3_client()
        client.upload_fileobj(
            Fileobj=stream,
            Bucket=settings.do_spaces_bucket,
            Key=object_key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": cache_control,
                "ACL": "private",
            },
        )
        base = (settings.do_spaces_public_base_url or settings.do_spaces_endpoint_url or "").rstrip("/")
        return f"{base}/{object_key}"

    # Local fallback
    target = _local_root() / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as f:
        shutil.copyfileobj(stream, f)
    return f"/api/admin/accidents/local-asset/{object_key}"


def generate_presigned_url(*, object_key: str, expires_in_seconds: int = 300) -> str:
    """Return a time-limited URL for the given object key."""
    if _use_remote():
        client = _make_boto3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.do_spaces_bucket, "Key": object_key},
            ExpiresIn=expires_in_seconds,
        )
    return f"/api/admin/accidents/local-asset/{object_key}"


def delete_object(*, object_key: str) -> None:
    """Delete a single object by key."""
    if _use_remote():
        client = _make_boto3_client()
        client.delete_object(Bucket=settings.do_spaces_bucket, Key=object_key)
        return
    target = _local_root() / object_key
    if target.exists():
        target.unlink()


def delete_prefix(*, prefix: str) -> int:
    """Delete all objects whose key starts with *prefix*. Returns count deleted."""
    if _use_remote():
        client = _make_boto3_client()
        deleted = 0
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.do_spaces_bucket, Prefix=prefix):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if not objects:
                continue
            client.delete_objects(
                Bucket=settings.do_spaces_bucket,
                Delete={"Objects": objects},
            )
            deleted += len(objects)
        return deleted

    root = _local_root() / prefix
    if not root.exists():
        return 0
    count = sum(1 for p in root.rglob("*") if p.is_file())
    shutil.rmtree(root, ignore_errors=True)
    return count


async def stream_upload_to_storage(
    *,
    object_key: str,
    upload_file,
    content_type: str,
    max_bytes: int,
) -> tuple[int, str]:
    """Read an UploadFile in chunks (up to max_bytes), upload, and return (size, public_url).

    Raises HTTP 413 if the file exceeds max_bytes.
    """
    buffer = BytesIO()
    total = 0
    chunk_size = 1024 * 1024  # 1 MB

    while True:
        chunk = await upload_file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail="Video maior que o limite permitido.",
            )
        buffer.write(chunk)

    buffer.seek(0)
    public_url = upload_stream(
        object_key=object_key,
        stream=buffer,
        content_type=content_type,
    )
    return total, public_url
