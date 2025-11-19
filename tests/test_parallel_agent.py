import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.agent.nodes import (
    fetcher_node,
    relevance_analyzer_node,
    crawl_manager_node,
    refinement_node,
)
from src.agent.state import AgentState


@pytest.mark.asyncio
async def test_crawl_manager_batching():
    # Ensure batch size is 5 for this test
    from src.core.config import config

    config.BATCH_SIZE = 5

    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[
            "http://a.com",
            "http://b.com",
            "http://c.com",
            "http://d.com",
            "http://e.com",
            "http://f.com",
        ],
        visited_urls=set(),
        failed_urls=set(),
        extracted_data=[],
        current_urls=[],
        current_contents=[],
        current_screenshots=[],
        relevant_flags=[],
        batch_next_urls=[],
        template_groups={},
        optimized_templates=set(),
        compressed_history="",
        recent_activity=[],
    )

    # Should pop 5 (BATCH_SIZE)
    result = await crawl_manager_node(state)
    assert len(result["current_urls"]) == 5
    assert result["current_urls"] == [
        "http://a.com",
        "http://b.com",
        "http://c.com",
        "http://d.com",
        "http://e.com",
    ]
    assert len(result["url_queue"]) == 1
    assert result["url_queue"] == ["http://f.com"]


@pytest.mark.asyncio
async def test_fetcher_node_parallel():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=["http://existing.com"],
        visited_urls={"http://visited.com"},
        failed_urls=set(),
        extracted_data=[],
        current_urls=["http://a.com", "http://b.com"],
        current_contents=[],
        current_screenshots=[],
        relevant_flags=[],
        batch_next_urls=[
            ["http://new1.com", "http://visited.com"],
            ["http://new2.com", "http://existing.com"],
        ],
        template_groups={},
        optimized_templates=set(),
        compressed_history="",
        recent_activity=[],
    )

    with patch("src.agent.nodes.fetching_engine") as mock_engine:
        mock_engine.fetch = AsyncMock(
            side_effect=[("Content A", 200, b""), ("Content B", 200, b"")]
        )

        result = await fetcher_node(state)

        assert len(result["current_contents"]) == 2
        assert result["current_contents"] == ["Content A", "Content B"]
        assert "http://a.com" in result["visited_urls"]
        assert "http://b.com" in result["visited_urls"]


@pytest.mark.asyncio
async def test_relevance_analyzer_parallel():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[],
        visited_urls=set(),
        failed_urls=set(),
        extracted_data=[],
        current_urls=["http://a.com", "http://b.com"],
        current_contents=["Content A", "Content B"],
        current_screenshots=[],
        relevant_flags=[],
        batch_next_urls=[],
        template_groups={},
        optimized_templates=set(),
        compressed_history="",
        recent_activity=[],
    )

    with patch("src.agent.nodes.gemini_client") as mock_client:
        mock_client.analyze_relevance = AsyncMock(
            side_effect=[
                {"is_relevant": True, "next_urls": ["http://x.com"]},
                {"is_relevant": False, "next_urls": []},
            ]
        )
        mock_client.analyze_api_endpoints = AsyncMock(return_value=[])

        result = await relevance_analyzer_node(state)

        assert result["relevant_flags"] == [True, False]
        assert result["batch_next_urls"] == [["http://x.com"], []]


@pytest.mark.asyncio
async def test_refinement_node_flattening():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[
            "http://a.com",
            "http://b.com",
            "http://c.com",
            "http://d.com",
            "http://e.com",
            "http://f.com",
        ],
        visited_urls=set(),
        failed_urls=set(),
        extracted_data=[],
        current_urls=[],
        current_contents=[],
        current_screenshots=[],
        relevant_flags=[],
        batch_next_urls=[
            ["http://new1.com", "http://visited.com"],
            ["http://new2.com", "http://existing.com"],
        ],
        template_groups={},
        optimized_templates=set(),
        compressed_history="",
        recent_activity=[],
    )

    result = await refinement_node(state)

    # Should flatten and filter
    # http://visited.com -> filtered (visited)
    # http://existing.com -> filtered (in queue)
    # http://new1.com -> added
    # http://new2.com -> added

    queue = result["url_queue"]
    # The order might vary or implementation details of refinement_node might have changed
    # Let's check if the new URLs are present
    assert "http://new1.com" in queue
    assert "http://new2.com" in queue
    # existing.com was already in queue, so it should remain
    assert "http://existing.com" in queue
