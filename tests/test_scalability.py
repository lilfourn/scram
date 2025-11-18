import pytest
from unittest.mock import AsyncMock, patch
from src.agent.nodes import crawl_manager_node, rust_execution_node
from src.agent.state import AgentState


@pytest.mark.asyncio
async def test_template_detection():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[
            "http://example.com/1",
            "http://example.com/2",
            "http://other.com/1",
        ],
        visited_urls=set(),
        extracted_data=[],
        current_urls=[],
        current_contents=[],
        current_screenshots=[],
        relevant_flags=[],
        batch_next_urls=[],
        template_groups={},
        optimized_templates=set(),
    )

    # Ensure batch size is sufficient
    from src.core.config import config

    config.BATCH_SIZE = 5

    result = await crawl_manager_node(state)

    groups = result["template_groups"]
    assert "example.com" in groups
    assert len(groups["example.com"]) == 2
    assert "other.com" in groups
    assert len(groups["other.com"]) == 1


@pytest.mark.asyncio
async def test_rust_execution_node():
    state = AgentState(
        session_title="Test",
        objective="Test",
        data_schema={},
        url_queue=[],
        visited_urls=set(),
        extracted_data=[],
        current_urls=[],
        current_contents=[],
        current_screenshots=[],
        relevant_flags=[],
        batch_next_urls=[],
        template_groups={},
        optimized_templates=set(),
    )

    # Just verify it runs without error for now
    result = await rust_execution_node(state)
    assert result == {}
