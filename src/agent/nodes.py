import logging
from typing import Dict, Any

from src.agent.state import AgentState
from src.fetching.engine import FetchingEngine
from src.ai.gemini import GeminiClient
from src.core.events import event_bus

logger = logging.getLogger(__name__)

# Global instances (to be initialized in main or graph setup)
fetching_engine = FetchingEngine()
gemini_client = GeminiClient()


async def initialization_node(state: AgentState) -> Dict[str, Any]:
    """Initialize the session and generate schema if needed."""
    logger.info(f"Initializing session: {state['session_title']}")
    event_bus.publish("agent_activity", status="Initializing Session")

    updates = {}

    if not state.get("data_schema"):
        logger.info("Generating schema from objective...")
        event_bus.publish("agent_activity", status="Generating Schema (AI)")
        try:
            schema = await gemini_client.generate_schema(state["objective"])
            updates["data_schema"] = schema
        except Exception as e:
            logger.error(f"Failed to generate schema: {e}")
            # Fallback or error handling

    return updates


async def crawl_manager_node(state: AgentState) -> Dict[str, Any]:
    """Select the next URL to crawl."""
    event_bus.publish("agent_activity", status="Managing Queue")
    if not state["url_queue"]:
        logger.info("Queue is empty.")
        return {"current_url": None}

    # Simple FIFO for now
    next_url = state["url_queue"].pop(0)

    if next_url in state["visited_urls"]:
        logger.info(f"Skipping visited URL: {next_url}")
        return await crawl_manager_node(state)

    return {"current_url": next_url, "url_queue": state["url_queue"]}


async def fetcher_node(state: AgentState) -> Dict[str, Any]:
    """Fetch the content of the current URL."""
    url = state.get("current_url")
    if not url:
        return {}

    logger.info(f"Fetching: {url}")
    event_bus.publish("agent_activity", status=f"Fetching {url}")

    # Simulate worker activity for the UI since we are running in a single-threaded graph node here
    # In a real concurrent setup, the engine would handle this.
    # We'll just update worker 0 for visual feedback.
    event_bus.publish(
        "worker_status", worker_id=0, status=f"Fetching {url}", progress=30
    )

    # We use the engine's internal methods directly for this synchronous-like flow
    # In a real high-concurrency scenario, this would be different.
    # We'll use the Tier 1 fetch first.
    content, status = await fetching_engine._fetch_http(url)

    if fetching_engine._should_escalate(status, content):
        logger.info("Escalating to browser fetch...")
        event_bus.publish("agent_activity", status="Escalating to Browser")
        event_bus.publish(
            "worker_status", worker_id=0, status="Escalating to Browser", progress=50
        )

        # Ensure browser is started if not already
        if not fetching_engine.browser:
            await fetching_engine.start()
        content, status = await fetching_engine._fetch_browser(url)

    if status != 200:
        logger.warning(f"Failed to fetch {url}, status: {status}")
        event_bus.publish("worker_status", worker_id=0, status="Failed", progress=0)
        return {"current_content": None, "visited_urls": {url} | state["visited_urls"]}

    event_bus.publish("worker_status", worker_id=0, status="Fetched", progress=100)
    event_bus.publish("stats_update", metric="pages_scanned", increment=1)

    return {"current_content": content, "visited_urls": {url} | state["visited_urls"]}


async def relevance_analyzer_node(state: AgentState) -> Dict[str, Any]:
    """Analyze content relevance and extract links."""
    content = state.get("current_content")
    url = state.get("current_url")

    if not content or not url:
        return {"is_relevant": False, "next_urls": []}

    event_bus.publish("agent_activity", status="Analyzing Relevance (AI)")
    event_bus.publish(
        "worker_status", worker_id=0, status="Analyzing Relevance", progress=60
    )

    analysis = await gemini_client.analyze_relevance(state["objective"], content, url)

    logger.info(f"Relevance: {analysis.get('is_relevant')} - {analysis.get('reason')}")

    updates = {
        "is_relevant": analysis.get("is_relevant", False),
        "next_urls": analysis.get("next_urls", []),
    }

    # Generate title if it's the placeholder
    if state.get("session_title") == "Generating Title..." and analysis.get(
        "is_relevant"
    ):
        try:
            event_bus.publish("agent_activity", status="Generating Title (AI)")
            new_title = await gemini_client.generate_title(state["objective"], content)
            updates["session_title"] = new_title
            # We might want to emit an event to update the UI title here if the UI supports it
            # For now, it just updates the state
            logger.info(f"Generated session title: {new_title}")
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")

    return updates


async def extractor_node(state: AgentState) -> Dict[str, Any]:
    """Extract data from relevant content."""
    if not state.get("is_relevant"):
        event_bus.publish("worker_status", worker_id=0, status="Idle", progress=0)
        return {}

    content = state.get("current_content")
    if not content:
        return {}

    event_bus.publish("agent_activity", status="Extracting Data (AI)")
    event_bus.publish(
        "worker_status", worker_id=0, status="Extracting Data", progress=80
    )

    data = await gemini_client.extract_data(content, state["data_schema"])

    if data:
        logger.info(f"Extracted {len(data)} items.")
        event_bus.publish("stats_update", metric="items_extracted", increment=len(data))
        current_data = state.get("extracted_data", [])
        event_bus.publish("worker_status", worker_id=0, status="Idle", progress=0)
        return {"extracted_data": current_data + data}

    event_bus.publish("worker_status", worker_id=0, status="Idle", progress=0)
    return {}


async def refinement_node(state: AgentState) -> Dict[str, Any]:
    """Add new URLs to the queue."""
    new_urls = state.get("next_urls", [])
    current_queue = state.get("url_queue", [])
    visited = state.get("visited_urls", set())

    # Filter duplicates and visited
    unique_new_urls = [
        url for url in new_urls if url not in visited and url not in current_queue
    ]

    if unique_new_urls:
        logger.info(f"Adding {len(unique_new_urls)} new URLs to queue.")

    return {"url_queue": current_queue + unique_new_urls}
