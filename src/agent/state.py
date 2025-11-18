from typing import Any, Dict, List, Set, TypedDict, Optional


class AgentState(TypedDict):
    session_title: str
    objective: str
    data_schema: Dict[str, Any]  # JSON Schema representation
    url_queue: List[str]
    visited_urls: Set[str]
    extracted_data: List[Any]
    current_url: Optional[str]
    current_content: Optional[str]
    is_relevant: bool
    next_urls: List[str]
