"""
Data models and enums for the load testing tool.
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field, field_validator
import validators


class AttackMode(str, Enum):
    """Available attack modes."""
    GET = "get"
    POST = "post"
    HEAD = "head"
    SLOW = "slow"  # Slowloris
    HTTP2 = "http2"


class ProxyType(str, Enum):
    """Supported proxy types."""
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    HTTP = "http"


class ProxyConfig(BaseModel):
    """Proxy configuration."""
    host: str = Field(..., description="Proxy host address")
    port: int = Field(..., ge=1, le=65535, description="Proxy port")
    proxy_type: ProxyType = Field(default=ProxyType.SOCKS5)
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def url(self) -> str:
        """Get proxy URL."""
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type.value}://{self.host}:{self.port}"

    @property
    def address(self) -> str:
        """Get proxy address as host:port."""
        return f"{self.host}:{self.port}"


class AttackConfig(BaseModel):
    """Main attack configuration with validation."""

    # Target configuration
    target_url: str = Field(..., description="Target URL to test")
    mode: AttackMode = Field(default=AttackMode.GET)

    # Performance settings
    threads: int = Field(default=100, ge=1, le=10000, description="Number of concurrent workers")
    duration: int = Field(default=60, ge=1, le=3600, description="Attack duration in seconds")
    requests_per_connection: int = Field(default=100, ge=1, le=1000)

    # Proxy settings
    proxy_file: str = Field(default="proxy.txt")
    proxy_type: ProxyType = Field(default=ProxyType.SOCKS5)

    # HTTP settings
    custom_headers: dict[str, str] = Field(default_factory=dict)
    cookies: dict[str, str] = Field(default_factory=dict)
    post_data: Optional[str] = None
    timeout: int = Field(default=10, ge=1, le=60)

    # Advanced settings
    brute_mode: bool = Field(default=False, description="Enable TCP_NODELAY")
    use_http2: bool = Field(default=False, description="Use HTTP/2")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    # Educational safeguards
    simulation_mode: bool = Field(default=True, description="Simulation mode (no real requests)")
    whitelist: List[str] = Field(default_factory=list, description="Whitelisted domains")
    require_authorization: bool = Field(default=True)
    authorization_token: Optional[str] = None

    @field_validator("target_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate target URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        if not validators.url(v):
            raise ValueError(f"Invalid URL: {v}")

        # Block localhost and private IPs
        if any(x in v.lower() for x in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]):
            raise ValueError("Localhost testing is not allowed in production mode")

        return v

    @field_validator("whitelist")
    @classmethod
    def validate_whitelist(cls, v: List[str]) -> List[str]:
        """Validate whitelist domains."""
        for domain in v:
            if not validators.domain(domain):
                raise ValueError(f"Invalid domain in whitelist: {domain}")
        return v


class AttackStats(BaseModel):
    """Statistics for an attack session."""

    session_id: str
    target_url: str
    mode: AttackMode

    # Timing
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0

    # Request stats
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Response stats
    status_codes: dict[int, int] = Field(default_factory=dict)
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0

    # Proxy stats
    total_proxies: int = 0
    active_proxies: int = 0
    failed_proxies: int = 0

    # Performance
    requests_per_second: float = 0.0
    bytes_sent: int = 0
    bytes_received: int = 0

    def calculate_metrics(self) -> None:
        """Calculate derived metrics."""
        if self.end_time and self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
            if self.duration > 0:
                self.requests_per_second = self.total_requests / self.duration

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class RequestResult(BaseModel):
    """Result of a single request."""

    success: bool
    status_code: Optional[int] = None
    response_time: float = 0.0
    error: Optional[str] = None
    proxy_used: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
