"""
Centralized configuration management.
Loads and validates environment variables, provides typed configuration objects.
"""

import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        """Load and validate settings from environment."""
        # Supabase Configuration
        self.supabase_url = self._get_required('SUPABASE_URL')
        self.supabase_key = self._get_required('SUPABASE_KEY')
        
        # Google Gemini API
        self.google_api_key = self._get_required('GOOGLE_API_KEY')
        
        # Embedding Model Configuration
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'Qwen/Qwen3-Embedding-0.6B')
        self.embedding_dimension = int(os.getenv('EMBEDDING_DIMENSION', '1024'))
        self.rag_embedding_model = os.getenv('RAG_EMBEDDING_MODEL', 'all-mpnet-base-v2')
        
        # Chunking Configuration (token-based)
        # chunk_size: Maximum tokens per chunk (1000 tokens for better semantic coherence)
        # chunk_overlap: 20% overlap for improved context continuity
        # min_chunk_size_tokens: Minimum tokens for a valid chunk (prevents tiny chunks)
        # use_semantic_chunking: Enable semantic boundary detection (topic shifts, headings)
        # topic_shift_threshold: Similarity threshold for detecting topic changes (0.0-1.0)
        # use_hierarchical_chunking: Enable parent-child chunk structure
        # parent_chunk_size: Size for parent chunks (broader context)
        # child_chunk_size: Size for child chunks (precise retrieval)
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '1000'))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '200'))  # 20% of chunk_size
        self.min_chunk_size_tokens = int(os.getenv('MIN_CHUNK_SIZE_TOKENS', '50'))
        self.use_semantic_chunking = os.getenv('USE_SEMANTIC_CHUNKING', 'true').lower() == 'true'
        self.topic_shift_threshold = float(os.getenv('TOPIC_SHIFT_THRESHOLD', '0.5'))
        self.use_hierarchical_chunking = os.getenv('USE_HIERARCHICAL_CHUNKING', 'false').lower() == 'true'
        self.parent_chunk_size = int(os.getenv('PARENT_CHUNK_SIZE', '2000'))
        self.child_chunk_size = int(os.getenv('CHILD_CHUNK_SIZE', '1000'))
        
        # Categorization Configuration
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.45'))  # Lowered for better semantic matching
        self.max_categories = int(os.getenv('MAX_CATEGORIES', '15'))  # Reduced from 30
        
        # Standard Categories for Students - BROAD TOPICS
        self.standard_categories = [
            'Academic Work',      # Assignments, homework, projects, essays
            'Course Materials',   # Lectures, notes, slides, textbooks
            'Research & Papers',   # Research papers, articles, studies
            'Science & Tech',      # CS, engineering, physics, chemistry, biology
            'Mathematics',        # Math, statistics, calculations
            'Business & Finance',  # Business, economics, finance, management
            'Language & Arts',     # Literature, writing, languages, arts
            'Health & Medicine',   # Medical, health, anatomy, physiology
            'Social Sciences',     # Psychology, sociology, history, politics
            'Professional Documents', # Cover letters, resumes, job applications
            'General Documents'   # Everything else
        ]
        
        # RAG Configuration
        self.rag_top_k = int(os.getenv('RAG_TOP_K', '8'))
        self.rag_similarity_threshold = float(os.getenv('RAG_SIMILARITY_THRESHOLD', '0.45'))
        
        # API Configuration
        self.api_version = os.getenv('API_VERSION', '1.0.0')
        cors_origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000,http://localhost:3001')
        self.cors_origins = [origin.strip() for origin in cors_origins_str.split(',')]
        
        # Processing Configuration
        self.batch_size = int(os.getenv('BATCH_SIZE', '32'))
        self.cache_ttl_seconds = int(os.getenv('CACHE_TTL_SECONDS', '300'))
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    def _get_required(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"{key} is required but not set in environment variables")
        return value


class ModelConfig:
    """Model-specific configuration."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    @property
    def embedding_model_name(self) -> str:
        return self.settings.embedding_model
    
    @property
    def embedding_dim(self) -> int:
        return self.settings.embedding_dimension
    
    @property
    def device(self) -> str:
        """Determine device for model inference."""
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"


class DatabaseConfig:
    """Database-specific configuration."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    @property
    def url(self) -> str:
        return self.settings.supabase_url
    
    @property
    def key(self) -> str:
        return self.settings.supabase_key


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_model_config() -> ModelConfig:
    """Get model configuration."""
    return ModelConfig(get_settings())


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return DatabaseConfig(get_settings())

