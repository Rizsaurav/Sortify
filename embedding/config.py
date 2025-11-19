#!/usr/bin/env python3
"""
Configuration management for RAG system.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class RAGConfig:
    """Configuration for RAG system."""
    
    # API Keys
    google_api_key: str
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    
    # Model Configuration
    embedding_model_name: str = "all-mpnet-base-v2"  # Default: all-mpnet-base-v2
    llm_model_name: str = "gemini-1.5-flash"  # Gemini API model
    
    # Processing Configuration
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_workers: int = 4
    batch_size: int = 32
    
    # Storage Configuration
    documents_dir: str = "./docs"
    embeddings_storage_path: str = "./storage"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Search Configuration
    default_top_k: int = 5
    similarity_threshold: float = 0.2  # Balanced threshold for relevance filtering
    
    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """Create configuration from environment variables."""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        return cls(
            google_api_key=google_api_key,
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "all-mpnet-base-v2"),
            llm_model_name=os.getenv("LLM_MODEL_NAME", "gemini-1.5-flash"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
            batch_size=int(os.getenv("BATCH_SIZE", "32")),
            documents_dir=os.getenv("DOCUMENTS_DIR", "./docs"),
            embeddings_storage_path=os.getenv("EMBEDDINGS_STORAGE_PATH", "./storage"),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            default_top_k=int(os.getenv("DEFAULT_TOP_K", "5")),
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.2"))
        )
    
    def validate(self) -> None:
        """Validate configuration."""
        if not self.google_api_key:
            raise ValueError("Google API key is required")
        
        # Create directories if they don't exist
        Path(self.documents_dir).mkdir(parents=True, exist_ok=True)
        Path(self.embeddings_storage_path).mkdir(parents=True, exist_ok=True)

# Global configuration instance
config = RAGConfig.from_env()
