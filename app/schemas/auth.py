"""Pydantic schemas for Auth API."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class WhoAmIResponse(BaseModel):
    username: str
    role: str
    allowed_cameras: list[str]
