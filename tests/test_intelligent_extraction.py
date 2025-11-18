import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.agent.nodes import fetcher_node, extractor_node, healing_node
from src.agent.state import AgentState


@pytest.mark.asyncio
async def test_fetcher_node_returns_screenshots():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[],
        visited_urls=set(),
        failed_urls=set(),
        extracted_data=[],
        current_urls=["http://test.com"],
        current_contents=[],
        current_screenshots=[],
        relevant_flags=[],
        batch_next_urls=[],
        template_groups={},
        optimized_templates=set(),
    )

    with patch("src.agent.nodes.fetching_engine") as mock_engine:
        # Mock fetch
        mock_engine.fetch = AsyncMock(return_value=("<html>Content</html>", 200, b""))

        result = await fetcher_node(state)

        assert len(result["current_contents"]) == 1
        assert len(result["current_screenshots"]) == 1
        assert result["current_screenshots"][0] == b""  # Default empty bytes for HTTP


@pytest.mark.asyncio
async def test_extractor_node_uses_screenshots():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[],
        visited_urls=set(),
        failed_urls=set(),
        extracted_data=[],
        current_urls=["http://test.com"],
        current_contents=["<html>Content</html>"],
        current_screenshots=[b"fake_image_data"],
        relevant_flags=[True],
        batch_next_urls=[],
        template_groups={},
        optimized_templates=set(),
    )

    with patch("src.agent.nodes.gemini_client") as mock_client:
        mock_client.extract_data = AsyncMock(return_value=[{"name": "Test"}])

        await extractor_node(state)

        # Verify extract_data was called with screenshot
        mock_client.extract_data.assert_called_once()
        args, kwargs = mock_client.extract_data.call_args
        assert args[0] == "<html>Content</html>"  # content
        assert args[2] == b"fake_image_data"  # screenshot


@pytest.mark.asyncio
async def test_healing_node():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[],
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
    )

    result = await healing_node(state)
    assert result == {}  # Should return empty dict for now
