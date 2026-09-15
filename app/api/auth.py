"""Auth endpoints."""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional

from ..core.config import get_config
from ..schemas.auth import WhoAmIResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(x_api_key: Optional[str] = Header(None)):
    cfg = get_config()
    if cfg.server.api_key and x_api_key != cfg.server.api_key:
        raise HTTPException(401, "Invalid API key")
    return WhoAmIResponse(
        username="api-client",
        role="admin",
        allowed_cameras=["*"],
    )
