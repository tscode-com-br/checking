from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .database import Base, engine
from .routers import admin, device, health
from .services.event_archives import ensure_event_archives_dir
from .services.forms_queue import forms_submission_worker


app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def startup() -> None:
    ensure_event_archives_dir()
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
    if settings.forms_queue_enabled:
        forms_submission_worker.start()


@app.on_event("shutdown")
def shutdown() -> None:
    if settings.forms_queue_enabled:
        forms_submission_worker.stop()


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
