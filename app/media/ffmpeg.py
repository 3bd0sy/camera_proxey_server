"""
FFmpeg inline media backend.
Produces MJPEG chunks directly to clients (Phase 1 fallback).
"""

import asyncio
import logging
import os
import shutil
from typing import AsyncIterator, Dict, Optional

from .base import MediaBackend
from ..core.config import FFmpegConfig

logger = logging.getLogger("camera_server.media.ffmpeg")


class _FFmpegProcess:
    def __init__(self, source_url: str):
        self.source_url = source_url
        self.process: Optional[asyncio.subprocess.Process] = None
        self.is_alive_flag = False

    async def start(self, cfg: FFmpegConfig) -> None:
        binary = cfg.binary_path
        if not shutil.which(binary) and not os.path.isfile(binary):
            raise FileNotFoundError(f"FFmpeg not found: {binary}")

        cmd = [
            binary,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-rtsp_transport",
            cfg.rtsp_transport,
            "-i",
            self.source_url,
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-q:v",
            str(cfg.jpeg_quality),
            "-r",
            str(cfg.framerate),
            "pipe:1",
        ]
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.is_alive_flag = True
        asyncio.create_task(self._drain_stderr())
        logger.info("FFmpeg started PID=%s", self.process.pid)

    async def _drain_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return
        try:
            async for line in self.process.stderr:
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    logger.debug("FFmpeg: %s", text)
        except Exception:
            logger.exception("stderr drain failed")

    async def iter_chunks(self, size: int = 16384) -> AsyncIterator[bytes]:
        if not self.process or not self.process.stdout:
            return
        while self.is_alive_flag:
            chunk = await self.process.stdout.read(size)
            if not chunk:
                break
            yield chunk

    async def stop(self) -> None:
        if not self.process:
            return
        self.is_alive_flag = False
        try:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        except ProcessLookupError:
            pass
        except Exception:
            logger.exception("Error stopping FFmpeg")
        self.process = None

    def kill_nowait(self) -> None:
        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass


class FFmpegBackend(MediaBackend):
    """One FFmpeg process per session."""

    def __init__(self, cfg: FFmpegConfig):
        self.cfg = cfg
        self._procs: Dict[str, _FFmpegProcess] = {}

    async def start(self, session_id: str, rtsp_url: str) -> str:
        proc = _FFmpegProcess(rtsp_url)
        await proc.start(self.cfg)
        self._procs[session_id] = proc
        # URL handled by the streams router
        return f"/api/v1/streams/{session_id}/video.mjpeg"

    async def stop(self, session_id: str) -> None:
        proc = self._procs.pop(session_id, None)
        if proc:
            await proc.stop()

    async def is_alive(self, session_id: str) -> bool:
        proc = self._procs.get(session_id)
        return bool(proc and proc.is_alive_flag)

    async def iter_chunks(self, session_id: str) -> AsyncIterator[bytes]:
        proc = self._procs.get(session_id)
        if not proc:
            return
        async for chunk in proc.iter_chunks():
            yield chunk

    async def shutdown(self) -> None:
        for sid in list(self._procs.keys()):
            self._procs[sid].kill_nowait()
        self._procs.clear()
