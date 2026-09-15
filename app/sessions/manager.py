"""In-memory session manager with TTL cleanup."""

import asyncio
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from ..core.config import get_config
from ..media import get_media_backend
from ..models.stream import StreamSession

logger = logging.getLogger("camera_server.sessions")


class SessionManager:
    """Holds active stream sessions in RAM."""

    def __init__(self):
        self._sessions: Dict[str, StreamSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        cfg = get_config().sessions
        self._cleanup_task = asyncio.create_task(
            self._cleanup_loop(cfg.cleanup_interval_seconds)
        )
        logger.info("Session manager started (TTL=%ss)", cfg.ttl_seconds)

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        media = get_media_backend()
        for sid in list(self._sessions.keys()):
            try:
                await media.stop(sid)
            except Exception:
                logger.exception("Failed to stop session %s on shutdown", sid)
        self._sessions.clear()
        await media.shutdown()

    async def create(
        self,
        camera_id: str,
        rtsp_url: str,
        requested_by: str = "",
    ) -> StreamSession:
        cfg = get_config()
        async with self._lock:
            if len(self._sessions) >= cfg.sessions.max_concurrent_sessions:
                raise RuntimeError("Max sessions reached")

            session_id = secrets.token_urlsafe(24)
            media = get_media_backend()
            public_url = await media.start(session_id, rtsp_url)

            now = datetime.now(timezone.utc)
            session = StreamSession(
                session_id=session_id,
                camera_id=camera_id,
                media_path=session_id,
                public_url=public_url,
                requested_by=requested_by,
                created_at=now,
                expires_at=now + timedelta(seconds=cfg.sessions.ttl_seconds),
                rtsp_url=rtsp_url,
                is_alive=True,
            )
            self._sessions[session_id] = session
            logger.info("Session created: %s camera=%s", session_id, camera_id)
            return session

    async def get(self, session_id: str) -> Optional[StreamSession]:
        async with self._lock:
            s = self._sessions.get(session_id)
            if s and self._is_expired(s):
                await self._destroy_locked(session_id)
                return None
            return s

    async def destroy(self, session_id: str) -> bool:
        async with self._lock:
            return await self._destroy_locked(session_id)

    async def _destroy_locked(self, session_id: str) -> bool:
        s = self._sessions.pop(session_id, None)
        if not s:
            return False
        try:
            await get_media_backend().stop(session_id)
        except Exception:
            logger.exception("Failed to stop media for %s", session_id)
        logger.info("Session destroyed: %s", session_id)
        return True

    def _is_expired(self, s: StreamSession) -> bool:
        return datetime.now(timezone.utc) > s.expires_at

    def list_all(self) -> List[StreamSession]:
        return list(self._sessions.values())

    async def _cleanup_loop(self, interval: int) -> None:
        while True:
            try:
                await asyncio.sleep(interval)
                await self._cleanup_once()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Cleanup error")

    async def _cleanup_once(self) -> None:
        async with self._lock:
            expired = [sid for sid, s in self._sessions.items() if self._is_expired(s)]
            for sid in expired:
                logger.info("Expired: %s", sid)
                await self._destroy_locked(sid)


_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
