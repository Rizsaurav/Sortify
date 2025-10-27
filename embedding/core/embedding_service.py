"""
Embedding service - Single responsibility: Generate embeddings from text.
Handles all embedding model loading and inference with memory pooling.
"""

import numpy as np
from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer
import sys
import os

# Add parent directory to path for memory_pool import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_logger
from config import get_settings, get_model_config
from memory_pool import get_memory_pool

logger = get_logger(__name__)


class EmbeddingService:

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        use_memory_pool: bool = True
    ):
        config = get_model_config()

        self.model_name = model_name or config.embedding_model_name
        self.device = device or config.device
        self.embedding_dim = config.embedding_dim
        self.use_memory_pool = use_memory_pool

        logger.info(f"Loading embedding model: {self.model_name} on device: {self.device}")

        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"✓ Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

        # Initialize memory pool
        if self.use_memory_pool:
            self.memory_pool = get_memory_pool(buffer_size=self.embedding_dim, initial_buffers=5)
            logger.info("✓ Memory pool initialized for embedding service")
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True,
        use_instruction: bool = False,
        instruction_prompt: str = "query"
    ) -> np.ndarray:
        
        try:
            # Handle single text
            is_single = isinstance(texts, str)
            if is_single:
                texts = [texts]
            
            # Prepare prompt if needed
            if use_instruction and hasattr(self.model, 'prompts'):
                # Qwen3-Embedding supports instruction prompts
                processed_texts = [f"{instruction_prompt}: {text}" for text in texts]
            else:
                processed_texts = texts
            
            # Generate embeddings
            embeddings = self.model.encode(
                processed_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=normalize,
                convert_to_numpy=True
            )
            
            # Return single embedding if input was single text
            if is_single:
                return embeddings[0]
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def encode_query(self, query: str) -> np.ndarray:
        return self.encode(query, use_instruction=True, instruction_prompt="query")
    
    def encode_document(self, document: str) -> np.ndarray:
        return self.encode(document, use_instruction=False)
    
    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        return self.encode(
            texts,
            batch_size=batch_size,
            show_progress=show_progress
        )
    
    def get_dimension(self) -> int:
        return self.embedding_dim
    
    def get_model_info(self) -> dict:
        info = {
            "model_name": self.model_name,
            "dimension": self.embedding_dim,
            "device": self.device,
            "max_seq_length": getattr(self.model, 'max_seq_length', 'unknown')
        }
        if self.use_memory_pool:
            info["memory_pool"] = self.memory_pool.get_stats()
        return info


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service