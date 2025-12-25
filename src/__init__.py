"""
HTTP Load Testing Tool - Educational Version
Version 4.0.0 - BTS SIO SISR Edition

⚠️  EDUCATIONAL PURPOSE ONLY
This tool is designed for authorized security testing and load testing only.
Unauthorized use against systems you don't own is illegal.

Features:
- Modern async architecture with asyncio
- HTTP/2 support
- Web dashboard
- Professional logging
- Input validation
- Educational safeguards
"""

__version__ = "4.0.0"
__author__ = "Educational Version"

from src.models import AttackMode, ProxyType, AttackConfig
from src.attack_engine import AttackEngine

__all__ = ["AttackMode", "ProxyType", "AttackConfig", "AttackEngine", "__version__"]
