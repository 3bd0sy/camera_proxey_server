"""
MediaMTX backend.
MediaMTX runs as a separate process (managed externally).
This backend uses MediaMTX's HTTP API to add/remove paths dynamically.
"""

import logging
from typing import Dict

import httpx

from .base import MediaBackend
from ..core.config import MediaMTXConfig

logger = logging.getLogger("camera_server.media.mediamtx")


class MediaMTXBackend(MediaBackend):
    """
    Control plane for MediaMTX.
    Each session = one path in MediaMTX.
    Clients read from MediaMTX via RTSP/WebRTC/HLS.
    """

    def __init__(self, cfg: MediaMTXConfig):
        self.cfg = cfg
        self._paths: Dict[str, str] = {}  # session_id -> path_name

    def _auth(self):
        if self.cfg.username:
            return (self.cfg.username, self.cfg.password)
        return None

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.cfg.api_url,
            auth=self._auth(),
            timeout=10.0,
        )

    async def start(self, session_id: str, rtsp_url: str) -> str:
        path_name = f"cam_{session_id[:12]}"

        payload = {
            "source": rtsp_url,
            "sourceOnDemand": True,  # lazy connect
            "sourceOnDemandCloseAfter": "10s",
        }

        async with await self._client() as client:
            await client.delete(f"/v3/config/paths/delete/{path_name}")
            r = await client.post(
                f"/v3/config/paths/add/{path_name}",
                json=payload,
            )
            r.raise_for_status()

        self._paths[session_id] = path_name
        logger.info(
            "MediaMTX path created: %s → %s", path_name, rtsp_url.split("@")[-1]
        )

        # Client reads via RTSP from MediaMTX
        public = (
            f"rtsp://{self.cfg.public_rtsp_host}:"
            f"{self.cfg.public_rtsp_port}/{path_name}"
        )
        return public

    async def stop(self, session_id: str) -> None:
        path_name = self._paths.pop(session_id, None)
        if not path_name:
            return
        async with await self._client() as client:
            r = await client.delete(f"/v3/config/paths/delete/{path_name}")
            if r.status_code not in (200, 404):
                logger.warning("MediaMTX delete failed: %s", r.status_code)
        logger.info("MediaMTX path removed: %s", path_name)

    async def is_alive(self, session_id: str) -> bool:
        path_name = self._paths.get(session_id)
        if not path_name:
            return False
        async with await self._client() as client:
            r = await client.get(f"/v3/paths/get/{path_name}")
            if r.status_code != 200:
                return False
            data = r.json()
            return data.get("ready", False)

    async def shutdown(self) -> None:
        for sid in list(self._paths.keys()):
            try:
                await self.stop(sid)
            except Exception:
                logger.exception("Failed to stop %s on shutdown", sid)
