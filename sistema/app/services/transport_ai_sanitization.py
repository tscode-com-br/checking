from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from ..core.config import Settings, settings


TRANSPORT_AI_REDACTED_VALUE = "[REDACTED]"


def _sanitize_transport_ai_string_base(value: str, *, settings_obj: Settings = settings) -> str:
    sanitized = str(value or "")
    literal_secrets = (
        settings_obj.openai_api_key,
        settings_obj.here_api_key,
        settings_obj.admin_session_secret,
        settings_obj.device_shared_key,
        settings_obj.mobile_app_shared_key,
        settings_obj.provider_shared_key,
        settings_obj.bootstrap_admin_password,
        settings_obj.wifi_password,
    )
    for secret in literal_secrets:
        if secret:
            sanitized = sanitized.replace(secret, TRANSPORT_AI_REDACTED_VALUE)

    return sanitized


def _sanitize_transport_ai_string_with_extra_literals(
    value: str,
    *,
    settings_obj: Settings = settings,
    extra_literal_secrets: Iterable[str | None] = (),
) -> str:
    sanitized = _sanitize_transport_ai_string_base(value, settings_obj=settings_obj)
    for secret in extra_literal_secrets:
        normalized_secret = str(secret or "").strip()
        if normalized_secret:
            sanitized = sanitized.replace(normalized_secret, TRANSPORT_AI_REDACTED_VALUE)

    sanitized = re.sub(
        r"sk-[A-Za-z0-9_-]+",
        TRANSPORT_AI_REDACTED_VALUE,
        sanitized,
    )
    sanitized = re.sub(
        r"gAAAAA[A-Za-z0-9_-]{20,}",
        TRANSPORT_AI_REDACTED_VALUE,
        sanitized,
    )
    sanitized = re.sub(
        r"(?i)bearer\s+[A-Za-z0-9._-]+",
        f"Bearer {TRANSPORT_AI_REDACTED_VALUE}",
        sanitized,
    )
    return sanitized


def sanitize_transport_ai_string(
    value: str,
    *,
    settings_obj: Settings = settings,
    extra_literal_secrets: Iterable[str | None] = (),
) -> str:
    return _sanitize_transport_ai_string_with_extra_literals(
        value,
        settings_obj=settings_obj,
        extra_literal_secrets=extra_literal_secrets,
    )


def sanitize_transport_ai_raw_value(
    value: Any,
    *,
    settings_obj: Settings = settings,
    extra_literal_secrets: Iterable[str | None] = (),
) -> Any:
    if value is None:
        return None
    if isinstance(value, Exception):
        return {
            "type": type(value).__name__,
            "message": sanitize_transport_ai_string(
                str(value),
                settings_obj=settings_obj,
                extra_literal_secrets=extra_literal_secrets,
            ),
        }

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return sanitize_transport_ai_raw_value(
            model_dump(mode="json"),
            settings_obj=settings_obj,
            extra_literal_secrets=extra_literal_secrets,
        )

    if isinstance(value, dict):
        sanitized_dict: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key.endswith("_hint"):
                sanitized_dict[str(key)] = sanitize_transport_ai_raw_value(
                    item,
                    settings_obj=settings_obj,
                    extra_literal_secrets=extra_literal_secrets,
                )
                continue
            if any(marker in normalized_key for marker in ("api_key", "token", "secret", "password", "authorization")):
                sanitized_dict[str(key)] = TRANSPORT_AI_REDACTED_VALUE
                continue
            sanitized_dict[str(key)] = sanitize_transport_ai_raw_value(
                item,
                settings_obj=settings_obj,
                extra_literal_secrets=extra_literal_secrets,
            )
        return sanitized_dict

    if isinstance(value, (list, tuple, set)):
        return [
            sanitize_transport_ai_raw_value(
                item,
                settings_obj=settings_obj,
                extra_literal_secrets=extra_literal_secrets,
            )
            for item in value
        ]

    if isinstance(value, str):
        return sanitize_transport_ai_string(
            value,
            settings_obj=settings_obj,
            extra_literal_secrets=extra_literal_secrets,
        )

    return value