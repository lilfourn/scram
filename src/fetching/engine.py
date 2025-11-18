import asyncio
import logging
import random
from typing import Optional, Dict, Any, List, cast
from urllib.parse import urlparse

from curl_cffi import requests as curl_requests
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

from src.core.config import config
from src.fetching.rate_limiter import RateLimiter
from src.core.events import event_bus

logger = logging.getLogger(__name__)


class FetchingEngine:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.rate_limiter = RateLimiter()
        self.active = False
        self.workers: List[asyncio.Task] = []
        self.stealth = Stealth()

        # Browser resources
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context_pool: List[BrowserContext] = []

    async def start(self):
        """Initialize resources and start workers."""
        self.active = True
        logger.info("Starting FetchingEngine...")
        event_bus.publish("log", message="Starting FetchingEngine...")

        # Initialize Playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=config.HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Create context pool
        for _ in range(config.BROWSER_POOL_SIZE):
            context = await self._create_context()
            self.context_pool.append(context)

        # Start workers
        for i in range(config.MAX_CONCURRENCY):
            task = asyncio.create_task(self._worker(i))
            self.workers.append(task)

        logger.info(f"FetchingEngine started with {len(self.workers)} workers.")
        event_bus.publish(
            "log", message=f"FetchingEngine started with {len(self.workers)} workers."
        )

    async def stop(self):
        """Stop workers and release resources."""
        self.active = False
        await self.queue.join()

        for task in self.workers:
            task.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)

        # Close browser resources
        for context in self.context_pool:
            await context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        logger.info("FetchingEngine stopped.")
        event_bus.publish("log", message="FetchingEngine stopped.")

    async def enqueue_url(self, url: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a URL to the fetch queue."""
        await self.queue.put((url, metadata or {}))
        event_bus.publish("stats_update", metric="queue_size", value=self.queue.qsize())

    async def _create_context(self) -> BrowserContext:
        """Create a configured browser context."""
        if not self.browser:
            raise RuntimeError("Browser not initialized")

        user_agent = random.choice(config.USER_AGENTS)
        proxy_settings: Optional[Dict[str, Any]] = None
        if config.PROXIES:
            proxy_url = random.choice(config.PROXIES)
            if proxy_url:
                proxy_settings = {"server": proxy_url}

        context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",  # Could be randomized
            proxy=cast(Any, proxy_settings),
        )
        return context

    async def _worker(self, worker_id: int):
        """Worker loop to process URLs."""
        logger.debug(f"Worker {worker_id} started.")
        event_bus.publish(
            "worker_status", worker_id=worker_id, status="Idle", progress=0
        )

        while self.active:
            try:
                event_bus.publish(
                    "worker_status",
                    worker_id=worker_id,
                    status="Waiting for URL",
                    progress=0,
                )
                url, metadata = await self.queue.get()

                event_bus.publish(
                    "worker_status",
                    worker_id=worker_id,
                    status=f"Rate Limiting: {urlparse(url).netloc}",
                    progress=10,
                )
                await self.rate_limiter.acquire(url)

                logger.info(f"Worker {worker_id} fetching: {url}")
                event_bus.publish(
                    "worker_status",
                    worker_id=worker_id,
                    status=f"Fetching: {url}",
                    progress=30,
                )

                # Tier 1: HTTP Fetch
                content, status = await self._fetch_http(url)
                event_bus.publish(
                    "worker_status",
                    worker_id=worker_id,
                    status="Analyzing Response",
                    progress=60,
                )

                # Tier 2: Browser Fetch (Escalation)
                if self._should_escalate(status, content):
                    logger.warning(
                        f"Escalating to browser for {url} (Status: {status})"
                    )
                    event_bus.publish(
                        "worker_status",
                        worker_id=worker_id,
                        status="Escalating to Browser",
                        progress=70,
                    )
                    content, status = await self._fetch_browser(url)

                # TODO: Pass content to processing pipeline
                # For now, just log success
                if status == 200:
                    logger.info(f"Successfully fetched {url} ({len(content)} bytes)")
                    event_bus.publish(
                        "log", message=f"Fetched {url} ({len(content)} bytes)"
                    )
                    event_bus.publish(
                        "stats_update", metric="pages_scanned", increment=1
                    )
                else:
                    logger.error(f"Failed to fetch {url}. Status: {status}")
                    event_bus.publish(
                        "log", message=f"Failed to fetch {url}. Status: {status}"
                    )
                    event_bus.publish("stats_update", metric="errors", increment=1)

                event_bus.publish(
                    "worker_status", worker_id=worker_id, status="Done", progress=100
                )
                self.queue.task_done()
                event_bus.publish(
                    "stats_update", metric="queue_size", value=self.queue.qsize()
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                event_bus.publish("log", message=f"Worker {worker_id} error: {e}")
                self.queue.task_done()

        event_bus.publish(
            "worker_status", worker_id=worker_id, status="Stopped", progress=0
        )

    async def _fetch_http(self, url: str) -> tuple[str, int]:
        """Tier 1: Fetch using curl_cffi (TLS spoofing)."""
        try:
            proxies: Optional[Dict[str, str]] = None
            if config.PROXIES:
                proxy_url = random.choice(config.PROXIES)
                if proxy_url:
                    proxies = {"http": proxy_url, "https": proxy_url}

            # Using curl_cffi.requests.AsyncSession
            async with curl_requests.AsyncSession(
                impersonate="chrome120", proxies=cast(Any, proxies)
            ) as session:
                response = await session.get(
                    url,
                    headers={"User-Agent": random.choice(config.USER_AGENTS)},
                    timeout=30,
                )
                return response.text, response.status_code
        except Exception as e:
            logger.warning(f"HTTP fetch failed for {url}: {e}")
            return "", 0

    async def _fetch_browser(self, url: str) -> tuple[str, int]:
        """Tier 2: Fetch using Playwright."""
        context = random.choice(self.context_pool)
        page = await context.new_page()
        try:
            await self.stealth.apply_stealth_async(page)
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=60000
            )
            content = await page.content()
            status = response.status if response else 0
            return content, status
        except Exception as e:
            logger.error(f"Browser fetch failed for {url}: {e}")
            return "", 0
        finally:
            await page.close()

    def _should_escalate(self, status: int, content: str) -> bool:
        """Determine if we should escalate to browser fetching."""
        if status in [403, 429, 503]:
            return True
        # Simple check for Cloudflare/bot detection text
        if "challenge" in content.lower() or "cloudflare" in content.lower():
            return True
        return False
