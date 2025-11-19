import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from src.fetching.engine import FetchingEngine
from src.data.cache import CacheManager


@pytest.mark.asyncio
async def test_incremental_scraping_logic():
    # Setup
    engine = FetchingEngine()
    # Use an in-memory DB for testing
    engine.cache = CacheManager(":memory:")

    url = "https://example.com/data"
    content = "<html>Data</html>"
    etag = "v1"

    # Mock scram_hpc_rs.fetch_url
    with patch("scram_hpc_rs.fetch_url", new_callable=AsyncMock) as mock_fetch:
        # Scenario 1: First Fetch (200 OK)
        mock_fetch.return_value = (content, 200, len(content), {"etag": etag})

        res_content, status, _ = await engine._fetch_http(url)

        assert status == 200
        assert res_content == content

        # Verify Cache Update
        entry = engine.cache.get_entry(url)
        assert entry is not None
        assert entry["content"] == content
        assert entry["etag"] == etag

        # Scenario 2: Second Fetch (304 Not Modified)
        # Reset mock to return 304
        mock_fetch.return_value = ("", 304, 0, {})

        res_content_2, status_2, _ = await engine._fetch_http(url)

        # Verify Headers sent
        call_args = mock_fetch.call_args
        sent_headers = call_args[0][1]
        assert sent_headers["If-None-Match"] == etag

        # Verify Result (Should return cached content)
        assert status_2 == 200  # Engine converts 304 -> 200 with cached content
        assert res_content_2 == content


@pytest.mark.asyncio
async def test_content_deduplication():
    engine = FetchingEngine()
    engine.cache = CacheManager(":memory:")

    url = "https://example.com/dynamic"
    content = "Same Content"

    with patch("scram_hpc_rs.fetch_url", new_callable=AsyncMock) as mock_fetch:
        # First Fetch
        mock_fetch.return_value = (content, 200, 100, {})
        await engine._fetch_http(url)

        # Second Fetch (200 OK but same content)
        mock_fetch.return_value = (content, 200, 100, {})

        # We just want to ensure it runs without error and updates/checks cache
        res_content, status, _ = await engine._fetch_http(url)
        assert res_content == content

        # Verify hash in cache
        entry = engine.cache.get_entry(url)
        assert entry["content_hash"] == engine.cache.get_content_hash(content)
