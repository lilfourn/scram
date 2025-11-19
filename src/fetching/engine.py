import asyncio
import logging
import random
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import scram_hpc_rs

from src.core.config import config
from src.fetching.rate_limiter import RateLimiter
from src.core.events import event_bus
from src.data.cache import CacheManager

logger = logging.getLogger(__name__)


class FetchingEngine:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.total_bandwidth_saved = 0
        self.cache = CacheManager()

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
        content, status, wire_length = await self._fetch_http(url)

        # Tier 2: Browser Fetch (Escalation)
        screenshot = b""
        if self._should_escalate(status, content):
            logger.warning(f"Escalating to browser for {safe_url} (Status: {status})")
            content, status, screenshot = await self._fetch_browser(url)
            # Browser fetch doesn't return wire length easily, assume 0 saved or ignore
            wire_length = None

        if status == 200:
            logger.info(f"Successfully fetched {safe_url} ({len(content)} bytes)")
            event_bus.publish("stats_update", metric="pages_scanned", increment=1)

            # Calculate bandwidth saved
            if wire_length is not None:
                # wire_length is the compressed size
                # len(content) is the uncompressed size (approx)
                saved_bytes = max(0, len(content) - wire_length)
                self.total_bandwidth_saved += saved_bytes

                saved_mb = self.total_bandwidth_saved / (1024 * 1024)
                event_bus.publish(
                    "stats_update", metric="bandwidth_saved", value=f"{saved_mb:.2f} MB"
                )
            else:
                # Fallback if wire_length is unknown (e.g. chunked encoding or browser fetch)
                # We don't update the metric to avoid guessing
                pass

        else:
            logger.error(f"Failed to fetch {safe_url}. Status: {status}")
            event_bus.publish("stats_update", metric="errors", increment=1)

        return content, status, screenshot

    async def _fetch_http(self, url: str) -> tuple[str, int, Optional[int]]:
        """Tier 1: Fetch using Rust HPC (TLS spoofing) with Caching."""
        try:
            headers = {
                "User-Agent": random.choice(config.USER_AGENTS),
                "Accept-Encoding": "gzip, br",
                "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            # Check Cache
            cache_entry = self.cache.get_entry(url)
            if cache_entry:
                if cache_entry.get("etag"):
                    headers["If-None-Match"] = cache_entry["etag"]
                if cache_entry.get("last_modified"):
                    headers["If-Modified-Since"] = cache_entry["last_modified"]

            # Call Rust function
            # Returns (content, status, wire_length, response_headers)
            (
                content,
                status,
                wire_length,
                response_headers,
            ) = await scram_hpc_rs.fetch_url(url, headers)

            # Handle 304 Not Modified
            if status == 304 and cache_entry:
                logger.info(f"Cache Hit (304) for {url}")
                return (
                    cache_entry["content"],
                    200,
                    0,
                )  # Return cached content as 200 for processing

            # Handle 200 OK
            if status == 200:
                # Check for content hash match (Deduplication)
                new_hash = self.cache.get_content_hash(content)
                if cache_entry and cache_entry.get("content_hash") == new_hash:
                    logger.info(f"Content Unchanged (Hash Match) for {url}")
                    # We could skip processing here, but the agent might need to see it again.
                    # For now, we just update the timestamp in cache implicitly if we were to save it again.
                    # But let's just return it.

                # Update Cache
                etag = response_headers.get("etag") or response_headers.get("ETag")
                last_modified = response_headers.get(
                    "last-modified"
                ) or response_headers.get("Last-Modified")
                self.cache.update_entry(url, content, etag, last_modified)

            return content, status, wire_length
        except Exception as e:
            logger.warning(f"HTTP fetch failed for {url}: {e}")
            return "", 0, None

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
