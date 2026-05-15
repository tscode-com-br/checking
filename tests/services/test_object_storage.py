"""Tests for Task F1 — object_storage.py service."""
from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — isolate the local-storage root per test via tmp_path
# ---------------------------------------------------------------------------


def _make_settings_patch(tmp_path: Path, remote: bool = False) -> dict:
    """Return a dict of settings overrides for the duration of a test."""
    patches = {
        "sistema.app.services.object_storage.settings": MagicMock(
            event_archives_dir=str(tmp_path),
            do_spaces_bucket="test-bucket" if remote else None,
            do_spaces_access_key="key" if remote else None,
            do_spaces_secret_key="secret" if remote else None,
            do_spaces_endpoint_url="https://ams3.digitaloceanspaces.com",
            do_spaces_region="ams3",
            do_spaces_public_base_url="https://test-bucket.ams3.cdn.digitaloceanspaces.com",
        ),
    }
    return patches


# ---------------------------------------------------------------------------
# test_upload_local_writes_file
# ---------------------------------------------------------------------------


def test_upload_local_writes_file(tmp_path):
    """upload_stream in local mode writes the content to disk."""
    from unittest.mock import patch as _patch

    with _patch(
        "sistema.app.services.object_storage.settings",
        MagicMock(
            event_archives_dir=str(tmp_path),
            do_spaces_bucket=None,
            do_spaces_access_key=None,
            do_spaces_secret_key=None,
        ),
    ):
        from sistema.app.services import object_storage as os_svc

        content = b"hello accident video"
        stream = BytesIO(content)
        os_svc.upload_stream(object_key="accidents/0001/user1/vid.mp4", stream=stream, content_type="video/mp4")

    written = tmp_path / "accidents_local_storage" / "accidents" / "0001" / "user1" / "vid.mp4"
    assert written.exists(), f"File not written: {written}"
    assert written.read_bytes() == content


# ---------------------------------------------------------------------------
# test_upload_local_returns_path_url
# ---------------------------------------------------------------------------


def test_upload_local_returns_path_url(tmp_path):
    """upload_stream in local mode returns a /api/admin/accidents/local-asset/... URL."""
    with patch(
        "sistema.app.services.object_storage.settings",
        MagicMock(
            event_archives_dir=str(tmp_path),
            do_spaces_bucket=None,
            do_spaces_access_key=None,
            do_spaces_secret_key=None,
        ),
    ):
        from sistema.app.services import object_storage as os_svc

        url = os_svc.upload_stream(
            object_key="accidents/0002/u/clip.webm",
            stream=BytesIO(b"data"),
            content_type="video/webm",
        )

    assert url == "/api/admin/accidents/local-asset/accidents/0002/u/clip.webm"


# ---------------------------------------------------------------------------
# test_delete_prefix_removes_all
# ---------------------------------------------------------------------------


def test_delete_prefix_removes_all(tmp_path):
    """delete_prefix removes the entire subtree and returns correct count."""
    # Pre-create some files under the prefix
    root = tmp_path / "accidents_local_storage" / "accidents" / "0003"
    root.mkdir(parents=True)
    (root / "user1").mkdir()
    (root / "user1" / "a.mp4").write_bytes(b"a")
    (root / "user1" / "b.mp4").write_bytes(b"b")
    (root / "c.zip").write_bytes(b"c")

    with patch(
        "sistema.app.services.object_storage.settings",
        MagicMock(
            event_archives_dir=str(tmp_path),
            do_spaces_bucket=None,
            do_spaces_access_key=None,
            do_spaces_secret_key=None,
        ),
    ):
        from sistema.app.services import object_storage as os_svc

        count = os_svc.delete_prefix(prefix="accidents/0003")

    assert count == 3
    assert not (tmp_path / "accidents_local_storage" / "accidents" / "0003").exists()


# ---------------------------------------------------------------------------
# test_stream_upload_rejects_oversized
# ---------------------------------------------------------------------------


def test_stream_upload_rejects_oversized(tmp_path):
    """stream_upload_to_storage raises HTTP 413 when content exceeds max_bytes."""
    from fastapi import HTTPException

    oversized = b"x" * (10 + 1)

    class FakeUpload:
        _data = oversized
        _pos = 0

        async def read(self, size=-1):
            if size == -1 or self._pos >= len(self._data):
                chunk = self._data[self._pos:]
            else:
                chunk = self._data[self._pos : self._pos + size]
            self._pos += len(chunk)
            return chunk

    with patch(
        "sistema.app.services.object_storage.settings",
        MagicMock(
            event_archives_dir=str(tmp_path),
            do_spaces_bucket=None,
            do_spaces_access_key=None,
            do_spaces_secret_key=None,
        ),
    ):
        from sistema.app.services import object_storage as os_svc

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                os_svc.stream_upload_to_storage(
                    object_key="accidents/0001/u/v.mp4",
                    upload_file=FakeUpload(),
                    content_type="video/mp4",
                    max_bytes=10,
                )
            )
    assert exc_info.value.status_code == 413


# ---------------------------------------------------------------------------
# test_generate_presigned_url_local_falls_back_to_path
# ---------------------------------------------------------------------------


def test_generate_presigned_url_local_falls_back_to_path(tmp_path):
    """generate_presigned_url in local mode returns the local-asset path URL."""
    with patch(
        "sistema.app.services.object_storage.settings",
        MagicMock(
            event_archives_dir=str(tmp_path),
            do_spaces_bucket=None,
            do_spaces_access_key=None,
            do_spaces_secret_key=None,
        ),
    ):
        from sistema.app.services import object_storage as os_svc

        url = os_svc.generate_presigned_url(object_key="accidents/0001/archive.zip", expires_in_seconds=300)

    assert url == "/api/admin/accidents/local-asset/accidents/0001/archive.zip"


# ---------------------------------------------------------------------------
# test_remote_mode_uses_boto3_mock
# ---------------------------------------------------------------------------


def test_remote_mode_uses_boto3_mock(tmp_path):
    """In remote mode, upload_stream delegates to boto3.client.upload_fileobj."""
    mock_client = MagicMock()
    mock_client.upload_fileobj = MagicMock()

    fake_settings = MagicMock(
        event_archives_dir=str(tmp_path),
        do_spaces_bucket="my-bucket",
        do_spaces_access_key="AKID",
        do_spaces_secret_key="SECRET",
        do_spaces_endpoint_url="https://ams3.digitaloceanspaces.com",
        do_spaces_region="ams3",
        do_spaces_public_base_url="https://my-bucket.ams3.cdn.digitaloceanspaces.com",
    )

    with (
        patch("sistema.app.services.object_storage.settings", fake_settings),
        patch("sistema.app.services.object_storage._make_boto3_client", return_value=mock_client),
    ):
        from sistema.app.services import object_storage as os_svc

        url = os_svc.upload_stream(
            object_key="accidents/0005/u/clip.mp4",
            stream=BytesIO(b"remote content"),
            content_type="video/mp4",
        )

    mock_client.upload_fileobj.assert_called_once()
    call_kwargs = mock_client.upload_fileobj.call_args
    assert call_kwargs.kwargs["Bucket"] == "my-bucket"
    assert call_kwargs.kwargs["Key"] == "accidents/0005/u/clip.mp4"
    assert "https://my-bucket.ams3.cdn.digitaloceanspaces.com/accidents/0005/u/clip.mp4" == url
