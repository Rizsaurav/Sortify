#!/usr/bin/env python3
"""
Upload and task queue management routes for Sortify.
Handles file uploads, task status tracking, and category retrieval.
"""

import logging
import uuid
import io
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from task_queue import task_queue, TaskStatus

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/upload",
    tags=["uploads"],
    responses={404: {"description": "Not found"}},
)

# Pydantic models
class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    doc_id: Optional[str] = None
    task_id: Optional[str] = None
    timestamp: datetime

class TaskStatusResponse(BaseModel):
    task_id: str
    doc_id: str
    status: str
    created_at: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

class FileCategoryResponse(BaseModel):
    doc_id: str
    category: str
    cluster_id: Optional[int] = None
    filename: str
    status: str


# Dependencies (will be injected from main app)
_rag_service = None
_sorter = None


def set_dependencies(rag_service, sorter):
    """Set dependencies for the router"""
    global _rag_service, _sorter
    _rag_service = rag_service
    _sorter = sorter
