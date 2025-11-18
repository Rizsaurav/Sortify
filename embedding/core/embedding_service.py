import os
import asyncio
import time
import numpy as np
from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer
from utils import get_logger
from config import get_model_config

logger = get_logger(__name__)

# Optional small optimization
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class EmbeddingService:
    """
    Async embedding generator using local Qwen3 Embedding model.
    Maintains EXACT same interface as your previous EmbeddingService.
    """

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        config = get_model_config()
        self.model_name = model_name or "Qwen/Qwen3-Embedding-0.6B"
        self.device = device or config.device or "cpu"

        try:
            logger.info(f"Loading Qwen embedding model: {self.model_name} on {self.device}")

            # Load WITHOUT flash-attn (critical!)
            self.model = SentenceTransformer(
                self.model_name,
                # Force safe default. No FA2.
                model_kwargs={"attn_implementation": "eager"},
                tokenizer_kwargs={"padding_side": "left"},
            )

            # Move to device
            self.model.to(self.device)

            # Get actual dimension
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

            logger.info(
                f"✓ Qwen3 Embedding loaded ({self.embedding_dim} dim) using {self.device}"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to load Qwen embedding model: {e}")

    # ------------------------------------------------------------
    # Core embedding
    # ------------------------------------------------------------
    async def generate_embeddings(
        self,
        texts: Union[str, List[Union[str, dict]]],
        batch_size: int = 8,
        normalize: bool = True,
        is_query: bool = False,
    ) -> np.ndarray:

        if isinstance(texts, str):
            texts = [texts]

        processed = []
        for t in texts:
            text = t["content"] if isinstance(t, dict) else t
            text = (text or "").strip()

            # Qwen recommends using built-in query prefix prompt
            if is_query:
                processed.append(text)
            else:
                processed.append(text)

        start = time.time()

        try:
            embeddings = await asyncio.to_thread(
                self.model.encode,
                processed,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=normalize,
                convert_to_numpy=True,
                prompt_name="query" if is_query else None,
            )

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError("Embedding generation failed")

        logger.info(
            f"✓ Embedded {len(processed)} texts in {time.time() - start:.2f}s"
        )

        return embeddings

    # ------------------------------------------------------------
    # Helpers (unchanged)
    # ------------------------------------------------------------
    def to_float_list(self, embeddings: np.ndarray) -> List[List[float]]:
        if embeddings.ndim == 1:
            return embeddings.astype(float).tolist()
        return [row.astype(float).tolist() for row in embeddings]

    async def generate_query_embedding(self, query: str) -> np.ndarray:
        emb = await self.generate_embeddings([query], is_query=True)
        return emb[0]

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


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Preserve exact old API."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
