"""Data models and enums for the load testing tool."""

from enum import Enum
from typing import Optional
from datetime import datetime
from ipaddress import ip_address, IPv4Address
from pydantic import BaseModel, Field, field_validator
import validators


class AttackMode(str, Enum):
    GET = "get"
    POST = "post"
    HEAD = "head"
    HTTP2 = "http2"


class ProxyType(str, Enum):
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    HTTP = "http"


class ProxyConfig(BaseModel):
    model_config = {"frozen": False, "use_enum_values": True}

    host: str
    port: int = Field(ge=1, le=65535)
    proxy_type: ProxyType = ProxyType.SOCKS5
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type}://{self.host}:{self.port}"

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


class AttackConfig(BaseModel):
    model_config = {"frozen": False}

    target_url: str
    mode: AttackMode = AttackMode.GET
    threads: int = Field(default=100, ge=1, le=10000)
    duration: int = Field(default=60, ge=1, le=3600)
    requests_per_connection: int = Field(default=100, ge=1, le=1000)
    proxy_file: str = "proxy.txt"
    proxy_type: ProxyType = ProxyType.SOCKS5
    custom_headers: dict[str, str] = Field(default_factory=dict)
    cookies: dict[str, str] = Field(default_factory=dict)
    post_data: Optional[str] = None
    timeout: int = Field(default=10, ge=1, le=60)
    brute_mode: bool = False
    use_http2: bool = False
    verify_ssl: bool = True
    simulation_mode: bool = True
    whitelist: list[str] = Field(default_factory=list)
    require_authorization: bool = True
    authorization_token: Optional[str] = None

    @field_validator("target_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        if not validators.url(v):
            raise ValueError(f"Invalid URL: {v}")

        return v

    @field_validator("whitelist")
    @classmethod
    def validate_whitelist(cls, v: list[str]) -> list[str]:
        for domain in v:
            if domain and not validators.domain(domain):
                raise ValueError(f"Invalid domain in whitelist: {domain}")
        return v

    @field_validator("custom_headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str]) -> dict[str, str]:
        forbidden = {"host", "content-length", "transfer-encoding"}
        for key in v.keys():
            if key.lower() in forbidden:
                raise ValueError(f"Header '{key}' cannot be overridden")
            if "\r" in key or "\n" in key or "\r" in v[key] or "\n" in v[key]:
                raise ValueError("Headers cannot contain CRLF characters")
        return v


class AttackStats(BaseModel):
    model_config = {"frozen": False}

    session_id: str
    target_url: str
    mode: AttackMode
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    status_codes: dict[int, int] = Field(default_factory=dict)
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    total_proxies: int = 0
    active_proxies: int = 0
    failed_proxies: int = 0
    requests_per_second: float = 0.0
    bytes_sent: int = 0
    bytes_received: int = 0

    def calculate_metrics(self) -> None:
        if self.end_time and self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
            if self.duration > 0:
                self.requests_per_second = self.total_requests / self.duration

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class RequestResult(BaseModel):
    model_config = {"frozen": False}

    success: bool
    status_code: Optional[int] = None
    response_time: float = 0.0
    error: Optional[str] = None
    proxy_used: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
