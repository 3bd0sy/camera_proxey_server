"""Streams endpoints — the core API."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional

from ..core.config import get_config


from ..core.security import require_api_key
from ..media import get_media_backend
from ..media.ffmpeg import FFmpegBackend
from ..models.camera import CameraRequest
from ..schemas.stream import (
    StreamCreateRequest,
    StreamCreateResponse,
    StreamStatusResponse,
    SessionListResponse,
)
from ..services.stream_service import StreamService
from ..core.security import SecurityError

logger = logging.getLogger("camera_server.api.streams")

router = APIRouter(prefix="/streams", tags=["streams"])


def _get_service() -> StreamService:
    return StreamService()


def _get_user(x_api_key: Optional[str]) -> str:
    return "api-client" if x_api_key else "anonymous"


# ============================================================
# Create stream
# ============================================================


@router.post(
    "",
    response_model=StreamCreateResponse,
    dependencies=[Depends(require_api_key)],
)
async def create_stream(
    payload: StreamCreateRequest,
    request: Request,
    x_api_key: Optional[str] = None,
):
    user = _get_user(x_api_key)
    camera = CameraRequest(
        camera_id=payload.camera_id,
        host=payload.host,
        port=payload.port,
        protocol=payload.protocol,
        username=payload.username,
        password=payload.password,
        path=payload.path,
        requested_by=str(payload.requested_by or ""),
    )

    service = _get_service()
    try:
        session = await service.start_stream(camera, user)
    except SecurityError as e:
        raise HTTPException(403, str(e))
    except RuntimeError as e:
        raise HTTPException(429, str(e))
    except FileNotFoundError as e:
        raise HTTPException(500, f"Media backend error: {e}")
    except Exception as e:
        logger.exception("create_stream failed")
        raise HTTPException(500, str(e))

    cfg = get_config()

    if cfg.server.public_url:
        base_url = cfg.server.public_url.rstrip("/")
        logger.debug("Using configured public_url: %s", base_url)
    else:
        base_url = str(request.base_url).rstrip("/")
        logger.debug("Using request.base_url: %s", base_url)

    if session.public_url.startswith(("/", "api/")):
        stream_url = f"{base_url}{session.public_url}"
        logger.info("Built absolute URL: %s", stream_url)
    else:
        stream_url = session.public_url
        logger.info("Using full URL from backend: %s", stream_url)

    if stream_url.startswith("rtsp://"):
        stream_type = "rtsp"
    elif stream_url.startswith(("http://", "https://")):
        stream_type = "mjpeg"
    else:
        stream_type = "unknown"

    return StreamCreateResponse(
        session_id=session.session_id,
        camera_id=session.camera_id,
        status="started",
        stream_url=stream_url,
        stream_type=stream_type,
        # stream_url=session.public_url,
        # stream_type="rtsp" if session.public_url.startswith("rtsp://") else "mjpeg",
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


# ============================================================
# MJPEG inline stream (only for FFmpeg backend)
# ============================================================


@router.get("/{session_id}/video.mjpeg")
async def stream_mjpeg(session_id: str):
    """
    Only valid when backend == FFmpeg.
    MediaMTX clients read from MediaMTX directly.
    """
    service = _get_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found or expired")

    media = get_media_backend()
    if not isinstance(media, FFmpegBackend):
        raise HTTPException(
            400,
            "This endpoint is only available with the ffmpeg backend",
        )

    async def gen():
        try:
            async for chunk in media.iter_chunks(session_id):
                yield chunk
        except Exception:
            logger.exception("Streaming failed")

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=ffserver",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Connection": "close",
        },
    )


# ============================================================
# Get status
# ============================================================


@router.get(
    "/{session_id}",
    response_model=StreamStatusResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_stream(session_id: str):
    service = _get_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    alive = await get_media_backend().is_alive(session_id)
    return StreamStatusResponse(
        session_id=session.session_id,
        camera_id=session.camera_id,
        is_alive=alive,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


# ============================================================
# Destroy
# ============================================================


@router.delete(
    "/{session_id}",
    dependencies=[Depends(require_api_key)],
)
async def destroy_stream(
    session_id: str,
    x_api_key: Optional[str] = None,
):
    user = _get_user(x_api_key)
    service = _get_service()
    ok = await service.stop_stream(session_id, user)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"status": "destroyed", "session_id": session_id}


# ============================================================
# List all
# ============================================================


@router.get(
    "",
    response_model=SessionListResponse,
    dependencies=[Depends(require_api_key)],
)
async def list_streams():
    service = _get_service()
    sessions = await service.list_sessions()
    return SessionListResponse(
        sessions=[
            StreamStatusResponse(
                session_id=s.session_id,
                camera_id=s.camera_id,
                is_alive=await get_media_backend().is_alive(s.session_id),
                created_at=s.created_at,
                expires_at=s.expires_at,
            )
            for s in sessions
        ],
        count=len(sessions),
    )
