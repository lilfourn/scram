# Task 04: Data Pipeline & Export

## Goal
Ensure extracted data is clean, validated, and exported in ML-ready formats.

## Requirements

### 1. Data Pipeline
- **Validation**: Ensure all data passes Pydantic validation (already handled in Extractor, but double-check).
- **Deduplication**: Remove duplicates based on unique keys.
- **Normalization**: Standardize formats (dates to ISO, numbers, etc.).

### 2. Export Logic
Implement export functionality using Pandas/Polars:
- **JSONL**: `df.to_json(lines=True)`
- **CSV**: `df.to_csv()`
- **Parquet**: `df.to_parquet()`
- **SQLite**: Save to local DB.

### 3. Persistence
- Create session directory: `scram/{session_title}/`.
- Save `config.json` (Objective, Schema, Metadata).
- Save `logs/`.
- Save `data/` (Exported files).

## Definition of Done
- Data can be exported to all supported formats.
- Directory structure is correctly created.
- Deduplication logic works.
- Full end-to-end test: Scrape -> Extract -> Export.
