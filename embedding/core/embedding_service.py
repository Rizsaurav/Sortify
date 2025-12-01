"""
Embedding service - Single responsibility: Generate embeddings from text.
Handles all embedding model loading and inference.
Optimized for BGE-M3 with support for instruction-based embeddings.
"""

import numpy as np
from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer

from utils import get_logger
from settings import get_settings, get_model_config

logger = get_logger(__name__)


class EmbeddingService:
    """
    Embedding service using BGE-M3 for high-quality semantic embeddings.

    BGE-M3 Features:
    - 1024-dimensional embeddings
    - Multilingual support (100+ languages)
    - Optimized for academic and technical content
    - Instruction-based query/passage encoding
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None
    ):
        config = get_model_config()

        self.model_name = model_name or config.embedding_model_name
        self.device = device or config.device
        self.embedding_dim = config.embedding_dim

        logger.info(f"Loading embedding model: {self.model_name} on device: {self.device}")

        try:
            # Load BGE-M3 with optimized settings
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                trust_remote_code=True
            )

            # Verify embedding dimension matches expected
            test_embedding = self.model.encode("test", convert_to_numpy=True)
            actual_dim = test_embedding.shape[0] if test_embedding.ndim == 1 else test_embedding.shape[1]

            if actual_dim != self.embedding_dim:
                logger.warning(f"Model dimension ({actual_dim}) differs from config ({self.embedding_dim}). Updating config.")
                self.embedding_dim = actual_dim

            logger.info(f"✓ Embedding model loaded successfully (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True,
        use_instruction: bool = False,
        instruction_prompt: str = "Represent this document for retrieval"
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings using BGE-M3.

        Args:
            texts: Single text or list of texts to embed
            batch_size: Batch size for processing
            show_progress: Show progress bar
            normalize: Normalize embeddings to unit length
            use_instruction: Prepend instruction for query encoding
            instruction_prompt: Instruction to use (BGE-M3 specific)

        Returns:
            Embedding vector(s) as a **Python list** of floats/lists, ensuring
            **JSON serialization compatibility** for database storage.
        """
        try:
            # Handle single text
            is_single = isinstance(texts, str)
            if is_single:
                texts = [texts]

            # BGE-M3 instruction format
            if use_instruction:
                processed_texts = [f"{instruction_prompt}: {text}" for text in texts]
            else:
                processed_texts = texts

            # Generate embeddings as np.ndarray for optimal performance
            embeddings = self.model.encode(
                processed_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=normalize,
                convert_to_numpy=True
            )
            
            # Convert NumPy array to standard Python list for database insertion.
            # This resolves the 'Object of type ndarray is not JSON serializable' error.
            embeddings_list = embeddings.tolist()

            # Return single embedding if input was single text
            if is_single:
                return embeddings_list[0]

            return embeddings_list

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def encode_query(self, query: str) -> List[float]:
        """
        Encode a search query using BGE-M3 query instruction.
        Returns a serializable Python list of floats.
        """
        return self.encode(
            query,
            use_instruction=True,
            instruction_prompt="Represent this sentence for searching relevant passages"
        )

    def encode_document(self, document: str) -> List[float]:
        """
        Encode a document using BGE-M3 (no instruction).
        Returns a serializable Python list of floats.
        """
        return self.encode(document, use_instruction=False)
    
    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Encodes a batch of texts.
        Returns a serializable Python list of lists of floats.
        """
        return self.encode(
            texts,
            batch_size=batch_size,
            show_progress=show_progress
        )
    
    def get_dimension(self) -> int:
        return self.embedding_dim
    
    def get_model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "dimension": self.embedding_dim,
            "device": self.device,
            "max_seq_length": getattr(self.model, 'max_seq_length', 'unknown')
        }


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service