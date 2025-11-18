from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes import (
    initialization_node,
    crawl_manager_node,
    fetcher_node,
    relevance_analyzer_node,
    extractor_node,
    refinement_node,
    finalization_node,
    healing_node,
    rust_execution_node,
)


def should_extract(state: AgentState) -> str:
    """Condition to determine if we should extract data."""
    if any(state.get("relevant_flags", [])):
        # Check if we can use optimized extraction
        # For MVP, we just check if the domain is in optimized_templates
        # In a real implementation, we'd check the specific URL against the template

        # This logic is simplified. We need to check if ANY of the current URLs match an optimized template.
        # If so, we should probably split the batch or handle it.
        # For now, if ANY match, we go to extractor (safe default).
        # If ALL match, we could go to rust_execution_node.

        # Let's assume for now we stick to Python extractor unless explicitly optimized
        return "extractor"
    return "crawl_manager"


def has_next_url(state: AgentState) -> str:
    """Condition to check if there are URLs to process."""
    if state.get("current_urls"):
        return "fetcher"
    return "finalization"


workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("initialization", initialization_node)
workflow.add_node("crawl_manager", crawl_manager_node)
workflow.add_node("fetcher", fetcher_node)
workflow.add_node("relevance_analyzer", relevance_analyzer_node)
workflow.add_node("queue_updater", refinement_node)  # Using refinement_node logic
workflow.add_node("extractor", extractor_node)
workflow.add_node("rust_execution", rust_execution_node)
workflow.add_node("healing", healing_node)
workflow.add_node("finalization", finalization_node)

# Set Entry Point
workflow.set_entry_point("initialization")

# Add Edges
workflow.add_edge("initialization", "crawl_manager")

# Conditional Edge from CrawlManager
workflow.add_conditional_edges(
    "crawl_manager",
    has_next_url,
    {"fetcher": "fetcher", "finalization": "finalization"},
)

workflow.add_edge("fetcher", "relevance_analyzer")
workflow.add_edge("relevance_analyzer", "queue_updater")

# Conditional Edge from QueueUpdater (was Refinement)
workflow.add_conditional_edges(
    "queue_updater",
    should_extract,
    {
        "extractor": "extractor",
        "crawl_manager": "crawl_manager",
        "rust_execution": "rust_execution",
    },
)

# Extractor can go to healing if needed, but for now we just loop back
# In a real implementation, we'd check for validation errors
workflow.add_edge("extractor", "crawl_manager")
workflow.add_edge("rust_execution", "crawl_manager")
workflow.add_edge("healing", "crawl_manager")
workflow.add_edge("finalization", END)

# Compile
app = workflow.compile()
