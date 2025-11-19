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
async def test_fetching_flow_http_success():
    engine = FetchingEngine()
    engine.rate_limiter.acquire = AsyncMock()

    # Mock HTTP fetch (Rust HPC)
    with patch(
        "src.fetching.engine.scram_hpc_rs.fetch_url", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ("<html>Success</html>", 200, 100, {})

        # We don't start the full engine, just test the worker logic or internal methods
        # But to test worker, we need to start it.
        # Let's just test _fetch_http directly first
        content, status, wire_length = await engine._fetch_http("http://example.com")
        assert status == 200
        assert content == "<html>Success</html>"
        assert wire_length == 100


@pytest.mark.asyncio
async def test_fetching_flow_browser_success():
    engine = FetchingEngine()
    engine.rate_limiter.acquire = AsyncMock()

    # Mock Browser fetch (Rust Mirage)
    with patch(
        "src.fetching.engine.scram_hpc_rs.fetch_browser", new_callable=AsyncMock
    ) as mock_fetch:
        # Return tuple with screenshot bytes
        mock_fetch.return_value = (
            "<html>Browser Success</html>",
            200,
            b"fake_screenshot",
        )

        content, status, screenshot = await engine._fetch_browser("http://example.com")
        assert status == 200
        assert content == "<html>Browser Success</html>"
        assert screenshot == b"fake_screenshot"


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
