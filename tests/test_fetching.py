import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.fetching.rate_limiter import RateLimiter
from src.fetching.engine import FetchingEngine
from src.core.config import config


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = RateLimiter()
    limiter.global_limit = 100  # Fast for test
    limiter.domain_limit = 100

    start = asyncio.get_running_loop().time()
    await limiter.acquire("http://example.com")
    await limiter.acquire("http://example.com")
    end = asyncio.get_running_loop().time()

    # Should be very fast since limits are high
    assert end - start < 1.0


@pytest.mark.asyncio
async def test_fetching_engine_lifecycle():
    engine = FetchingEngine()

    # Mock Playwright
    with patch("src.fetching.engine.async_playwright") as mock_playwright_func:
        # Setup the mock chain for await async_playwright().start()
        mock_context_manager = MagicMock()
        mock_playwright_obj = MagicMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()

        # async_playwright() returns the context manager
        mock_playwright_func.return_value = mock_context_manager

        # .start() returns an awaitable that yields the playwright object
        start_future = asyncio.Future()
        start_future.set_result(mock_playwright_obj)
        mock_context_manager.start.return_value = start_future

        # playwright.chromium.launch() needs to be an async method
        mock_playwright_obj.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright_obj.stop = AsyncMock()

        # browser.new_context() needs to be an async method
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        # context.close()
        mock_context.close = AsyncMock()

        await engine.start()
        assert engine.active
        assert len(engine.workers) == config.MAX_CONCURRENCY

        await engine.stop()
        assert not engine.active


@pytest.mark.asyncio
async def test_fetching_flow_http_success():
    engine = FetchingEngine()
    engine.rate_limiter.acquire = AsyncMock()

    # Mock HTTP fetch
    with patch("src.fetching.engine.curl_requests.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.get.return_value.text = "<html>Success</html>"
        mock_session.get.return_value.status_code = 200
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # We don't start the full engine, just test the worker logic or internal methods
        # But to test worker, we need to start it.
        # Let's just test _fetch_http directly first
        content, status = await engine._fetch_http("http://example.com")
        assert status == 200
        assert content == "<html>Success</html>"


@pytest.mark.asyncio
async def test_escalation_logic():
    engine = FetchingEngine()

    # Should escalate on 403
    assert engine._should_escalate(403, "") is True

    # Should escalate on Cloudflare challenge
    assert (
        engine._should_escalate(200, "Please complete the security challenge to access")
        is True
    )

    # Should not escalate on normal 200
    assert engine._should_escalate(200, "<html>Normal content</html>") is False
