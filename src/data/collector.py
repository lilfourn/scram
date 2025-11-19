import json
import aiofiles
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RawDataCollector:
    def __init__(self):
        self.file_path = None

    def set_session(self, session_title: str):
        """Initialize the raw data file for the session."""
        # Sanitize title for filename
        safe_title = (
            "".join([c for c in session_title if c.isalnum() or c in (" ", "-", "_")])
            .strip()
            .replace(" ", "_")
        )
        self.file_path = f"data/raw_{safe_title}.jsonl"
        # Ensure directory exists
        os.makedirs("data", exist_ok=True)
        logger.info(f"Raw data collector initialized at {self.file_path}")

    async def save(self, data: List[Dict[str, Any]]):
        """Append raw data to the file."""
        if not self.file_path:
            logger.warning("RawDataCollector not initialized with a session.")
            return

        try:
            async with aiofiles.open(self.file_path, mode="a") as f:
                for item in data:
                    await f.write(json.dumps(item) + "\n")
        except Exception as e:
            logger.error(f"Failed to save raw data: {e}")

    async def load_all(self) -> List[Dict[str, Any]]:
        """Load all raw data for processing."""
        if not self.file_path or not os.path.exists(self.file_path):
            return []

        data = []
        try:
            async with aiofiles.open(self.file_path, mode="r") as f:
                async for line in f:
                    if line.strip():
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Failed to load raw data: {e}")
        return data

    def cleanup(self):
        """Delete the raw data file."""
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
                logger.info(f"Deleted raw data file: {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to delete raw data file: {e}")


# Global instance
collector = RawDataCollector()
