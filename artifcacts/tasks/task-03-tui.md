# Task 03: Terminal User Interface (TUI)

## Goal
Create a professional, interactive TUI using Textual to control the agent and visualize data.

## Requirements

### 1. Architecture
- **Threading**: Run the LangGraph agent in a separate thread/process to avoid blocking the UI.
- **Communication**: Use thread-safe queues (`queue.Queue`) to pass messages (logs, stats, data) between Agent and TUI.

### 2. Screens
- **Setup Screen**:
  - Inputs for Session Title, Target URLs, and Objective.
- **Schema Confirmation**:
  - Display generated schema (Code widget).
  - Allow editing/confirmation.
- **Crawling Dashboard**:
  - **Stats Panel**: URLs processed, speed, success rate.
  - **Log Panel**: Real-time agent activity.
  - **Live Feed**: Preview of extracted items.
- **Review Modal**:
  - DataTable to show sample data.
  - Buttons: Approve, Refine, Discard.
- **Export Screen**:
  - Format selection (JSONL, CSV, Parquet).

## Definition of Done
- TUI application launches and navigates between screens.
- Can start the Agent thread and receive updates.
- Dashboard updates in real-time.
- User input is correctly passed to the Agent.
