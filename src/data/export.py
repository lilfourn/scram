import asyncio
import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.data.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class DataExporter:
    def __init__(self, base_dir: str = "scram_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.graph = KnowledgeGraph()
        self._lock = asyncio.Lock()

    def _get_session_dir(self, session_title: str) -> Path:
        # Sanitize title
        safe_title = (
            "".join(
                [
                    c if c.isalnum() or c in (" ", "-", "_") else "_"
                    for c in session_title
                ]
            )
            .strip()
            .replace(" ", "_")
        )
        session_dir = self.base_dir / safe_title
        session_dir.mkdir(exist_ok=True)
        (session_dir / "data").mkdir(exist_ok=True)
        (session_dir / "logs").mkdir(exist_ok=True)
        return session_dir

    def save_config(self, session_title: str, config_data: Dict[str, Any]):
        """Save session configuration and metadata."""
        session_dir = self._get_session_dir(session_title)
        try:
            with open(session_dir / "config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    async def save_batch(
        self,
        session_title: str,
        data: List[Dict[str, Any]],
        screenshots: List[bytes] = None,
    ):
        """Save a batch of data to raw storage (JSONL/CSV) immediately."""
        if not data:
            return

        session_dir = self._get_session_dir(session_title)
        data_dir = session_dir / "data"
        images_dir = session_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # Update Knowledge Graph & Save Screenshots
        # Note: Graph updates are in-memory and not async, but file writes need locking
        for i, item in enumerate(data):
            # Save screenshot if available
            screenshot_path = ""
            if screenshots and i < len(screenshots) and screenshots[i]:
                import hashlib

                # Use hash of content or ID for filename
                img_hash = hashlib.md5(screenshots[i]).hexdigest()
                img_filename = f"{img_hash}.png"
                img_path = images_dir / img_filename

                # Use lock for file writing
                async with self._lock:
                    with open(img_path, "wb") as f:
                        f.write(screenshots[i])
                screenshot_path = str(img_path)

                # Update metadata
                if "_metadata" not in item:
                    item["_metadata"] = {}
                item["_metadata"]["screenshot_path"] = screenshot_path

            # Infer entity type from schema or default to 'Entity'
            # For now, we assume flat items are entities
            entity_type = "Entity"
            # Try to guess type from keys
            if "product_name" in item or "price" in item:
                entity_type = "Product"
            elif "article_body" in item:
                entity_type = "Article"

            self.graph.add_entity(entity_type, item)

        # Append to JSONL (Raw storage)
        try:
            async with self._lock:
                with open(data_dir / "raw_data.jsonl", "a", encoding="utf-8") as f:
                    for item in data:
                        f.write(json.dumps(item) + "\n")
        except Exception as e:
            logger.error(f"Failed to save raw JSONL: {e}")

        # Append to CSV (Best effort for monitoring)
        try:
            filepath = data_dir / "raw_data.csv"
            file_exists = filepath.exists()

            # Use keys from the first item, but this might be unstable if schema changes
            # Ideally we use the schema, but for raw dump this is fine
            keys = list(data[0].keys())

            async with self._lock:
                with open(filepath, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    if not file_exists:
                        writer.writeheader()
                    for item in data:
                        # Handle missing keys safely
                        row = {k: item.get(k, "") for k in keys}
                        writer.writerow(row)
        except Exception as e:
            logger.error(f"Failed to save raw CSV: {e}")

    def finalize_session(self, session_title: str):
        """Read raw data, deduplicate, normalize, and export to all formats."""
        session_dir = self._get_session_dir(session_title)
        raw_jsonl = session_dir / "data" / "raw_data.jsonl"

        if not raw_jsonl.exists():
            logger.warning(f"No data found for session {session_title} to finalize.")
            return

        logger.info(f"Finalizing session: {session_title}")

        # Load Data
        try:
            df = pd.read_json(raw_jsonl, lines=True)
        except ValueError as e:
            logger.error(f"Failed to read JSONL data for finalization: {e}")
            return

        if df.empty:
            logger.info("Dataframe is empty.")
            return

        # Deduplicate
        # If 'url' column exists, use it as a key. Otherwise, drop exact duplicates.
        initial_count = len(df)

        # Handle unhashable types (like dicts in _metadata) before deduplication
        # We can convert dict columns to strings for the purpose of deduplication if needed,
        # or just exclude them from the subset if we are doing exact match.

        # If we have a primary key like 'url' or 'id', use that.
        subset = None
        if "url" in df.columns:
            subset = ["url"]
        elif "id" in df.columns:
            subset = ["id"]

        try:
            if subset:
                df = df.drop_duplicates(subset=subset)
            else:
                # If no clear key, we try to drop duplicates based on all columns.
                # But if we have dicts (like _metadata), this fails.
                # We can try to drop duplicates based on columns that are hashable.

                # Identify hashable columns
                hashable_cols = []
                for col in df.columns:
                    # Check first non-null value to see if it's a dict/list
                    sample = (
                        df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                    )
                    if not isinstance(sample, (dict, list)):
                        hashable_cols.append(col)

                if hashable_cols:
                    df = df.drop_duplicates(subset=hashable_cols)
                else:
                    # Fallback: Convert to string to deduplicate
                    # This is expensive but safe
                    df = df.loc[df.astype(str).drop_duplicates().index]

        except Exception as e:
            logger.warning(f"Deduplication failed: {e}. Proceeding with raw data.")

        logger.info(f"Deduplication: {initial_count} -> {len(df)} items")

        # Export Paths
        export_base = session_dir / "data" / "clean_data"

        # 1. JSONL
        try:
            df.to_json(str(export_base) + ".jsonl", orient="records", lines=True)
        except Exception as e:
            logger.error(f"Failed to export clean JSONL: {e}")

        # 2. CSV
        try:
            df.to_csv(str(export_base) + ".csv", index=False)
        except Exception as e:
            logger.error(f"Failed to export clean CSV: {e}")

        # 3. Parquet
        try:
            df.to_parquet(str(export_base) + ".parquet")
        except ImportError:
            logger.warning("PyArrow not installed. Skipping Parquet export.")
        except Exception as e:
            logger.error(f"Parquet export failed: {e}")

        # 4. SQLite
        try:
            db_path = session_dir / "data" / "database.sqlite"
            conn = sqlite3.connect(db_path)
            df.to_sql("extracted_data", conn, if_exists="replace", index=False)
            conn.close()
        except Exception as e:
            logger.error(f"SQLite export failed: {e}")

        # 5. Knowledge Graph (GraphML)
        try:
            graph_path = session_dir / "data" / "knowledge_graph.graphml"
            self.graph.export_graphml(str(graph_path))
        except Exception as e:
            logger.error(f"GraphML export failed: {e}")

        logger.info(f"Session finalized. Exports available in {session_dir}/data/")


# Global instance
exporter = DataExporter()
