"""Configuration loader with pydantic-settings."""

import os
from pathlib import Path
from functools import lru_cache
from typing import List, Optional

import yaml
from pydantic import BaseModel


class SSLConfig(BaseModel):
    """SSL/TLS configuration for HTTPS."""

    enabled: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ssl_version: Optional[str] = None


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8443
    api_key: Optional[str] = None
    ssl: SSLConfig = SSLConfig()
    public_url: str = ""


class SecurityConfig(BaseModel):
    allowed_camera_networks: List[str] = []
    allowed_protocols: List[str] = ["RTSP"]
    allowed_ports: List[int] = [554, 8554]


class SessionsConfig(BaseModel):
    ttl_seconds: int = 3600
    cleanup_interval_seconds: int = 60
    max_concurrent_sessions: int = 50


class FFmpegConfig(BaseModel):
    binary_path: str = "ffmpeg"
    rtsp_transport: str = "tcp"
    framerate: int = 15
    jpeg_quality: int = 5


class MediaMTXConfig(BaseModel):
    api_url: str = "http://127.0.0.1:9997"
    public_rtsp_host: str = "127.0.0.1"
    public_rtsp_port: int = 8554
    username: str = ""
    password: str = ""


class MediaConfig(BaseModel):
    backend: str = "ffmpeg"  # "ffmpeg" | "mediamtx"
    ffmpeg: FFmpegConfig = FFmpegConfig()
    mediamtx: MediaMTXConfig = MediaMTXConfig()


class AuditConfig(BaseModel):
    enabled: bool = True
    file: str = "audit.log"


class AppConfig(BaseModel):
    server: ServerConfig
    security: SecurityConfig
    sessions: SessionsConfig
    media: MediaConfig
    audit: AuditConfig


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    path = os.environ.get(
        "CAMERA_SERVER_CONFIG",
        str(Path(__file__).parent.parent.parent / "config.yaml"),
    )
    data = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    return AppConfig(
        server=ServerConfig(**(data.get("server") or {})),
        security=SecurityConfig(**(data.get("security") or {})),
        sessions=SessionsConfig(**(data.get("sessions") or {})),
        media=MediaConfig(**(data.get("media") or {})),
        audit=AuditConfig(**(data.get("audit") or {})),
    )
