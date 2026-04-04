"""API layer - FastAPI routes and endpoints."""

from .upload_api import router as upload_router
from .rag_api import router as rag_router
from .category_api import router as category_router
from .notifications_api import router as notifications_router
from .task_manager import get_task_manager, TaskManager

__all__ = [
    "upload_router",
    "rag_router",
    "category_router",
    "notifications_router",
    "get_task_manager",
    "TaskManager",
]

