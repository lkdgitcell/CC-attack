"""
Configuration management with environment variables and validation.
"""

import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "HTTP Load Tester EDU"
    app_version: str = "4.0.1"
    debug: bool = Field(default=False, description="Enable debug mode")

    # Paths
    data_dir: Path = Field(default=Path("data"), description="Data directory")
    logs_dir: Path = Field(default=Path("logs"), description="Logs directory")
    proxy_dir: Path = Field(default=Path("proxies"), description="Proxy files directory")

    # Web Dashboard
    web_host: str = Field(default="127.0.0.1", description="Web server host")
    web_port: int = Field(default=8080, ge=1024, le=65535, description="Web server port")
    web_reload: bool = Field(default=False, description="Auto-reload web server")

    # Security
    enable_whitelist: bool = Field(default=True, description="Enable domain whitelist")
    simulation_mode_default: bool = Field(default=True, description="Default to simulation mode")
    require_auth_token: bool = Field(default=False, description="Require authorization token")
    auth_token: Optional[str] = Field(default=None, description="Authorization token")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or console)")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Performance
    max_concurrent_requests: int = Field(
        default=1000, ge=1, le=100000, description="Max concurrent requests"
    )
    connection_pool_size: int = Field(default=100, ge=1, le=1000)
    request_timeout: int = Field(default=30, ge=1, le=300)

    # Proxy sources (for download)
    proxy_check_timeout: int = Field(default=5, ge=1, le=30)
    proxy_check_url: str = Field(default="http://1.1.1.1", description="URL for proxy checking")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [self.data_dir, self.logs_dir, self.proxy_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug


# Global settings instance
settings = Settings()


# User agent lists for randomization
USER_AGENTS = {
    "chrome": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ],
    "firefox": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ],
    "safari": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ],
}

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
]

ACCEPT_LANGUAGE = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "fr-FR,fr;q=0.9",
    "de-DE,de;q=0.9",
]

ACCEPT_ENCODING = [
    "gzip, deflate, br",
    "gzip, deflate",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.yahoo.com/",
]
