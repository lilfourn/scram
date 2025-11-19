# Scram Version 0.1: The Foundation

## Overview
Version 0.1 marks the successful establishment of Scram's core architecture. This release delivers a functional, intelligent web crawling agent powered by Google Gemini and controlled via a modern Terminal User Interface (TUI). The system is capable of understanding natural language objectives, navigating web pages semantically, and extracting structured data for Machine Learning applications.

## Key Features Implemented

### 1. Intelligent Agent Core (`src/agent`)
- **LangGraph Orchestration**: A robust state machine manages the crawling lifecycle, handling initialization, fetching, analysis, extraction, and refinement.
- **Semantic Navigation**: The agent utilizes Gemini to analyze page content and determine relevance to the user's objective, minimizing wasteful crawling.

### 2. High-Performance Fetching Engine (`src/fetching`)
- **Hybrid Strategy**: Implements a two-tier fetching system:
  - **Speed Tier**: Fast, async HTTP requests (httpx) via Rust.
  - **Evasion Tier**: Headless browser automation (Playwright) for dynamic content.
- **Efficiency**: 
  - **Incremental Scraping**: SQLite-backed caching with conditional requests (`ETag`) to avoid re-fetching unchanged content.
  - **Bandwidth Optimization**: Native `gzip`/`brotli` support and API discovery to prioritize lightweight data sources.
- **Resilience**: Built-in rate limiting, exponential backoff, and error handling.

### 3. Professional TUI (`src/tui`)
- **Interactive Dashboard**: A Textual-based interface providing real-time visibility into the agent's operations.
- **Live Feedback**: Users can define objectives, review extraction schemas, and monitor crawling progress via logs and stats.
- **Data Preview**: Real-time preview of extracted data items.

### 4. AI Integration (`src/ai`)
- **Gemini Powered**: Deep integration with Google Gemini for:
  - **Schema Generation**: Converting natural language goals into rigorous Pydantic models.
  - **Relevance Analysis**: Determining if a URL is worth crawling.
  - **Structured Extraction**: Parsing unstructured HTML into clean JSON objects.
- **Context Management**: 
  - **History Compression**: Summarizes long session histories to maintain LLM performance.
  - **Observation Pruning**: Compresses large HTML payloads before analysis.

### 5. Data Pipeline (`src/data`)
- **Validation**: Strict data validation using dynamically generated Pydantic schemas.
- **Advanced Export**: 
  - **Formats**: JSONL, CSV, SQLite, and `zstd`-compressed Parquet.
  - **Structural Compression**: Custom Schema-Data JSON format for high-efficiency storage.
  - **Semantic Deduplication**: Uses vector embeddings to identify and merge semantically identical items.
- **Session Management**: Automatic saving of session config, logs, and data to `scram_data/`.

## Architecture Snapshot
The codebase follows a modular design:
- `src/agent`: The "Brain" - LangGraph workflow and nodes.
- `src/ai`: The "Intelligence" - Prompts and Gemini API wrappers.
- `src/fetching`: The "Hands" - Network requests and browser control.
- `src/tui`: The "Face" - User interface and interaction logic.
- `src/core`: Configuration, logging, and event systems.
- `src/data`: Export logic and graph handling.

## Usage
To launch the application:
```bash
python main.py
```
This initiates the TUI, where you can define a new session, set your objective, and start the intelligent crawler.

## Roadmap (Next Steps)
With the foundation and efficiency layers (Phase 1-3) largely in place, development shifts to advanced scale and distributed operations:
- **Phase 4 (Scalability)**: Implementing the adaptive model distillation pipeline and distributed crawling capabilities.
- **Phase 5 (Stealth)**: Advanced fingerprinting resistance and behavioral synthesis refinement.

## Implemented Phase Details

### Phase 1: Rust HPC (Completed)
- **Core Library**: `scram_hpc_rs` created and linked via PyO3.
- **Performance**: HTTP fetching offloaded to Rust using `reqwest`/`tokio` for high concurrency.
- **TLS**: `rustls` integration for consistent handshakes.

### Phase 2: Mirage Engine (Completed)
- **Browser Automation**: Implemented `MirageBrowser` in Rust using `chromiumoxide` (Chrome DevTools Protocol).
- **Stealth**: Integrated "Behavioral Synthesis" (jitter, random delays) to mimic human activity.
- **Hybrid Fetching**: Agent successfully escalates from HTTP to Mirage Browser when blocked.

### Phase 3: Intelligence & Efficiency (Completed)
- **Incremental Scraping**: Implemented SQLite-backed caching with `ETag`/`Last-Modified` support to skip unchanged resources.
- **Context Compression**: Added `ContextCompressor` to summarize session history and truncate large HTML observations, preventing context window overflows.
- **ML Data Pipeline**:
  - **Parquet Export**: High-efficiency storage with `zstd` compression.
  - **Structural Compression**: Custom Schema-Data JSON format to reduce redundancy.
  - **Semantic Deduplication**: Vector-based deduplication using Gemini embeddings to merge semantically identical items.
- **Bandwidth Optimization**: Enabled `gzip`/`brotli` in Rust fetcher and added API endpoint discovery to prefer lightweight JSON over HTML.
