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


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_event_archives_dir()
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
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
    gerencia_dir = static_dir / "gerencia"
    transport_dir = static_dir / "transport"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if admin_dir.exists():
        @app.get("/admin", include_in_schema=False)
        def admin_page() -> FileResponse:
            return FileResponse(admin_dir / "index.html")

        @app.get("/admin/", include_in_schema=False)
        def admin_page_trailing_slash() -> RedirectResponse:
            return RedirectResponse(url="../admin", status_code=307)

        app.mount("/admin", StaticFiles(directory=admin_dir), name="admin")

    if gerencia_dir.exists():
        @app.get("/gerencia", include_in_schema=False)
        def gerencia_page() -> FileResponse:
            return FileResponse(gerencia_dir / "index.html")

        @app.get("/gerencia/", include_in_schema=False)
        def gerencia_page_trailing_slash() -> RedirectResponse:
            return RedirectResponse(url="../gerencia", status_code=307)

        app.mount("/gerencia", StaticFiles(directory=gerencia_dir), name="gerencia")

    if check_dir.exists():
        @app.get("/user", include_in_schema=False)
        def user_page() -> FileResponse:
            return FileResponse(check_dir / "index.html")

        @app.get("/user/", include_in_schema=False)
        def user_page_trailing_slash() -> RedirectResponse:
            return RedirectResponse(url="../user", status_code=307)

        app.mount("/user", StaticFiles(directory=check_dir), name="user")

    if transport_dir.exists():
        @app.get("/transport", include_in_schema=False)
        def transport_page() -> FileResponse:
            return FileResponse(transport_dir / "index.html")

        @app.get("/transport/", include_in_schema=False)
        def transport_page_trailing_slash() -> RedirectResponse:
            return RedirectResponse(url="../transport", status_code=307)

        app.mount("/transport", StaticFiles(directory=transport_dir), name="transport")
