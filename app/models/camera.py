"""Internal camera domain model (server-side, in-memory only)."""

from dataclasses import dataclass, field


@dataclass
class CameraRequest:
    """Temporary camera data received from QGIS — never persisted."""

    camera_id: str
    host: str
    port: int
    protocol: str
    username: str = ""
    password: str = field(default="", repr=False)  # excluded from repr
    path: str = ""
    requested_by: str = ""
