# Task 02: AI Agent Framework (LangGraph)

## Goal
Build the "Brain" of Scram using LangGraph to manage the crawling workflow, state, and AI decision-making.

## Requirements

### 1. Agent State
Define the `State` TypedDict/Pydantic model:
- `session_title`: str
- `objective`: str (User's goal)
- `data_schema`: Pydantic Model (Dynamic)
- `url_queue`: List[str]
- `visited_urls`: Set[str]
- `extracted_data`: List[Any]
- `cache`: Dict[str, str] (URL -> HTML)

### 2. Nodes (Workflow Steps)
Implement the following LangGraph nodes:
- **Initialization**: Setup state from user input.
- **CrawlManager**: Manage queue and prioritization.
- **Fetcher**: Call the `FetchingEngine` (from Task 01).
- **RelevanceAnalyzer** (AI):
  - Prompt Gemini: "Is this page relevant to [objective]?"
  - Extract new links.
- **Extractor** (AI):
  - Use Gemini Function Calling to extract data into `data_schema`.
- **Presenter**: Pause for TUI feedback.
- **Refinement** (AI): Update schema based on user feedback.

### 3. Edges (Logic Flow)
- Connect nodes as per the plan:
  - `Init` -> `CrawlManager`
  - `CrawlManager` -> `Fetcher` or `Presenter`
  - `Fetcher` -> `RelevanceAnalyzer`
  - `RelevanceAnalyzer` -> `Extractor` (if relevant) or `CrawlManager`
  - `Extractor` -> `CrawlManager`

### 4. AI Engine Integration
- Create a wrapper for Google Gemini API.
- Implement prompt templates for Relevance and Extraction.

## Definition of Done
- LangGraph graph is compiled and runnable.
- Mock tests verify the flow between nodes.
- Gemini integration is tested (can generate schema and extract data).
