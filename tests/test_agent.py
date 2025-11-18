import pytest
from unittest.mock import AsyncMock, patch
from src.agent.state import AgentState
from src.agent.graph import app


@pytest.mark.asyncio
async def test_agent_workflow():
    # Mock dependencies
    with (
        patch("src.agent.nodes.gemini_client") as mock_gemini,
        patch("src.agent.nodes.fetching_engine") as mock_fetcher,
    ):
        # Setup Mocks using AsyncMock for async methods
        mock_gemini.generate_schema = AsyncMock(
            return_value={"type": "object", "properties": {"name": {"type": "string"}}}
        )

        # analyze_relevance needs to be an AsyncMock with side_effect
        mock_gemini.analyze_relevance = AsyncMock(
            side_effect=[
                {
                    "is_relevant": True,
                    "reason": "Test",
                    "next_urls": ["http://test.com/2"],
                },  # First URL
                {
                    "is_relevant": False,
                    "reason": "Not relevant",
                    "next_urls": [],
                },  # Second URL
            ]
        )

        mock_gemini.extract_data = AsyncMock(return_value=[{"name": "Test Item"}])

        # Mock fetch method
        mock_fetcher.fetch = AsyncMock(return_value=("<html>Content</html>", 200, b""))

        # Initial State
        initial_state = AgentState(
            session_title="Test Session",
            objective="Extract names",
            data_schema={},
            url_queue=["http://test.com/1"],
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

        result = await app.ainvoke(initial_state)

        assert len(result["extracted_data"]) >= 1
        assert result["extracted_data"][0]["name"] == "Test Item"
        assert "http://test.com/1" in result["visited_urls"]
        assert "http://test.com/2" in result["visited_urls"]
