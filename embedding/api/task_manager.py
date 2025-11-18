import asyncio
from datetime import datetime
from typing import Dict, Optional
from collections import deque

from models import TaskInfo, TaskStatus
from sortify.embedding.agents.rag_agent import RAGAgent

# Singleton RAGAgent
_rag_agent: Optional[RAGAgent] = None

def get_rag_agent() -> RAGAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent


class TaskManager:
    # Manages background categorization and embedding tasks
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.queue: deque[str] = deque()
        self.is_processing = False
        self._lock = asyncio.Lock()
        self._max_concurrent_tasks = 2
        self._max_retries = 3
        self._retry_delay = 2.0

    def add_task(self, task_id: str, doc_id: str, user_id: str, content: str,
                 filename: str, file_type: str, file_size: int):
        task = TaskInfo(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
        )
        task.metadata = {
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size
        }
        self.tasks[task_id] = task
        self.queue.append(task_id)

        if not self.is_processing:
            asyncio.create_task(self.process_queue())

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        return self.tasks.get(task_id)

    async def process_queue(self):
        async with self._lock:
            if self.is_processing:
                return
            self.is_processing = True

        try:
            while self.queue:
                batch_size = min(self._max_concurrent_tasks, len(self.queue))
                batch = [self.queue.popleft() for _ in range(batch_size)]
                await asyncio.gather(*(self._process_single_task(tid) for tid in batch))
        finally:
            self.is_processing = False

    async def _process_single_task(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            return

        agent = get_rag_agent()
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
        return len(self.queue)

    def get_stats(self) -> Dict:
        return {
            "total_tasks": len(self.tasks),
            "pending": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            "processing": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING),
            "completed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "queue_size": len(self.queue),
            "is_processing": self.is_processing,
        }


_task_manager: Optional[TaskManager] = None

def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
