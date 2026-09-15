"""Camera endpoints — placeholder for Phase 2."""

from fastapi import APIRouter, Depends

from ..core.security import require_api_key

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", dependencies=[Depends(require_api_key)])
async def list_cameras():
    """
    Phase 1: no central camera DB on the server.
    Cameras come from QGIS. Return empty list.
    """
    return {"cameras": [], "note": "cameras are managed client-side in Phase 1"}
