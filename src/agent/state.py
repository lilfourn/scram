from typing import Any, Dict, List, Set, TypedDict, Optional


class AgentState(TypedDict):
    session_title: str
    objective: str
    data_schema: Dict[str, Any]  # JSON Schema representation
    url_queue: List[str]
    visited_urls: Set[str]
    failed_urls: Set[str]  # Track URLs that failed to fetch
    extracted_data: List[Dict[str, Any]]
    current_urls: List[str]
    current_contents: List[Optional[str]]
    current_screenshots: List[bytes]
    relevant_flags: List[bool]
    batch_next_urls: List[List[str]]
    template_groups: Dict[str, List[str]]  # Template ID -> List of URLs
    optimized_templates: Set[str]  # Set of Template IDs that are optimized
