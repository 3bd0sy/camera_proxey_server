"""Append-only audit logger — never stores credentials."""

import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.config import get_config

logger = logging.getLogger("camera_server.audit")


def _write(record: dict) -> None:
    cfg = get_config().audit
    if not cfg.enabled:
        return
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    line = json.dumps(record, ensure_ascii=False)
    try:
        with open(cfg.file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        logger.exception("Failed to write audit log")


def log_event(
    action: str,
    user: Optional[str] = None,
    camera_id: Optional[str] = None,
    session_id: Optional[str] = None,
    result: str = "SUCCESS",
    detail: str = "",
) -> None:
    """Log a single audit event (no credentials)."""
    _write(
        {
            "action": action,
            "user": user,
            "camera_id": camera_id,
            "session_id": session_id,
            "result": result,
            "detail": detail,
        }
    )
