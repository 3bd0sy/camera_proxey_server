"""
Authorization service.
Phase 1: any authenticated user can access any camera.
Phase 2: map user → allowed cameras.
"""

import logging

from ..models.camera import CameraRequest

logger = logging.getLogger("camera_server.authz")


class AuthorizationService:
    """Placeholder for per-camera authorization."""

    def can_access(self, user: str, camera: CameraRequest) -> bool:
        # Phase 1: permissive. Phase 2 will check DB / token claims.
        return True
