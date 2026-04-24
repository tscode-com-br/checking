from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .core.config import settings
from .database import Base, engine
from .routers import admin, device, health, mobile, provider, transport as transport_api, web_check
from .services.admin_auth import seed_default_admin
from .services.event_archives import ensure_event_archives_dir
from .services.forms_queue import forms_submission_worker
from .services.project_catalog import seed_default_projects


STATIC_SITE_FLAG_BY_NAME = {
    "admin": "serve_admin_site_in_api",
    "user": "serve_user_site_in_api",
    "transport": "serve_transport_site_in_api",
}


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_event_archives_dir()
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
    seed_default_projects()
    seed_default_admin()
    if settings.forms_queue_enabled:
        forms_submission_worker.start()
    try:
        yield
    finally:
        if settings.forms_queue_enabled:
            forms_submission_worker.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(tauri\.localhost|localhost(:\d+)?|127\.0\.0\.1(:\d+)?)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_session_secret,
    max_age=settings.admin_session_max_age_seconds,
    same_site="lax",
    https_only=False,
)


app.include_router(health.router)
app.include_router(device.router)
app.include_router(mobile.router)
app.include_router(provider.router)
app.include_router(web_check.router)
app.include_router(transport_api.router)
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
