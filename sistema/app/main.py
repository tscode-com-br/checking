import json
import logging
import time
from contextlib import asynccontextmanager
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.sessions import SessionMiddleware

from .core.config import settings
from .database import Base, engine, reset_database_request_context, set_database_request_context
from .routers import admin, device, health, mobile, provider, transport as transport_api, transport_ai as transport_ai_api, web_check
from .services.admin_auth import seed_default_admin
from .services.admin_updates import start_realtime_brokers, stop_realtime_brokers
from .services.event_archives import ensure_event_archives_dir
from .services.project_catalog import seed_default_projects
from .services.transport_ai_llm_settings import get_transport_ai_here_api_key_decrypted
from .services.transport_ai_sanitization import sanitize_transport_ai_raw_value


STATIC_SITE_FLAG_BY_NAME = {
    "admin": "serve_admin_site_in_api",
    "user": "serve_user_site_in_api",
    "transport": "serve_transport_site_in_api",
}
REQUEST_ID_HEADER_NAME = "X-Request-ID"
HTTP_REQUEST_LOGGER = logging.getLogger("checking.http")
ADMIN_SESSION_KEY = "admin_user_id"
TRANSPORT_SESSION_KEY = "transport_user_id"
WEB_USER_SESSION_KEY = "web_user_chave"
CRITICAL_ROUTE_PATHS = frozenset(
    {
        "/api/health",
        "/api/health/live",
        "/api/health/ready",
        "/api/web/check/state",
        "/api/mobile/state",
        "/api/admin/stream",
        "/api/admin/checkin",
        "/api/admin/checkout",
        "/api/admin/projects",
    }
)
CLIENT_SURFACE_BY_PREFIX = (
    ("/api/transport/ai", "transport_ai"),
    ("/api/transport", "transport"),
    ("/api/admin", "admin"),
    ("/api/web", "web_check"),
    ("/api/mobile", "mobile"),
    ("/api/provider", "provider"),
    ("/api/device", "device"),
    ("/admin", "admin_static"),
    ("/user", "user_static"),
    ("/transport", "transport_static"),
    ("/assets", "assets"),
)
SESSION_AUTH_BY_PREFIX = (
    ("/api/admin", ADMIN_SESSION_KEY, "admin_session"),
    ("/api/transport", TRANSPORT_SESSION_KEY, "transport_session"),
    ("/api/web", WEB_USER_SESSION_KEY, "web_session"),
)
HEADER_AUTH_BY_PREFIX = (
    ("/api/mobile", "x-mobile-shared-key", "mobile_shared_key"),
    ("/api/provider", "x-provider-shared-key", "provider_shared_key"),
)
DEVICE_BODY_SHARED_KEY_PATHS = frozenset({"/api/device/heartbeat", "/api/scan"})


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _normalize_request_id(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    return normalized[:80]


def _get_request_session(request: Request) -> Mapping[str, object] | None:
    session = request.scope.get("session")
    if isinstance(session, Mapping):
        return session
    return None


def _infer_client_surface(path: str) -> str:
    if _path_matches_prefix(path, "/api/health"):
        return "health"
    if path == "/api/scan":
        return "device"
    for prefix, surface_name in CLIENT_SURFACE_BY_PREFIX:
        if _path_matches_prefix(path, prefix):
            return surface_name
    return "unknown"


def _infer_authenticated_kind(request: Request, path: str) -> str | None:
    session = _get_request_session(request)
    for prefix, session_key, authenticated_kind in SESSION_AUTH_BY_PREFIX:
        if _path_matches_prefix(path, prefix):
            if session and session.get(session_key) not in (None, ""):
                return authenticated_kind
            return "anonymous"

    for prefix, header_name, authenticated_kind in HEADER_AUTH_BY_PREFIX:
        if _path_matches_prefix(path, prefix):
            return authenticated_kind if request.headers.get(header_name) else "anonymous"

    if path in DEVICE_BODY_SHARED_KEY_PATHS:
        return None

    return None


def _is_critical_route(path: str) -> bool:
    return path in CRITICAL_ROUTE_PATHS


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        request_id = _normalize_request_id(request.headers.get(REQUEST_ID_HEADER_NAME)) or uuid4().hex
        client_surface = _infer_client_surface(path)
        database_request_context = set_database_request_context(request_id=request_id, path=path)
        request.state.request_id = request_id
        request.state.client_surface = client_surface
        request.state.is_critical_route = _is_critical_route(path)

        start_time = time.perf_counter()
        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            reset_database_request_context(database_request_context)
            if response is not None:
                response.headers.setdefault(REQUEST_ID_HEADER_NAME, request_id)
                request_id = response.headers[REQUEST_ID_HEADER_NAME]

            HTTP_REQUEST_LOGGER.info(
                json.dumps(
                    {
                        "authenticated_kind": _infer_authenticated_kind(request, path),
                        "client_surface": client_surface,
                        "event": "http_request",
                        "is_critical_route": _is_critical_route(path),
                        "latency_ms": int(round((time.perf_counter() - start_time) * 1000)),
                        "method": request.method,
                        "path": path,
                        "request_id": request_id,
                        "status_code": status_code,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )


def should_serve_static_site(site_name: str, *, settings_obj=settings) -> bool:
    flag_name = STATIC_SITE_FLAG_BY_NAME.get(site_name)
    if flag_name is None:
        raise ValueError(f"Unknown static site: {site_name}")
    return bool(getattr(settings_obj, flag_name, True))


def build_static_index_handler(directory: Path):
    def handler() -> FileResponse:
        return FileResponse(directory / "index.html")

    return handler


def build_static_trailing_slash_handler(route_path: str):
    def handler() -> RedirectResponse:
        return RedirectResponse(url=f"..{route_path}", status_code=307)

    return handler


def mount_static_site(app: FastAPI, *, site_name: str, route_path: str, directory: Path) -> None:
    if not directory.exists() or not should_serve_static_site(site_name):
        return

    app.add_api_route(
        route_path,
        build_static_index_handler(directory),
        methods=["GET"],
        include_in_schema=False,
    )
    app.add_api_route(
        f"{route_path}/",
        build_static_trailing_slash_handler(route_path),
        methods=["GET"],
        include_in_schema=False,
    )
    app.mount(route_path, StaticFiles(directory=directory), name=site_name)


_STARTUP_LOGGER = logging.getLogger("checking.startup")


def _load_here_api_key_from_db() -> None:
    from .database import SessionLocal
    try:
        with SessionLocal() as db:
            here_api_key = get_transport_ai_here_api_key_decrypted(db)
            if here_api_key:
                settings.here_api_key = here_api_key
    except Exception:
        _STARTUP_LOGGER.warning("Failed to load HERE API key from database at startup.", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_event_archives_dir()
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
    seed_default_projects()
    seed_default_admin()
    _load_here_api_key_from_db()
    start_realtime_brokers()
    try:
        yield
    finally:
        stop_realtime_brokers()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(tauri\.localhost|localhost(:\d+)?|127\.0\.0\.1(:\d+)?)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_session_secret,
    max_age=settings.admin_session_max_age_seconds,
    same_site="lax",
    https_only=False,
)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    if str(request.url.path or "").strip() == "/api/transport/ai/settings":
        return JSONResponse(
            status_code=422,
            content={
                "detail": sanitize_transport_ai_raw_value(exc.errors()),
            },
        )
    return await request_validation_exception_handler(request, exc)


app.include_router(health.router)
app.include_router(device.router)
app.include_router(mobile.router)
app.include_router(provider.router)
app.include_router(web_check.router)
app.include_router(transport_api.router)
app.include_router(transport_ai_api.router)
app.include_router(admin.router)

static_dir = Path(__file__).resolve().parent / "static"
assets_dir = Path(__file__).resolve().parents[2] / "assets"
if static_dir.exists():
    admin_dir = static_dir / "admin"
    check_dir = static_dir / "check"
    transport_dir = static_dir / "transport"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    mount_static_site(app, site_name="admin", route_path="/admin", directory=admin_dir)
    mount_static_site(app, site_name="user", route_path="/user", directory=check_dir)
    mount_static_site(app, site_name="transport", route_path="/transport", directory=transport_dir)
