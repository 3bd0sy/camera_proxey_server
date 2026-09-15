"""
Authentication service.
Phase 1: simple API-key based. Placeholder for JWT.
"""

import logging
from typing import Optional

from ..core.config import get_config
from ..core.security import SecurityError

logger = logging.getLogger("camera_server.auth")


class AuthService:
    """Very simple authn — replace with JWT/OIDC in production."""

    def authenticate_api_key(self, provided: Optional[str]) -> bool:
        expected = get_config().server.api_key
        if not expected:
            return True
        return provided == expected

    def get_current_user(self, x_api_key: Optional[str]) -> str:
        """Return an identity string. In real deployments, use JWT claims."""
        if not self.authenticate_api_key(x_api_key):
            raise SecurityError("Authentication failed")
        return "api-client"
