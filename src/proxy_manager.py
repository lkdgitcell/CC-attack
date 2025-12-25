"""
Proxy management with async downloading, validation, and rotation.
"""

import asyncio
import random
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import urlparse

import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType as SocksProxyType

from src.models import ProxyConfig, ProxyType
from src.config import settings
from src.logger import logger


class ProxyManager:
    """Manages proxy downloading, validation, and rotation."""

    # Proxy source APIs
    SOCKS4_SOURCES = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4",
        "https://openproxylist.xyz/socks4.txt",
        "https://proxyspace.pro/socks4.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks4.txt",
        "https://www.proxy-list.download/api/v1/get?type=socks4",
    ]

    SOCKS5_SOURCES = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5",
        "https://openproxylist.xyz/socks5.txt",
        "https://proxyspace.pro/socks5.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks5.txt",
        "https://www.proxy-list.download/api/v1/get?type=socks5",
    ]

    HTTP_SOURCES = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
        "https://openproxylist.xyz/http.txt",
        "https://proxyspace.pro/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/http.txt",
        "https://www.proxy-list.download/api/v1/get?type=http",
    ]

    def __init__(self, proxy_type: ProxyType = ProxyType.SOCKS5):
        """
        Initialize ProxyManager.

        Args:
            proxy_type: Type of proxies to manage.
        """
        self.proxy_type = proxy_type
        self.proxies: List[ProxyConfig] = []
        self.dead_proxies: Set[str] = set()
        self._lock = asyncio.Lock()

        logger.info("proxy_manager_initialized", proxy_type=proxy_type.value)

    async def download_proxies(self, output_file: Optional[Path] = None) -> int:
        """
        Download proxies from multiple sources.

        Args:
            output_file: Optional file path to save proxies.

        Returns:
            Number of proxies downloaded.

        Raises:
            ValueError: If proxy type is invalid.
        """
        sources = {
            ProxyType.SOCKS4: self.SOCKS4_SOURCES,
            ProxyType.SOCKS5: self.SOCKS5_SOURCES,
            ProxyType.HTTP: self.HTTP_SOURCES,
        }

        if self.proxy_type not in sources:
            raise ValueError(f"Unsupported proxy type: {self.proxy_type}")

        logger.info("downloading_proxies", proxy_type=self.proxy_type.value)

        all_proxies: Set[str] = set()

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._download_from_source(session, url)
                for url in sources[self.proxy_type]
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.warning("download_failed", error=str(result))
                    continue
                if result:
                    all_proxies.update(result)

        # Parse proxies
        for proxy_str in all_proxies:
            try:
                proxy = self._parse_proxy(proxy_str.strip())
                if proxy:
                    self.proxies.append(proxy)
            except ValueError as e:
                logger.debug("invalid_proxy", proxy=proxy_str, error=str(e))

        # Save to file if requested
        if output_file:
            await self._save_proxies(output_file)

        logger.info(
            "proxies_downloaded",
            total=len(self.proxies),
            proxy_type=self.proxy_type.value,
        )

        return len(self.proxies)

    async def _download_from_source(
        self, session: aiohttp.ClientSession, url: str
    ) -> List[str]:
        """Download proxies from a single source."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    text = await response.text()
                    proxies = [line.strip() for line in text.split('\n') if line.strip()]
                    logger.debug("source_downloaded", url=url, count=len(proxies))
                    return proxies
                else:
                    logger.warning("source_failed", url=url, status=response.status)
                    return []
        except asyncio.TimeoutError:
            logger.warning("source_timeout", url=url)
            return []
        except Exception as e:
            logger.error("source_error", url=url, error=str(e))
            return []

    def _parse_proxy(self, proxy_str: str) -> Optional[ProxyConfig]:
        """
        Parse proxy string into ProxyConfig.

        Args:
            proxy_str: Proxy string (host:port or user:pass@host:port).

        Returns:
            ProxyConfig object or None if invalid.

        Raises:
            ValueError: If proxy format is invalid.
        """
        if not proxy_str or ':' not in proxy_str:
            return None

        # Skip comments
        if proxy_str.startswith('#'):
            return None

        parts = proxy_str.split(':')
        if len(parts) < 2:
            return None

        # Handle auth proxies (user:pass@host:port)
        if '@' in proxy_str:
            auth, location = proxy_str.rsplit('@', 1)
            username, password = auth.split(':', 1)
            host, port_str = location.rsplit(':', 1)
            return ProxyConfig(
                host=host,
                port=int(port_str),
                proxy_type=self.proxy_type,
                username=username,
                password=password,
            )

        # Simple format (host:port)
        host = parts[0]
        port_str = parts[1]

        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError(f"Port out of range: {port}")

            return ProxyConfig(
                host=host,
                port=port,
                proxy_type=self.proxy_type,
            )
        except ValueError:
            return None

    async def load_from_file(self, file_path: Path) -> int:
        """
        Load proxies from a file.

        Args:
            file_path: Path to proxy file.

        Returns:
            Number of proxies loaded.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Proxy file not found: {file_path}")

        logger.info("loading_proxies", file=str(file_path))

        async with asyncio.Lock():
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                proxy = self._parse_proxy(line.strip())
                if proxy:
                    self.proxies.append(proxy)

        # Remove duplicates
        seen = set()
        unique_proxies = []
        for proxy in self.proxies:
            if proxy.address not in seen:
                seen.add(proxy.address)
                unique_proxies.append(proxy)

        self.proxies = unique_proxies

        logger.info("proxies_loaded", total=len(self.proxies))
        return len(self.proxies)

    async def _save_proxies(self, file_path: Path) -> None:
        """Save proxies to file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as f:
            for proxy in self.proxies:
                f.write(f"{proxy.address}\n")

        logger.info("proxies_saved", file=str(file_path), total=len(self.proxies))

    async def validate_proxies(self, max_concurrent: int = 100) -> int:
        """
        Validate all proxies concurrently.

        Args:
            max_concurrent: Maximum concurrent validation requests.

        Returns:
            Number of working proxies.
        """
        if not self.proxies:
            logger.warning("no_proxies_to_validate")
            return 0

        logger.info("validating_proxies", total=len(self.proxies))

        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [
            self._validate_proxy(proxy, semaphore)
            for proxy in self.proxies
        ]

        results = await asyncio.gather(*tasks)

        # Filter out dead proxies
        working_proxies = [
            proxy for proxy, is_valid in zip(self.proxies, results) if is_valid
        ]

        removed = len(self.proxies) - len(working_proxies)
        self.proxies = working_proxies

        logger.info(
            "validation_complete",
            working=len(working_proxies),
            removed=removed,
        )

        return len(working_proxies)

    async def _validate_proxy(
        self, proxy: ProxyConfig, semaphore: asyncio.Semaphore
    ) -> bool:
        """Validate a single proxy."""
        async with semaphore:
            try:
                # Convert ProxyType to aiohttp-socks ProxyType
                proxy_type_map = {
                    ProxyType.SOCKS4: SocksProxyType.SOCKS4,
                    ProxyType.SOCKS5: SocksProxyType.SOCKS5,
                    ProxyType.HTTP: SocksProxyType.HTTP,
                }

                connector = ProxyConnector(
                    proxy_type=proxy_type_map[proxy.proxy_type],
                    host=proxy.host,
                    port=proxy.port,
                    username=proxy.username,
                    password=proxy.password,
                )

                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        settings.proxy_check_url,
                        timeout=aiohttp.ClientTimeout(total=settings.proxy_check_timeout),
                    ) as response:
                        is_valid = response.status == 200
                        if is_valid:
                            logger.debug("proxy_valid", proxy=proxy.address)
                        return is_valid

            except Exception as e:
                logger.debug("proxy_invalid", proxy=proxy.address, error=str(e))
                return False

    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """
        Get a random working proxy.

        Returns:
            Random ProxyConfig or None if no proxies available.
        """
        available = [p for p in self.proxies if p.address not in self.dead_proxies]

        if not available:
            # Reset dead proxies if all are dead
            if self.proxies:
                logger.warning("all_proxies_dead_resetting")
                self.dead_proxies.clear()
                available = self.proxies
            else:
                return None

        return random.choice(available)

    def mark_dead(self, proxy: ProxyConfig) -> None:
        """Mark a proxy as dead."""
        self.dead_proxies.add(proxy.address)
        logger.debug("proxy_marked_dead", proxy=proxy.address)

    def get_stats(self) -> dict:
        """Get proxy statistics."""
        return {
            "total": len(self.proxies),
            "active": len(self.proxies) - len(self.dead_proxies),
            "dead": len(self.dead_proxies),
            "type": self.proxy_type.value,
        }
