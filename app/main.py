"""FastAPI application factory — Control Plane only."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .core.logging import setup_logging
from .sessions.manager import get_session_manager
from .api import auth as auth_api
from .api import cameras as cameras_api
from .api import streams as streams_api
from .core.security import SecurityError

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    mgr = get_session_manager()
    await mgr.start()
    yield
    await mgr.stop()


app = FastAPI(
    title="GIS Camera Server",
    version=__version__,
    description="Control plane for camera streaming (Phase 1).",
    lifespan=lifespan,
)


# --- Error handlers ---


@app.exception_handler(SecurityError)
async def security_error_handler(request: Request, exc: SecurityError):
    return JSONResponse(status_code=403, content={"error": str(exc)})


# --- Health ---


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


# --- Routers ---

app.include_router(auth_api.router, prefix="/api/v1")
app.include_router(cameras_api.router, prefix="/api/v1")
app.include_router(streams_api.router, prefix="/api/v1")
