# Scram Version 0.1: The Foundation

## Overview
Version 0.1 marks the successful establishment of Scram's core architecture. This release delivers a functional, intelligent web crawling agent powered by Google Gemini and controlled via a modern Terminal User Interface (TUI). The system is capable of understanding natural language objectives, navigating web pages semantically, and extracting structured data for Machine Learning applications.

## Key Features Implemented

### 1. Intelligent Agent Core (`src/agent`)
- **LangGraph Orchestration**: A robust state machine manages the crawling lifecycle, handling initialization, fetching, analysis, extraction, and refinement.
- **Semantic Navigation**: The agent utilizes Gemini to analyze page content and determine relevance to the user's objective, minimizing wasteful crawling.

### 2. High-Performance Fetching Engine (`src/fetching`)
- **Hybrid Strategy**: Implements a two-tier fetching system:
  - **Speed Tier**: Fast, async HTTP requests (httpx).
  - **Evasion Tier**: Headless browser automation (Playwright) for dynamic content and anti-bot measures.
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

### 5. Data Pipeline (`src/data`)
- **Validation**: Strict data validation using dynamically generated Pydantic schemas.
- **Export Formats**: Support for ML-ready exports including JSONL, CSV, and Parquet.
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
With the foundation and performance layers (Phase 1 & 2) largely in place, development shifts to advanced intelligence and scale:
- **Phase 3 (Intelligent Extraction)**: Enhancing visual-semantic understanding and integrating the ONNX inference engine (currently a stub).
- **Phase 4 (Scalability)**: Implementing the adaptive model distillation pipeline and distributed crawling capabilities.

## Implemented Phase Details

### Phase 1: Rust HPC (Completed)
- **Core Library**: `scram_hpc_rs` created and linked via PyO3.
- **Performance**: HTTP fetching offloaded to Rust using `reqwest`/`tokio` for high concurrency.
- **TLS**: `rustls` integration for consistent handshakes.

### Phase 2: Mirage Engine (MVP Completed)
- **Browser Automation**: Implemented `MirageBrowser` in Rust using `chromiumoxide` (Chrome DevTools Protocol).
- **Stealth**: Integrated "Behavioral Synthesis" (jitter, random delays) to mimic human activity.
- **Hybrid Fetching**: Agent successfully escalates from HTTP to Mirage Browser when blocked.
