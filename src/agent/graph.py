from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes import (
    initialization_node,
    crawl_manager_node,
    fetcher_node,
    relevance_analyzer_node,
    extractor_node,
    refinement_node,
)


def should_extract(state: AgentState) -> str:
    """Condition to determine if we should extract data."""
    if state.get("is_relevant"):
        return "extractor"
    return "crawl_manager"


def has_next_url(state: AgentState) -> str:
    """Condition to check if there are URLs to process."""
    if state.get("current_url"):
        return "fetcher"
    return END


workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("initialization", initialization_node)
workflow.add_node("crawl_manager", crawl_manager_node)
workflow.add_node("fetcher", fetcher_node)
workflow.add_node("relevance_analyzer", relevance_analyzer_node)
workflow.add_node("queue_updater", refinement_node)  # Using refinement_node logic
workflow.add_node("extractor", extractor_node)

# Set Entry Point
workflow.set_entry_point("initialization")

# Add Edges
workflow.add_edge("initialization", "crawl_manager")

# Conditional Edge from CrawlManager
workflow.add_conditional_edges(
    "crawl_manager", has_next_url, {"fetcher": "fetcher", END: END}
)

workflow.add_edge("fetcher", "relevance_analyzer")
workflow.add_edge("relevance_analyzer", "queue_updater")

# Conditional Edge from QueueUpdater (was Refinement)
workflow.add_conditional_edges(
    "queue_updater",
    should_extract,
    {"extractor": "extractor", "crawl_manager": "crawl_manager"},
)

workflow.add_edge("extractor", "crawl_manager")

# Compile
app = workflow.compile()
