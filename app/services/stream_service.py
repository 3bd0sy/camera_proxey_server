"""Business logic for stream sessions — orchestrates everything."""

import logging
from typing import List, Optional

from ..core.config import get_config
from ..core.security import (
    SecurityError,
    build_rtsp_url,
    validate_host_against_networks,
)
from ..models.camera import CameraRequest
from ..models.stream import StreamSession
from ..sessions.manager import get_session_manager
from ..audit import logger as audit
from .authorization_service import AuthorizationService

logger = logging.getLogger("camera_server.stream_service")


class StreamService:
    def __init__(self):
        self.authz = AuthorizationService()

    async def start_stream(
        self,
        camera: CameraRequest,
        user: str,
    ) -> StreamSession:
        cfg = get_config()

        # 1) Authorization
        if not self.authz.can_access(user, camera):
            audit.log_event(
                action="STREAM_START",
                user=user,
                camera_id=camera.camera_id,
                result="DENIED",
                detail="authorization",
            )
            raise SecurityError("Access denied")

        # 2) Protocol / port
        if camera.protocol.upper() not in [
            p.upper() for p in cfg.security.allowed_protocols
        ]:
            raise SecurityError(f"Protocol '{camera.protocol}' not allowed")
        if camera.port not in cfg.security.allowed_ports:
            raise SecurityError(f"Port {camera.port} not allowed")

        # 3) SSRF check
        validate_host_against_networks(
            camera.host, cfg.security.allowed_camera_networks
        )

        # 4) Build RTSP URL
        rtsp_url = build_rtsp_url(
            host=camera.host,
            port=camera.port,
            protocol=camera.protocol,
            username=camera.username,
            password=camera.password,
            path=camera.path,
        )

        # 5) Create session (media backend starts here)
        mgr = get_session_manager()
        session = await mgr.create(
            camera_id=camera.camera_id,
            rtsp_url=rtsp_url,
            requested_by=camera.requested_by,
        )

        audit.log_event(
            action="STREAM_START",
            user=user,
            camera_id=camera.camera_id,
            session_id=session.session_id,
            result="SUCCESS",
        )
        return session

    async def stop_stream(self, session_id: str, user: str) -> bool:
        mgr = get_session_manager()
        session = await mgr.get(session_id)
        if not session:
            return False
        ok = await mgr.destroy(session_id)
        audit.log_event(
            action="STREAM_STOP",
            user=user,
            camera_id=session.camera_id,
            session_id=session_id,
            result="SUCCESS" if ok else "FAILED",
        )
        return ok

    async def get_session(self, session_id: str) -> Optional[StreamSession]:
        return await get_session_manager().get(session_id)

    async def list_sessions(self) -> List[StreamSession]:
        return get_session_manager().list_all()
