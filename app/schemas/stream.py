"""Pydantic schemas for Streams API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StreamCreateRequest(BaseModel):
    camera_id: str = Field(..., min_length=1, max_length=128)
    host: str = Field(..., min_length=1)
    port: int = Field(554, ge=1, le=65535)
    protocol: str = Field("RTSP")
    username: str = Field("", max_length=128)
    password: str = Field("", max_length=256)
    path: str = Field("", max_length=512)
    requested_by: Optional[str] = None


class StreamCreateResponse(BaseModel):
    session_id: str
    camera_id: str
    status: str
    stream_url: str
    stream_type: str
    created_at: datetime
    expires_at: datetime


class StreamStatusResponse(BaseModel):
    session_id: str
    camera_id: str
    is_alive: bool
    created_at: datetime
    expires_at: datetime


class SessionListResponse(BaseModel):
    sessions: list[StreamStatusResponse]
    count: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
