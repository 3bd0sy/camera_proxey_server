"""Stream session domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class StreamSession:
    """Represents a live streaming session."""

    session_id: str
    camera_id: str
    media_path: str  # path inside media backend (e.g. mtx)
    public_url: str  # URL clients should read
    requested_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = None
    # Runtime-only sensitive data
    rtsp_url: str = field(default="", repr=False)
    is_alive: bool = True
