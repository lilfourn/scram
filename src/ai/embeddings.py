import logging
import os
from typing import List, Dict, Any
import google.generativeai as genai
from src.core.config import config
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY not found. Embeddings will fail.")

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not self.api_key or not texts:
            return []

        try:
            # Gemini embedding model
            model = "models/embedding-001"

            # Batch processing if needed (Gemini has limits)
            # For now, we assume small batches or handle it simply
            result = genai.embed_content(
                model=model,
                content=texts,
                task_type="clustering",
            )

            if "embedding" in result:
                return [result["embedding"]]  # Single result
            elif "embeddings" in result:
                return result["embeddings"]  # Batch result

            return []
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return []

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(v1)
        vec2 = np.array(v2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    async def deduplicate_semantically(
        self, data: List[Dict[str, Any]], threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate items based on semantic similarity of their string representation.
        """
        if not data:
            return []

        # Create string representations
        # We focus on values, ignoring metadata
        texts = []
        for item in data:
            # Filter out metadata and sort keys for stability
            content = " ".join(
                str(v)
                for k, v in sorted(item.items())
                if k != "_metadata" and v is not None
            )
            texts.append(content)

        embeddings = await self.generate_embeddings(texts)

        if not embeddings or len(embeddings) != len(data):
            logger.warning(
                "Embedding generation failed or mismatch. Skipping semantic deduplication."
            )
            return data

        unique_indices = []
        seen_vectors = []

        for i, vec in enumerate(embeddings):
            is_duplicate = False
            for seen_vec in seen_vectors:
                sim = self.cosine_similarity(vec, seen_vec)
                if sim > threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_indices.append(i)
                seen_vectors.append(vec)

        logger.info(
            f"Semantic Deduplication: {len(data)} -> {len(unique_indices)} items"
        )
        return [data[i] for i in unique_indices]


# Global instance
embedding_engine = EmbeddingEngine()
