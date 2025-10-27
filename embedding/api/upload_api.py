"""
Upload API routes - Handles document uploads and task management.
Clean separation of concerns with proper dependency injection.
"""

import io
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks

from models import DocumentUploadResponse, TaskStatusResponse, FileCategoryResponse
from services import get_document_service, get_categorization_service
from core import get_database_service
from utils import get_logger
from api.task_manager import get_task_manager
from classifier import get_hybrid_pipeline

logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/upload",
    tags=["uploads"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload a document and queue it for processing.
    Returns immediately without waiting for ML processing.
    
    Args:
        file: Uploaded file
        user_id: User ID
    
    Returns:
        Upload response with task ID
    """
    try:
        logger.info(f"Upload request: {file.filename} (user={user_id})")
        
        # Get services
        doc_service = get_document_service()
        db_service = get_database_service()
        task_manager = get_task_manager()
        
        # Read file content
        content_bytes = await file.read()
        
        # Extract text based on file type
        content_str = await _extract_content(file, content_bytes)
        
        # Check for duplicates
        duplicate_id = doc_service.check_duplicate(content_str, user_id)
        if duplicate_id:
            logger.info(f"Duplicate detected: {duplicate_id}")
            return DocumentUploadResponse(
                filename=file.filename,
                status="duplicate",
                message=f"Document already exists with ID {duplicate_id}",
                doc_id=duplicate_id,
                task_id=None,
                timestamp=datetime.now()
            )
        
        # Insert parent document to database (with FULL content)
        doc_id = db_service.insert_document(
            content=content_str,  # FULL CONTENT, not preview!
            metadata={
                'user_id': user_id,
                'filename': file.filename,
                'type': file.content_type,
                'size': len(content_bytes)
            },
            embedding=None,  # Will be set after chunking
            cluster_id=None  # Will be set after categorization
        )
        
        logger.info(f"Created document {doc_id} with {len(content_str)} characters")
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Add to task queue for chunking + categorization
        task_manager.add_task(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content_str,  # Full content for processing
            filename=file.filename,
            file_type=file.content_type or 'unknown',
            file_size=len(content_bytes)
        )
        
        # Process in background (this will chunk AND categorize)
        background_tasks.add_task(task_manager.process_queue)
        
        logger.info(f"Task {task_id} queued for processing")
        
        return DocumentUploadResponse(
            filename=file.filename,
            status="queued",
            message=f"Document uploaded. Task {task_id} queued for processing.",
            doc_id=doc_id,
            task_id=task_id,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a processing task.
    
    Args:
        task_id: Task ID
    
    Returns:
        Task status information
    """
    try:
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get category name if available
        category_name = None
        if task.category_id:
            db_service = get_database_service()
            categories = db_service.get_categories_by_user(task.user_id)
            for cat in categories:
                if cat['id'] == task.category_id:
                    category_name = cat['label']
                    break
        
        return TaskStatusResponse(
            task_id=task.task_id,
            doc_id=task.doc_id,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            category_id=task.category_id,
            category_name=category_name,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error=task.error
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-category/{doc_id}", response_model=FileCategoryResponse)
async def get_file_category(doc_id: str):
    """
    Get the category of a file.
    
    Args:
        doc_id: Document ID
    
    Returns:
        File category information
    """
    try:
        db_service = get_database_service()
        
        # Get document
        doc = db_service.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get category if assigned
        cluster_id = doc.get('cluster_id')
        category_name = "Uncategorized"
        
        if cluster_id:
            user_id = doc.get('metadata', {}).get('user_id')
            categories = db_service.get_categories_by_user(user_id)
            for cat in categories:
                if cat['id'] == cluster_id:
                    category_name = cat['label']
                    break
        
        filename = doc.get('metadata', {}).get('filename', 'Unknown')
        
        return FileCategoryResponse(
            doc_id=doc_id,
            category=category_name,
            cluster_id=cluster_id,
            filename=filename,
            status="categorized" if cluster_id else "pending"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function
async def _extract_content(file: UploadFile, content_bytes: bytes) -> str:
    """Extract text content from file based on type."""
    try:
        if file.content_type and file.content_type.startswith('text/'):
            return content_bytes.decode("utf-8", errors="ignore")
        
        elif file.content_type == 'application/pdf':
            try:
                from pypdf import PdfReader
                pdf_file = io.BytesIO(content_bytes)
                reader = PdfReader(pdf_file)
                text_pages = [
                    page.extract_text()
                    for page in reader.pages
                    if page.extract_text()
                ]
                content = "\n\n".join(text_pages)
                return content if content.strip() else f"PDF: {file.filename} (no text)"
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                return f"PDF: {file.filename} (extraction failed)"
        
        elif file.content_type and file.content_type.startswith('image/'):
            return f"Image: {file.filename}\nType: {file.content_type}\nSize: {len(content_bytes)} bytes"
        
        else:
            return f"File: {file.filename}\nType: {file.content_type or 'unknown'}"
    
    except Exception as e:
        logger.error(f"Content extraction failed: {e}")
        return f"File: {file.filename} (extraction failed)"


@router.post("/initialize-categories")
async def initialize_user_categories(user_id: str):
    """
    Initialize standard categories for a user.
    Useful for existing users or manual category setup.
    
    Args:
        user_id: User ID
    
    Returns:
        List of created category IDs and names
    """
    try:
        from services import get_improved_categorization_service
        
        cat_service = get_improved_categorization_service()
        category_ids = cat_service.initialize_standard_categories(user_id)
        
        if category_ids:
            return {
                "success": True,
                "message": f"Initialized {len(category_ids)} standard categories",
                "category_count": len(category_ids),
                "categories": cat_service.standard_categories
            }
        else:
            return {
                "success": False,
                "message": "Categories already exist or initialization failed"
            }
    
    except Exception as e:
        logger.error(f"Category initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-correction")
async def record_user_correction(
    document_id: str = Form(...),
    predicted_category: str = Form(...),
    final_category: str = Form(...),
    predicted_confidence: float = Form(...),
    user_id: str = Form(...),
    filename: str = Form("")
):
    """
    Record when user manually corrects a categorization.
    """
    try:
        pipeline = get_hybrid_pipeline()
        
        success = pipeline.record_user_correction(
            user_id=user_id,
            document_id=document_id,
            predicted_category=predicted_category,
            final_category=final_category,
            predicted_confidence=predicted_confidence,
            filename=filename
        )
        
        if success:
            return {
                "success": True,
                "message": "User correction recorded successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to record correction")
            
    except Exception as e:
        logger.error(f"Failed to record user correction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-status")
async def get_system_status():
    """
    Get system status for all classifier components.
    """
    try:
        pipeline = get_hybrid_pipeline()
        status = pipeline.get_system_status()
        
        return {
            "status": "healthy" if all(status.get(k, {}).get('active', False) for k in status.keys() if k != 'timestamp') else "degraded",
            "components": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint for classifier system.
    """
    try:
        pipeline = get_hybrid_pipeline()
        status = pipeline.get_system_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "reference_classifier": status.get("reference_classifier", {}).get("trained", False),
                "user_preferences": status.get("user_preferences", {}).get("active", False),
                "drift_control": status.get("drift_control", {}).get("active", False),
                "ux_hooks": status.get("ux_hooks", {}).get("active", False)
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


