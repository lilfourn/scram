import pytest
import pandas as pd
import json
import os
from unittest.mock import MagicMock, patch, AsyncMock
from src.data.export import DataExporter
from src.ai.embeddings import EmbeddingEngine


@pytest.mark.asyncio
async def test_structural_compression():
    exporter = DataExporter(":memory:")

    data = [
        {"id": 1, "name": "A", "val": 10},
        {"id": 2, "name": "B", "val": 20},
        {"id": 3, "name": "A", "val": 10},  # Duplicate values
    ]
    df = pd.DataFrame(data)

    filepath = "test_compressed.json"
    exporter._export_structural_compressed(df, filepath)

    assert os.path.exists(filepath)

    with open(filepath, "r") as f:
        loaded = json.load(f)

    assert "schema" in loaded
    assert "data" in loaded
    assert loaded["schema"]["columns"] == ["id", "name", "val"]
    assert len(loaded["data"]) == 3
    assert loaded["data"][0] == [1, "A", 10]

    os.remove(filepath)


@pytest.mark.asyncio
async def test_semantic_deduplication():
    engine = EmbeddingEngine()

    data = [
        {"title": "iPhone 13"},
        {"title": "Apple iPhone 13"},  # Semantic duplicate
        {"title": "Samsung Galaxy"},
    ]

    # Mock embeddings
    # iPhone 13 -> [1, 0]
    # Apple iPhone 13 -> [0.99, 0.01] (High similarity)
    # Samsung -> [0, 1]

    with patch.object(
        engine, "generate_embeddings", new_callable=AsyncMock
    ) as mock_embed:
        mock_embed.return_value = [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]]

        deduped = await engine.deduplicate_semantically(data, threshold=0.9)

        assert len(deduped) == 2
        assert deduped[0]["title"] == "iPhone 13"
        assert deduped[1]["title"] == "Samsung Galaxy"


@pytest.mark.asyncio
async def test_finalize_session_integration():
    exporter = DataExporter("test_data")

    # Create dummy raw data
    session_title = "Test Session"
    session_dir = exporter._get_session_dir(session_title)
    (session_dir / "data").mkdir(parents=True, exist_ok=True)

    raw_data = [
        {"id": 1, "title": "A"},
        {"id": 1, "title": "A"},  # Exact duplicate
        {"id": 2, "title": "B"},
    ]

    with open(session_dir / "data" / "raw_data.jsonl", "w") as f:
        for item in raw_data:
            f.write(json.dumps(item) + "\n")

    # Mock semantic deduplication to do nothing (pass through)
    with patch(
        "src.ai.embeddings.embedding_engine.deduplicate_semantically",
        new_callable=AsyncMock,
    ) as mock_dedup:
        mock_dedup.side_effect = lambda data, **kwargs: data

        await exporter.finalize_session(session_title)

        # Check if clean data exists
        clean_jsonl = session_dir / "data" / "clean_data.jsonl"
        assert clean_jsonl.exists()

        df = pd.read_json(clean_jsonl, lines=True)
        # Exact deduplication should have happened
        assert len(df) == 2
        assert 1 in df["id"].values
        assert 2 in df["id"].values

    # Cleanup
    import shutil

    shutil.rmtree("test_data")
