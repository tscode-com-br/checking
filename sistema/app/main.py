from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .database import Base, engine
from .routers import admin, device, health


app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def startup() -> None:
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)


app.include_router(health.router)
app.include_router(device.router)
app.include_router(admin.router)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/admin", StaticFiles(directory=static_dir / "admin", html=True), name="admin")
