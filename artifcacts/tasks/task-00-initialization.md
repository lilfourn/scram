# Task 00: Project Initialization & Core Architecture

## Goal
Establish the project foundation, directory structure, and core dependencies to support high concurrency, AI integration, and the TUI.

## Requirements

### 1. Technology Stack Setup
- **Python Version**: Ensure Python 3.10+ is used.
- **Dependency Management**: Set up `pyproject.toml` (using Poetry or standard pip/venv).
- **Core Dependencies**:
  - `asyncio` (Standard lib)
  - `httpx` (Async HTTP)
  - `curl_cffi` (TLS Spoofing)
  - `playwright` & `playwright-stealth` (Browser Automation)
  - `langgraph` & `langchain` (Agent Framework)
  - `textual` (TUI)
  - `pydantic` (Data Validation - V2)
  - `pandas` or `polars` (Data Manipulation)
  - `google-generativeai` (Gemini API)

### 2. Directory Structure
Create a modular architecture:
```
scram/
├── src/
│   ├── core/          # Configuration, Logging, Utils
│   ├── agent/         # LangGraph Orchestrator
│   ├── tui/           # Textual Interface
│   ├── fetching/      # HTTP & Browser Engine
│   ├── ai/            # Gemini Interface
│   └── data/          # Pipeline & Export
├── tests/
├── artifcacts/        # Docs & Tasks
└── main.py            # Entry point
```

### 3. Scaffolding
- Create the `main.py` entry point.
- Configure logging (async-compatible).
- Set up environment variable handling (API keys for Gemini).

## Definition of Done
- Project environment is active with all dependencies installed.
- Directory structure is created.
- `main.py` runs without errors (even if it just prints "Hello Scram").
- `pytest` is configured and running.
