from datetime import datetime
import io
import uuid
import asyncio
from typing import Optional

from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Query,
)

from sortify.embedding.agents.rag_agent import get_rag_agent_sync
from models import (
    DocumentUploadResponse,
    TaskStatusResponse,
    FileCategoryResponse,
    TaskStatus,
)
from core import get_database_service
from api.task_manager import get_task_manager

router = APIRouter(prefix="/upload", tags=["uploads"])

# ----------------------------------------------------------------------
# SINGLETONS
# ----------------------------------------------------------------------

# Global RAG agent (chunk + embed + store). No categorization here.
agent = get_rag_agent_sync()


# ----------------------------------------------------------------------
# UPLOAD DOCUMENT
# ----------------------------------------------------------------------
@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    """
    Uploads a file, stores it in the DB, and queues a background
    RAG indexing task. Categorization is NOT done here; uncategorized
    docs are treated as belonging to the 'General' category.
    """
    import traceback

    try:
        db = get_database_service()
        task_manager = get_task_manager()

        # Auto-initialize standard categories for user on first upload
        existing_categories = await db.get_categories_by_user(user_id)
        if not existing_categories:
            print(f"[UPLOAD] No categories found for user {user_id}, initializing standard categories...")
            from services import get_categorization_service
            cat_service = get_categorization_service()
            created_ids = await cat_service.initialize_standard_categories(user_id)
            print(f"[UPLOAD] Created {len(created_ids)} categories: {created_ids}")
        else:
            print(f"[UPLOAD] User {user_id} has {len(existing_categories)} existing categories")

        # Read + extract content
        file_bytes = await file.read()
        content = await _extract_content(file, file_bytes)

        # Duplicate check (by content hash / whatever db.check_duplicate does)
        duplicate = await db.check_duplicate(content, user_id)
        if duplicate:
            return DocumentUploadResponse(
                filename=file.filename,
                status="duplicate",
                message=f"Document already exists with ID {duplicate}",
                doc_id=duplicate,
                task_id=None,
                timestamp=datetime.now(),
            )

        # Insert document into DB (no embedding / category yet)
        doc_id = await db.insert_document(
            content=content,
            metadata={
                "user_id": user_id,
                "filename": file.filename,
                "type": file.content_type,
                "size": len(file_bytes),
            },
            embedding=None,
            cluster_id=None,  # no category yet → treated as "General" in APIs
        )

        # Create task entry
        task_id = str(uuid.uuid4())
        task_manager.add_task(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            status=TaskStatus.PENDING,
            metadata={
                "filename": file.filename,
                "file_type": file.content_type,
                "file_size": len(file_bytes),
            },
        )

        # Background job: RAG indexing + async categorization
        async def _run_indexing(
            doc_id: str,
            content: str,
            user_id: str,
            metadata: dict,
            task_id: str,
        ):
            tm = get_task_manager()
            tm.mark_processing(task_id)

            try:
                # 1) Pure RAG indexing: chunk + embed + store
                await agent.index_document(
                    document_id=doc_id,
                    text=content,
                    user_id=user_id,
                    metadata=metadata,
                )

                # 2) Semantic categorization from stored chunks
                from services import get_categorization_service

                cat_service = get_categorization_service()
                cat_result = await cat_service.categorize_from_chunks(
                    document_id=doc_id,
                    user_id=user_id,
                    filename=metadata.get("filename", file.filename),
                )

                category_id = cat_result.get("category_id")

                # Store category on the task for /task-status
                tm.mark_completed(task_id, category_id=category_id)
            except Exception as e:
                tm.mark_failed(task_id, str(e))

        background_tasks.add_task(
            _run_indexing,
            doc_id,
            content,
            user_id,
            {"filename": file.filename, "type": file.content_type},
            task_id,
        )

        # Response to client
        return DocumentUploadResponse(
            filename=file.filename,
            status="queued",
            message=f"Document uploaded and queued (Task {task_id})",
            doc_id=doc_id,
            task_id=task_id,
            timestamp=datetime.now(),
        )

    except Exception as e:
        print("\nUPLOAD ERROR:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------
# GET ALL DOCUMENTS FOR USER
# ----------------------------------------------------------------------
@router.get("/documents")
async def get_documents(user_id: str = Query(...)):
    try:
        db = get_database_service()
        docs = await db.get_documents_by_user(user_id)
        return {
            "success": True,
            "documents": docs,
            "count": len(docs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------
# GET TASK STATUS
# ----------------------------------------------------------------------
@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    try:
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Default to "General" if no category has been assigned yet
        category_name: Optional[str] = "General"

        if task.category_id:
            db = get_database_service()
            cats = await db.get_categories_by_user(task.user_id)
            for c in cats:
                if c["id"] == task.category_id:
                    category_name = c["label"]
                    break

        return TaskStatusResponse(
            task_id=task.task_id,
            doc_id=task.doc_id,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            category_id=task.category_id,
            category_name=category_name,
            completed_at=task.completed_at.isoformat()
            if task.completed_at
            else None,
            error=task.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------
# GET FILE CATEGORY
# ----------------------------------------------------------------------
@router.get("/file-category/{doc_id}", response_model=FileCategoryResponse)
async def get_file_category(doc_id: str):
    """
    Returns the category for a document. If no explicit cluster/category
    is set, it is treated as belonging to the 'General' category.
    """
    try:
        db = get_database_service()
        doc = await db.get_document(doc_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        cluster_id = doc.get("cluster_id")
        filename = doc.get("metadata", {}).get("filename", "Unknown")

        # Default to "General"
        category_name = "General"

        if cluster_id:
            user_id = doc.get("metadata", {}).get("user_id")
            cats = await db.get_categories_by_user(user_id)
            for c in cats:
                if c["id"] == cluster_id:
                    category_name = c["label"]
                    break

        # "General" is treated as a real category from the frontend POV
        return FileCategoryResponse(
            doc_id=doc_id,
            category=category_name,
            cluster_id=cluster_id,
            filename=filename,
            status="categorized",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------
# EXTRACT FILE CONTENT
# ----------------------------------------------------------------------
async def _extract_content(file: UploadFile, data: bytes) -> str:
    """
    Very lightweight extraction:
    - text/* → utf-8 decode
    - pdf → text via pypdf
    - images → stub string (we don't OCR here)
    - other → basic description
    """
    try:
        if file.content_type and file.content_type.startswith("text/"):
            return data.decode("utf-8", errors="ignore")

        if file.content_type == "application/pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            extracted = [p.extract_text() for p in reader.pages if p.extract_text()]
            return (
                "\n\n".join(extracted)
                if extracted
                else f"PDF: {file.filename} (no text)"
            )

        if file.content_type and file.content_type.startswith("image/"):
            return (
                f"Image: {file.filename}\n"
                f"Type: {file.content_type}\n"
                f"Size: {len(data)} bytes"
            )

        return f"File: {file.filename}\nType: {file.content_type or 'unknown'}"

    except Exception:
        return f"File: {file.filename} (extraction failed)"


# ----------------------------------------------------------------------
# INITIALIZE STANDARD CATEGORIES (INCLUDING GENERAL)
# ----------------------------------------------------------------------
@router.post("/initialize-categories")
async def initialize_user_categories(user_id: str):
    """
    Initialize standard categories for a user via the improved categorization
    service. That service should ensure a 'General' category exists.
    """
    try:
        from services import get_categorization_service

        cat_service = get_categorization_service()
        ids = await cat_service.initialize_standard_categories(user_id)

        if ids:
            return {
                "success": True,
                "message": f"Initialized {len(ids)} categories",
                "categories": cat_service.standard_categories,
            }

        return {
            "success": False,
            "message": "Categories already exist",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
