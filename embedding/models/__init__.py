"""
Data models and schemas for the Sortify application.
Centralized location for all Pydantic models, dataclasses, and type definitions.
"""

from .api_models import (
    QuestionRequest,
    QuestionResponse,
    SearchRequest,
    SearchResponse,
    SearchResultModel,
    DocumentUploadResponse,
    TaskStatusResponse,
    FileCategoryResponse,
    ProcessingStatus,
    HealthResponse,
)

from .domain_models import (
    Category,
    Chunk,
    ChunkedDocument,
    Document,
    TaskInfo,
    TaskStatus,
)

__all__ = [
    # API Models
    "QuestionRequest",
    "QuestionResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultModel",
    "DocumentUploadResponse",
    "TaskStatusResponse",
    "FileCategoryResponse",
    "ProcessingStatus",
    "HealthResponse",
    # Domain Models
    "Category",
    "Chunk",
    "ChunkedDocument",
    "Document",
    "TaskInfo",
    "TaskStatus",
]

