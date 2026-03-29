from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .core.config import settings
from .database import Base, engine
from .routers import admin, device, health
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
    SessionMiddleware,
    secret_key=settings.admin_session_secret,
    max_age=settings.admin_session_max_age_seconds,
    same_site="lax",
    https_only=False,
)


app.include_router(health.router)
app.include_router(device.router)
app.include_router(admin.router)

static_dir = Path(__file__).resolve().parent / "static"
assets_dir = Path(__file__).resolve().parents[2] / "assets"
if static_dir.exists():
    @app.get("/admin", include_in_schema=False)
    def legacy_admin_redirect_root() -> RedirectResponse:
        return RedirectResponse(url="./", status_code=307)

    @app.get("/admin/{path:path}", include_in_schema=False)
    def legacy_admin_redirect(path: str = "") -> RedirectResponse:
        return RedirectResponse(url="../", status_code=307)

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    app.mount("/", StaticFiles(directory=static_dir / "admin", html=True), name="admin")
