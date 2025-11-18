import asyncio
import logging
import random
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import scram_hpc_rs

from src.core.config import config
from src.fetching.rate_limiter import RateLimiter
from src.core.events import event_bus

logger = logging.getLogger(__name__)


class FetchingEngine:
    def __init__(self):
        self.rate_limiter = RateLimiter()

    def _sanitize_url(self, url: str) -> str:
        """Strip query parameters and fragments for safe logging."""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except Exception:
            return "INVALID_URL"

    async def fetch(self, url: str) -> tuple[str, int, bytes]:
        """
        Fetch a URL with rate limiting and automatic escalation.
        Returns: (content, status_code, screenshot_bytes)
        """
        safe_url = self._sanitize_url(url)

        # Rate Limiting
        event_bus.publish("log", message=f"Rate Limiting: {urlparse(url).netloc}")
        await self.rate_limiter.acquire(url)

        logger.info(f"Fetching: {safe_url}")

        # Tier 1: HTTP Fetch
        content, status = await self._fetch_http(url)

        # Tier 2: Browser Fetch (Escalation)
        screenshot = b""
        if self._should_escalate(status, content):
            logger.warning(f"Escalating to browser for {safe_url} (Status: {status})")
            content, status, screenshot = await self._fetch_browser(url)

        if status == 200:
            logger.info(f"Successfully fetched {safe_url} ({len(content)} bytes)")
            event_bus.publish("stats_update", metric="pages_scanned", increment=1)
        else:
            logger.error(f"Failed to fetch {safe_url}. Status: {status}")
            event_bus.publish("stats_update", metric="errors", increment=1)

        return content, status, screenshot

    async def _fetch_http(self, url: str) -> tuple[str, int]:
        """Tier 1: Fetch using Rust HPC (TLS spoofing)."""
        try:
            headers = {"User-Agent": random.choice(config.USER_AGENTS)}
            # Call Rust function
            content, status = await scram_hpc_rs.fetch_url(url, headers)
            return content, status
        except Exception as e:
            logger.warning(f"HTTP fetch failed for {url}: {e}")
            return "", 0

    async def _fetch_browser(self, url: str) -> tuple[str, int, bytes]:
        """Tier 2: Fetch using Rust Mirage Engine (CDP)."""
        try:
            # Call Rust function
            content, status, screenshot = await scram_hpc_rs.fetch_browser(
                url, config.HEADLESS
            )
            # Convert screenshot (list of ints) to bytes
            screenshot_bytes = bytes(screenshot) if screenshot else b""
            return content, status, screenshot_bytes
        except Exception as e:
            logger.error(f"Browser fetch failed for {url}: {e}")
            return "", 0, b""

    def _should_escalate(self, status: int, content: str) -> bool:
        """Determine if we should escalate to browser fetching."""
        if status in [403, 429, 503]:
            return True
        # Simple check for Cloudflare/bot detection text
        if "challenge" in content.lower() or "cloudflare" in content.lower():
            return True
        return False
