import asyncio
from datetime import datetime
from typing import Dict, Optional
from collections import deque
from models import TaskInfo, TaskStatus
from agents.rag_agent import RAGAgent

agent = RAGAgent()


class TaskManager:
    # Handles background document processing with automatic async queueing
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.queue: deque[str] = deque()
        self.is_processing = False
        self._lock = asyncio.Lock()
        self._max_concurrent_tasks = 2
        self._max_retries = 3
        self._retry_delay = 2.0

    def add_task(self, task_id: str, doc_id: str, user_id: str, content: str, filename: str, file_type: str, file_size: int):
        # Add new task and trigger background worker
        task = TaskInfo(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
        )
        task.metadata = {"filename": filename, "file_type": file_type, "file_size": file_size}
        self.tasks[task_id] = task
        self.queue.append(task_id)
        if not self.is_processing:
            asyncio.create_task(self.process_queue())

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        # Retrieve task by ID
        return self.tasks.get(task_id)

    async def process_queue(self):
        # Process queued tasks concurrently with retries
        async with self._lock:
            if self.is_processing:
                return
            self.is_processing = True
        try:
            while self.queue:
                # Create a batch of concurrent tasks (e.g., 2 at a time)
                batch = [self.queue.popleft() for _ in range(min(self._max_concurrent_tasks, len(self.queue)))]
                await asyncio.gather(*(self._process_single_task(tid) for tid in batch))
        finally:
            self.is_processing = False

    async def _process_single_task(self, task_id: str):
        # Process a single task with retry logic
        task = self.tasks.get(task_id)
        if not task:
            return
        task.status = TaskStatus.PROCESSING
        retries = 0
        while retries < self._max_retries:
            try:
                await agent.index_document(
                    document_id=task.doc_id,
                    text=task.content,
                    user_id=task.user_id,
                    metadata=task.metadata,
                )
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                return
            except Exception as e:
                retries += 1
                if retries >= self._max_retries:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    return
                await asyncio.sleep(self._retry_delay * retries)

    def get_queue_size(self) -> int:
        # Return queue size
        return len(self.queue)

    def get_stats(self) -> Dict:
        # Return task metrics
        return {
            "total_tasks": len(self.tasks),
            "pending": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            "processing": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING),
            "completed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "queue_size": len(self.queue),
            "is_processing": self.is_processing,
        }


# Singleton accessor
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    # Return singleton instance
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
