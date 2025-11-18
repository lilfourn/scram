import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.export import DataExporter


class TestDataExporter:
    @pytest.fixture
    def exporter(self):
        self.temp_dir = tempfile.mkdtemp()
        exporter = DataExporter(base_dir=self.temp_dir)
        yield exporter
        shutil.rmtree(self.temp_dir)

    def test_save_config(self, exporter):
        session_title = "Test Session"
        config = {"objective": "Test", "schema": {}}
        exporter.save_config(session_title, config)

        session_dir = Path(self.temp_dir) / "Test_Session"
        assert session_dir.exists()
        assert (session_dir / "config.json").exists()

        with open(session_dir / "config.json") as f:
            loaded = json.load(f)
        assert loaded["objective"] == "Test"

    @pytest.mark.asyncio
    async def test_save_batch(self, exporter):
        session_title = "Test Session"
        data = [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]
        await exporter.save_batch(session_title, data)

        session_dir = Path(self.temp_dir) / "Test_Session"
        data_dir = session_dir / "data"
        assert (data_dir / "raw_data.jsonl").exists()
        assert (data_dir / "raw_data.csv").exists()

        # Check JSONL content
        with open(data_dir / "raw_data.jsonl") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == 1

    @pytest.mark.asyncio
    async def test_finalize_session(self, exporter):
        session_title = "Test Session"
        # Save duplicates to test deduplication
        data1 = [{"url": "http://a.com", "val": "a"}]
        data2 = [{"url": "http://a.com", "val": "a"}]  # Duplicate
        data3 = [{"url": "http://b.com", "val": "b"}]

        await exporter.save_batch(session_title, data1)
        await exporter.save_batch(session_title, data2)
        await exporter.save_batch(session_title, data3)

        exporter.finalize_session(session_title)

        session_dir = Path(self.temp_dir) / "Test_Session"
        clean_dir = session_dir / "data"

        # Check Clean JSONL
        clean_jsonl = clean_dir / "clean_data.jsonl"
        assert clean_jsonl.exists()
        df = pd.read_json(clean_jsonl, lines=True)
        assert len(df) == 2  # Should be 2 unique items
        assert "http://a.com" in df["url"].values
        assert "http://b.com" in df["url"].values

        # Check SQLite
        db_path = clean_dir / "database.sqlite"
        assert db_path.exists()
        conn = sqlite3.connect(db_path)
        df_sql = pd.read_sql("SELECT * FROM extracted_data", conn)
        conn.close()
        assert len(df_sql) == 2
