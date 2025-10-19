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

@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload a document and queue it for categorization.
    Returns immediately without waiting for ML processing.
    """
    try:
        # Read content
        content_bytes = await file.read()
        
        # Extract content based on type
        if file.content_type and file.content_type.startswith('text/'):
            content_str = content_bytes.decode("utf-8", errors="ignore")
            
        elif file.content_type == 'application/pdf':
            try:
                from pypdf import PdfReader
                pdf_file = io.BytesIO(content_bytes)
                reader = PdfReader(pdf_file)
                text_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
                content_str = "\n\n".join(text_pages)
                if not content_str.strip():
                    content_str = f"PDF: {file.filename} (no extractable text)"
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                content_str = f"PDF: {file.filename} (extraction failed: {str(e)})"
                
        elif file.content_type and file.content_type.startswith('image/'):
            content_str = f"Image: {file.filename}\nType: {file.content_type}\nSize: {len(content_bytes)} bytes"
            
        else:
            content_str = f"File: {file.filename}\nType: {file.content_type or 'unknown'}"
        
        # Insert to Supabase WITHOUT waiting for categorization
        insert_response = _rag_service.supabase.table('documents').insert({
            'content': content_str,
            'metadata': {
                'user_id': user_id,
                'filename': file.filename,
                'type': file.content_type,
                'size': len(content_bytes)
            },
            'embedding': None,
            'cluster_id': None  # Will be updated by background task
        }).execute()
        
        doc_id = insert_response.data[0]['id']
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Add to queue
        task_queue.add_task(task_id, doc_id, user_id, content_str)
        
        # Start queue processing in background
        background_tasks.add_task(task_queue.process_queue, _sorter)
        
        return DocumentUploadResponse(
            filename=file.filename,
            status="queued",
            message=f"Document uploaded with ID {doc_id}. Task {task_id} queued for processing.",
            doc_id=doc_id,
            task_id=task_id,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
    async def get_task_status(task_id: str):
        """Get the status of a queued task"""
        task = task_queue.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        response = {
            "task_id": task.task_id,
            "doc_id": task.doc_id,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
        }
        
        if task.status == TaskStatus.COMPLETED:
            response["category_id"] = task.category_id
            response["completed_at"] = task.completed_at.isoformat()
            
            # Fetch category name from database
            try:
                cluster_response = _rag_service.supabase.table('clusters')\
                    .select('label')\
                    .eq('id', task.category_id)\
                    .single()\
                    .execute()
                if cluster_response.data:
                    response["category_name"] = cluster_response.data['label']
            except Exception as e:
                logger.error(f"Error fetching category: {e}")
        
        elif task.status == TaskStatus.FAILED:
            response["error"] = task.error
        
        return TaskStatusResponse(**response)
    
    @router.get("/file-category/{doc_id}", response_model=FileCategoryResponse)
    async def get_file_category(doc_id: str):
        """Get the category of a document from vector database"""
        try:
            # Fetch document with cluster info
            doc_response = _rag_service.supabase.table('documents')\
                .select('cluster_id, metadata')\
                .eq('id', doc_id)\
                .single()\
                .execute()
            
            if not doc_response.data:
                raise HTTPException(status_code=404, detail="Document not found")
            
            cluster_id = doc_response.data.get('cluster_id')
            
            if not cluster_id:
                return FileCategoryResponse(
                    doc_id=doc_id,
                    category="Uncategorized",
                    status="pending",
                    filename=doc_response.data.get('metadata', {}).get('filename', 'Unknown')
                )
            
            # Fetch category label
            cluster_response = _rag_service.supabase.table('clusters')\
                .select('label')\
                .eq('id', cluster_id)\
                .single()\
                .execute()
            
            return FileCategoryResponse(
                doc_id=doc_id,
                category=cluster_response.data['label'] if cluster_response.data else "Unknown",
                cluster_id=cluster_id,
                filename=doc_response.data.get('metadata', {}).get('filename', 'Unknown'),
                status="categorized"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching file category: {e}")
            raise HTTPException(status_code=500, detail=str(e))


