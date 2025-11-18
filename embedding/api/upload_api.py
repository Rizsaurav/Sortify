from datetime import datetime
import io
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from sortify.embedding.agents.rag_agent import RAGAgent
from models import DocumentUploadResponse, TaskStatusResponse, FileCategoryResponse
from core import get_database_service
from api.task_manager import get_task_manager

router = APIRouter(prefix="/upload", tags=["uploads"])

agent = RAGAgent()


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    # Upload a document and queue it for processing
    try:
        db_service = get_database_service()
        task_manager = get_task_manager()

        file_bytes = await file.read()
        content = await _extract_content(file, file_bytes)

        duplicate = db_service.check_duplicate(content, user_id)
        if duplicate:
            return DocumentUploadResponse(
                filename=file.filename,
                status="duplicate",
                message=f"Document already exists with ID {duplicate}",
                doc_id=duplicate,
                task_id=None,
                timestamp=datetime.now()
            )

        doc_id = db_service.insert_document(
            content=content,
            metadata={
                "user_id": user_id,
                "filename": file.filename,
                "type": file.content_type,
                "size": len(file_bytes)
            },
            embedding=None,
            cluster_id=None
        )

        task_id = str(uuid.uuid4())

        # Background processing for embedding + categorization
        background_tasks.add_task(agent.index_document, doc_id, content, user_id, {
            "filename": file.filename,
            "type": file.content_type
        })

        # Track background task
        task_manager.add_task(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content,
            filename=file.filename,
            file_type=file.content_type,
            file_size=len(file_bytes)
        )

        return DocumentUploadResponse(
            filename=file.filename,
            status="queued",
            message=f"Document uploaded and queued (Task {task_id})",
            doc_id=doc_id,
            task_id=task_id,
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def get_documents(user_id: str = Query(...)):
    # Return all documents for a user
    try:
        db_service = get_database_service()
        docs = db_service.get_documents_by_user(user_id)
        return {"success": True, "documents": docs, "count": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    # Return the current status of a processing task
    try:
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        category_name = None
        if task.category_id:
            db_service = get_database_service()
            cats = db_service.get_categories_by_user(task.user_id)
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
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error=task.error
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-category/{doc_id}", response_model=FileCategoryResponse)
async def get_file_category(doc_id: str):
    # Return file category information
    try:
        db_service = get_database_service()
        doc = db_service.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        cluster_id = doc.get("cluster_id")
        category_name = "Uncategorized"

        if cluster_id:
            user_id = doc.get("metadata", {}).get("user_id")
            cats = db_service.get_categories_by_user(user_id)
            for c in cats:
                if c["id"] == cluster_id:
                    category_name = c["label"]
                    break

        filename = doc.get("metadata", {}).get("filename", "Unknown")

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
        raise HTTPException(status_code=500, detail=str(e))


async def _extract_content(file: UploadFile, data: bytes) -> str:
    # Extract text content based on MIME type
    try:
        if file.content_type and file.content_type.startswith("text/"):
            return data.decode("utf-8", errors="ignore")
        elif file.content_type == "application/pdf":
            from pypdf import PdfReader
            pdf = io.BytesIO(data)
            reader = PdfReader(pdf)
            text = "\n\n".join(
                [p.extract_text() for p in reader.pages if p.extract_text()]
            )
            return text or f"PDF: {file.filename} (no text)"
        elif file.content_type and file.content_type.startswith("image/"):
            return f"Image: {file.filename}\nType: {file.content_type}\nSize: {len(data)} bytes"
        else:
            return f"File: {file.filename}\nType: {file.content_type or 'unknown'}"
    except Exception:
        return f"File: {file.filename} (extraction failed)"


@router.post("/initialize-categories")
async def initialize_user_categories(user_id: str):
    # Initialize standard categories for user
    try:
        from services import get_improved_categorization_service
        cat_service = get_improved_categorization_service()
        ids = cat_service.initialize_standard_categories(user_id)
        if ids:
            return {
                "success": True,
                "message": f"Initialized {len(ids)} categories",
                "categories": cat_service.standard_categories
            }
        return {"success": False, "message": "Categories already exist"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
