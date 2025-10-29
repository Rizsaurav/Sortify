"""
Domain models for business logic.
Dataclasses and domain entities used throughout the application.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import numpy as np


class TaskStatus(str, Enum):
    """Task processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Category:
    """Document category/cluster."""
    id: int
    label: str
    centroid: np.ndarray
    doc_count: int
    user_id: str
    created_at: str
    updated_at: Optional[str] = None
    keywords: Optional[list] = None


@dataclass
class Chunk:
    """Document chunk with embedding."""
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    embedding: np.ndarray
    word_count: int
    char_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkedDocument:
    """Document that has been chunked."""
    document_id: str
    filename: str
    total_chunks: int
    content_hash: str
    chunks: Optional[list] = None


@dataclass
class Document:
    """Full document entity."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    cluster_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class TaskInfo:
    """Task queue information."""
    task_id: str
    doc_id: str
    user_id: str
    content: str
    status: TaskStatus
    created_at: datetime
    category_id: Optional[int] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

