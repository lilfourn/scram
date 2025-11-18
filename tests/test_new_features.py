import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.ai.gemini import GeminiClient
from src.agent.nodes import relevance_analyzer_node
from src.agent.state import AgentState


@pytest.mark.asyncio
async def test_analyze_seed_url():
    client = GeminiClient()
    # Mock the fast model
    client.fast_model = MagicMock()
    client.fast_model.generate_content_async = AsyncMock(
        return_value=MagicMock(
            text='{"summary": "Test Summary", "suggestions": ["Obj 1", "Obj 2"]}'
        )
    )

    result = await client.analyze_seed_url("http://test.com", "content")

    assert result["summary"] == "Test Summary"
    assert len(result["suggestions"]) == 2
    client.fast_model.generate_content_async.assert_called_once()


@pytest.mark.asyncio
async def test_generate_title():
    client = GeminiClient()
    client.fast_model = MagicMock()
    client.fast_model.generate_content_async = AsyncMock(
        return_value=MagicMock(text="Test Title")
    )

    title = await client.generate_title("Objective", "Content")

    assert title == "Test Title"
    client.fast_model.generate_content_async.assert_called_once()


@pytest.mark.asyncio
async def test_relevance_node_generates_title():
    # Mock dependencies
    with patch("src.agent.nodes.gemini_client") as mock_gemini:
        # Setup mocks
        mock_gemini.analyze_relevance = AsyncMock(
            return_value={"is_relevant": True, "reason": "Relevant", "next_urls": []}
        )
        mock_gemini.generate_title = AsyncMock(return_value="Generated Title")

        state = AgentState(
            session_title="Generating Title...",
            objective="Test Objective",
            data_schema={},
            url_queue=[],
            visited_urls=set(),
            extracted_data=[],
            current_urls=["http://test.com"],
            current_contents=["Content"],
            current_screenshots=[],
            relevant_flags=[],
            batch_next_urls=[],
            template_groups={},
            optimized_templates=set(),
        )

        updates = await relevance_analyzer_node(state)

        assert updates["session_title"] == "Generated Title"
        mock_gemini.generate_title.assert_called_once()


@pytest.mark.asyncio
async def test_relevance_node_skips_title_if_already_set():
    # Mock dependencies
    with patch("src.agent.nodes.gemini_client") as mock_gemini:
        # Setup mocks
        mock_gemini.analyze_relevance = AsyncMock(
            return_value={"is_relevant": True, "reason": "Relevant", "next_urls": []}
        )

        state = AgentState(
            session_title="Existing Title",
            objective="Test Objective",
            data_schema={},
            url_queue=[],
            visited_urls=set(),
            extracted_data=[],
            current_urls=["http://test.com"],
            current_contents=["Content"],
            current_screenshots=[],
            relevant_flags=[],
            batch_next_urls=[],
            template_groups={},
            optimized_templates=set(),
        )

        updates = await relevance_analyzer_node(state)

        assert "session_title" not in updates
        mock_gemini.generate_title.assert_not_called()
