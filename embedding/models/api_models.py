"""
API request and response models.
All Pydantic models used for FastAPI endpoints.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Request model for question answering."""
    question: str = Field(..., description="Question to ask the RAG system")
    top_k: Optional[int] = Field(5, description="Number of top results to return")
    threshold: Optional[float] = Field(0.25, description="Similarity threshold")


class QuestionResponse(BaseModel):
    """Response model for question answering."""
    answer: str
    sources: List[str]
    response_time: float
    chunks_used: int
    fallback_used: bool = False
    timestamp: datetime


class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(..., description="Search query")
    top_k: Optional[int] = Field(5, description="Number of top results to return")
    threshold: Optional[float] = Field(0.25, description="Similarity threshold")


class SearchResultModel(BaseModel):
    """Individual search result."""
    content: str
    source: str
    score: float
    rank: int


class SearchResponse(BaseModel):
    """Response model for search results."""
    results: List[SearchResultModel]
    query: str
    response_time: float
    timestamp: datetime


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    filename: str
    status: str  # "queued", "duplicate", "error"
    message: str
    doc_id: Optional[str] = None
    task_id: Optional[str] = None
    timestamp: datetime


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    doc_id: str
    status: str  # "pending", "processing", "completed", "failed"
    created_at: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class FileCategoryResponse(BaseModel):
    """Response model for file category retrieval."""
    doc_id: str
    category: str
    cluster_id: Optional[int] = None
    filename: str
    status: str


class ProcessingStatus(BaseModel):
    """System processing status."""
    status: str
    documents: int
    chunks: int
    processing_time: Optional[float] = None
    ready: bool
    loaded_from_cache: bool = False
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    ready: bool
    documents_loaded: int
    chunks_available: int
    timestamp: datetime


