import asyncio
import numpy as np
from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer
from utils import get_logger
from config import get_model_config

logger = get_logger(__name__)


class EmbeddingService:
    """Async embedding generator using SentenceTransformer."""

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        config = get_model_config()
        self.model_name = model_name or config.embedding_model_name
        self.device = device or config.device

        try:
            self.model = SentenceTransformer(self.model_name)
            self.model.to(self.device)

            # ALWAYS get real dimension from model
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

            logger.info(f"✓ Loaded embedding model: {self.model_name} ({self.embedding_dim} dim)")
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model {self.model_name}: {e}")

    async def generate_embeddings(
        self,
        texts: Union[str, List[Union[str, dict]]],
        batch_size: int = 32,
        normalize: bool = True,
        is_query: bool = False,
    ) -> np.ndarray:
        """Generate embeddings asynchronously."""
        if isinstance(texts, str):
            texts = [texts]

        processed = []
        for t in texts:
            text = t["content"] if isinstance(t, dict) else t
            text = text.strip()
            prefix = "query:" if is_query else "passage:"
            processed.append(f"{prefix} {text}")

        try:
            embeddings = await asyncio.to_thread(
                self.model.encode,
                processed,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=normalize,
                convert_to_numpy=True,
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError("Embedding generation failed")

        # Safety normalization
        if normalize:
            embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)

        return embeddings

    def to_float_list(self, embeddings: np.ndarray) -> List[List[float]]:
        """Convert numpy embeddings to a Python list for pgvector."""
        if embeddings.ndim == 1:
            return embeddings.astype(float).tolist()
        return [e.astype(float).tolist() for e in embeddings]

    async def generate_query_embedding(self, query: str) -> np.ndarray:
        result = await self.generate_embeddings([query], is_query=True)
        return result[0]

    async def generate_document_embeddings(self, texts: List[str]) -> np.ndarray:
        return await self.generate_embeddings(texts, is_query=False)

    def get_dimension(self) -> int:
        return self.embedding_dim

    def get_model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "dimension": self.embedding_dim,
            "device": self.device,
            "max_seq_length": getattr(self.model, "max_seq_length", "unknown"),
        }


# Singleton
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
