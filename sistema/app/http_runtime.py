import os
import sys

from .core.config import settings


def _get_positive_integer_env(name: str, default: int) -> str:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer value for {name}: {raw_value}") from exc

    if parsed <= 0:
        raise RuntimeError(f"{name} must be greater than zero")

    return str(parsed)


def build_http_server_command() -> list[str]:
    app_host = os.getenv("APP_HOST", settings.app_host).strip() or settings.app_host
    app_port = _get_positive_integer_env("APP_PORT", settings.app_port)

    return [
        sys.executable,
        "-m",
        "gunicorn.app.wsgiapp",
        "sistema.app.main:app",
        "--worker-class",
        "uvicorn.workers.UvicornWorker",
        "--workers",
        _get_positive_integer_env("APP_WORKERS", 1),
        "--bind",
        f"{app_host}:{app_port}",
        "--keep-alive",
        _get_positive_integer_env("APP_KEEPALIVE_SECONDS", 5),
        "--timeout",
        _get_positive_integer_env("APP_TIMEOUT_SECONDS", 90),
        "--graceful-timeout",
        _get_positive_integer_env("APP_GRACEFUL_TIMEOUT_SECONDS", 30),
        "--max-requests",
        _get_positive_integer_env("APP_MAX_REQUESTS", 1000),
        "--max-requests-jitter",
        _get_positive_integer_env("APP_MAX_REQUESTS_JITTER", 100),
    ]


def main() -> None:
    command = build_http_server_command()
    os.execv(command[0], command)


if __name__ == "__main__":
    main()