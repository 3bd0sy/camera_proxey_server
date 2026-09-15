"""Abstract media backend interface."""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class MediaBackend(ABC):
    """
    A media backend manages one stream of data per session.

    Two concerns:
      - Lifecycle: start/stop
      - Data: either provide an MJPEG chunk iterator (FFmpeg) or a URL (MediaMTX)
    """

    @abstractmethod
    async def start(self, session_id: str, rtsp_url: str) -> str:
        """
        Start a stream.
        Returns a public URL that clients should read.
        """

    @abstractmethod
    async def stop(self, session_id: str) -> None:
        """Stop and release resources."""

    @abstractmethod
    async def is_alive(self, session_id: str) -> bool:
        """Check if stream is alive."""

    async def iter_chunks(self, session_id: str) -> AsyncIterator[bytes]:
        """
        Only used by inline backends (FFmpeg).
        MediaMTX backend leaves this unimplemented.
        """
        raise NotImplementedError("This backend does not support inline iteration")

    async def shutdown(self) -> None:
        """Optional cleanup on server shutdown."""
        return
