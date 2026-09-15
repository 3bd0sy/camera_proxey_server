"""Media backends factory."""
from .base import MediaBackend
from .ffmpeg import FFmpegBackend
from .mediamtx import MediaMTXBackend

from ..core.config import get_config


_backend_instance: MediaBackend | None = None


def get_media_backend() -> MediaBackend:
    global _backend_instance
    if _backend_instance is not None:
        return _backend_instance

    cfg = get_config()
    name = cfg.media.backend.lower()

    if name == "mediamtx":
        _backend_instance = MediaMTXBackend(cfg.media.mediamtx)
    else:
        _backend_instance = FFmpegBackend(cfg.media.ffmpeg)

    return _backend_instance


def reset_media_backend() -> None:
    global _backend_instance
    _backend_instance = None
