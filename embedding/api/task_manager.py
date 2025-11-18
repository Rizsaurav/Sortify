from datetime import datetime
from typing import Dict, Optional, Any

from models import TaskInfo, TaskStatus


class TaskManager:
    """
    Lightweight task tracker for document indexing.

    IMPORTANT:
    - This class NO LONGER runs the RAG agent or does any indexing.
    - It ONLY tracks task metadata and status for the API (/upload/task-status).
    - The actual work (agent.index_document) should be triggered elsewhere
      (e.g., FastAPI BackgroundTasks in upload_router).
    """

    def __init__(self) -> None:
        # task_id -> TaskInfo
        self.tasks: Dict[str, TaskInfo] = {}

    # Creation

    def add_task(
        self,
        task_id: str,
        doc_id: str,
        user_id: str,
        status: TaskStatus = TaskStatus.PENDING,
        metadata: Optional[Dict[str, Any]] = None,
        category_id: Optional[str] = None,
    ) -> TaskInfo:
        """
        Register a new task in 'PENDING' (or provided) status.

        This does NOT start any background processing.
        The caller is responsible for actually running indexing.
        """
        task = TaskInfo(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=None, 
            status=status,
            created_at=datetime.now(),
        )

        # Optional metadata (filename, size, file_type, etc.)
        task.metadata = metadata or {}
        task.category_id = category_id
        task.completed_at = None
        task.error = None

        self.tasks[task_id] = task
        return task

    # Lookups
    # 

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        return self.tasks.get(task_id)

    # Status updates

    def mark_processing(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = TaskStatus.PROCESSING

    def mark_completed(
        self,
        task_id: str,
        category_id: Optional[str] = None,
    ) -> None:
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        if category_id is not None:
            task.category_id = category_id

    def mark_failed(self, task_id: str, error: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = datetime.now()

    # Stats

    def get_stats(self) -> Dict[str, Any]:
        """
        Basic stats used by /health or any monitoring endpoints.
        """
        return {
            "total_tasks": len(self.tasks),
            "pending": sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.PENDING
            ),
            "processing": sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING
            ),
            "completed": sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED
            ),
            "failed": sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.FAILED
            ),
            # kept for backwards compatibility (no real queue anymore)
            "queue_size": 0,
            "is_processing": False,
        }


_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
