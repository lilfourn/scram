import sqlite3
import hashlib
import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, db_path: str = "scram_data/cache.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._init_db()

    def _connect(self):
        """Establish database connection."""
        if self.db_path != ":memory:":
            path = Path(self.db_path)
            path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def _init_db(self):
        """Initialize the cache database."""
        try:
            with self.conn:
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS http_cache (
                        url TEXT PRIMARY KEY,
                        etag TEXT,
                        last_modified TEXT,
                        content_hash TEXT,
                        timestamp REAL,
                        content TEXT
                    )
                """
                )
        except Exception as e:
            logger.error(f"Failed to initialize cache DB: {e}")

    def get_entry(self, url: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cache entry for a URL."""
        try:
            cursor = self.conn.execute("SELECT * FROM http_cache WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error(f"Cache read error for {url}: {e}")
        return None

    def update_entry(
        self,
        url: str,
        content: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ):
        """Update or insert a cache entry."""
        try:
            # Calculate content hash
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

            with self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO http_cache 
                    (url, etag, last_modified, content_hash, timestamp, content)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (url, etag, last_modified, content_hash, time.time(), content),
                )
        except Exception as e:
            logger.error(f"Cache write error for {url}: {e}")

    def get_content_hash(self, content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def close(self):
        if self.conn:
            self.conn.close()
