# Project Scram: Technical Specifications

## 1. Introduction

**Project Name:** Scram
**Objective:** To develop an intelligent, high-performance, terminal-based web crawling agent designed to extract structured, machine-learning-ready data at scale. It utilizes LLMs (Gemini) for intelligent navigation and extraction, features advanced anti-bot evasion, and operates via a professional Terminal User Interface (TUI).

## 2. Core Requirements

### 2.1. Performance & Concurrency
*   **Target:** Achieve processing speeds (fetching and analyzing) exceeding 1000 pages per minute.
*   **Implementation:** Must utilize Python's `asyncio` for high concurrency.

### 2.2. Data Quality
*   **Structure:** Output must be strictly structured and validated against a dynamically generated schema.
*   **ML-Ready:** Data must be clean, normalized, and ready for immediate use in ML pipelines.

### 2.3. Intelligence (AI)
*   **LLM:** Google Gemini.
*   **Navigation:** Agent must use semantic analysis of content to determine relevance to the user's objective, avoiding irrelevant crawls.
*   **Extraction:** Utilize LLM function calling/tool use for precise, structured data extraction from unstructured HTML.
*   **Adaptability:** Incorporate user feedback loops to refine the extraction schema in real-time.

### 2.4. Evasion & Resilience
*   **Anti-Bot:** Must actively bypass common bot mitigation systems (e.g., Cloudflare, Akamai).
*   **Strategy:** Implement a hybrid fetching strategy (HTTP client prioritized, escalating to headless browser when necessary).
*   **Techniques:** Utilize proxy rotation, TLS fingerprint spoofing, and stealth browser configurations.

### 2.5. User Interface
*   **Type:** Terminal User Interface (TUI).
*   **Features:** Interactive dashboard, real-time logging, data preview, and feedback modals.

## 3. Technology Stack

| Domain                 | Technologies                                                                    |
|------------------------|---------------------------------------------------------------------------------|
| **Core Language**      | Python (>= 3.10)                                                                |
| **AI Model**           | Google Gemini (via API)                                                         |
| **Agent Framework**    | LangGraph (built on LangChain)                                                  |
| **TUI Framework**      | Textual                                                                         |
| **Networking (Async)** | `asyncio`, `httpx` (Primary HTTP Client)                                        |
| **Evasion (TLS Spoofing)** | `curl_cffi`                                                                     |
| **Browser Automation** | `Playwright` (Asynchronous) with `playwright-stealth`                           |
| **Data Validation**    | Pydantic V2                                                                     |
| **Data Export**        | Pandas or Polars                                                                |

## 4. System Architecture

The architecture is modular, consisting of five primary services.

### 4.1. Agent Core (LangGraph Orchestrator)
*   Manages the global state of the scraping session (objective, schema, queue, results).
*   Defines the workflow as a state machine (Graph).
*   **Nodes:** Initialization, Crawl Manager, Fetcher, Relevance Analyzer (AI), Extractor (AI), Presenter (TUI interaction), Refinement (AI).

### 4.2. TUI Service (Textual)
*   Handles user input (URLs, Objective, Feedback).
*   Displays the dashboard, logs, and data previews.
*   Must run independently of the Agent Core (e.g., separate thread) and communicate via thread-safe queues to maintain responsiveness.

### 4.3. Fetching Engine
*   Manages the `asyncio.Queue` and concurrent workers.
*   Implements the Hybrid Fetching Strategy.
*   Integrates the Anti-Bot Evasion System.
*   Handles rate limiting (global and per-domain) and exponential backoff for retries.

### 4.4. Anti-Bot Evasion System
*   **Proxy Management:** Rotation of high-quality residential proxies.
*   **Fingerprinting:** TLS/JA3 fingerprint spoofing (via `curl_cffi`). Consistent HTTP header management.
*   **Browser Stealth:** Maintaining a pool of Playwright instances utilizing `playwright-stealth`.

### 4.5. AI Engine (Gemini Interface)
*   Handles all interactions with the Gemini API.
*   **Key Tasks:**
    *   Schema Generation (Objective -> Pydantic).
    *   Relevance Analysis (Semantic similarity between HTML and Objective).
    *   Structured Extraction (HTML + Pydantic Schema -> JSON Object) using Function Calling/Tool Use.

### 4.6. Data Pipeline
*   Validates extracted data using Pydantic.
*   Performs deduplication and normalization.
*   Handles conversion to DataFrame and export.

## 5. Data Management

### 5.1. Output Formats
*   JSON Lines (JSONL)
*   CSV
*   Parquet (Optimized for ML)
*   SQLite

### 5.2. Directory Structure
Session data will be saved in the user's root directory:
`scram/{scrape-session-title}/`
*   `data/` (Contains exported files)
*   `config.json` (Session metadata, objective, and final schema for reproducibility)
*   `logs/` (Detailed session logs)