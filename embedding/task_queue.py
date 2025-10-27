import asyncio
from typing import Dict, Optional
from collections import deque
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from heapq import heappush, heappop

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskPriority(Enum):
    """Task priority levels for job queue"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass
class QueuedTask:
    task_id: str
    doc_id: str
    user_id: str
    content: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    category_id: Optional[int] = None
    error: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3

    def __lt__(self, other):
        """Priority queue comparison"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

class TaskQueueManager:
    """Manages file processing tasks with priority queue and retry logic"""

    def __init__(self):
        self.queue: list = []  # Priority queue (min-heap)
        self.tasks: Dict[str, QueuedTask] = {}
        self.is_processing = False

    def add_task(
        self,
        task_id: str,
        doc_id: str,
        user_id: str,
        content: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3
    ) -> QueuedTask:
        """Add a task to the priority queue"""
        task = QueuedTask(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            priority=priority,
            max_retries=max_retries
        )
        heappush(self.queue, (task.priority.value, task.created_at, task_id))
        self.tasks[task_id] = task
        logger.info(f"Task {task_id} added to queue (priority={priority.name}). Queue size: {len(self.queue)}")
        return task
    
    def get_task_status(self, task_id: str) -> Optional[QueuedTask]:
        """Get the status of a task"""
        return self.tasks.get(task_id)

    def get_queue_stats(self) -> dict:
        """Get queue statistics"""
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        return {
            "queue_size": len(self.queue),
            "total_tasks": len(self.tasks),
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed
        }

    async def process_queue(self, sorter):
        """Process tasks in priority queue with retry logic"""
        if self.is_processing:
            return

        self.is_processing = True

        while self.queue:
            _, _, task_id = heappop(self.queue)
            task = self.tasks.get(task_id)

            if not task or task.status != TaskStatus.PENDING:
                continue

            task.status = TaskStatus.PROCESSING
            logger.info(f"Processing task {task_id} (priority={task.priority.name})")

            try:
                # Run sorting in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    sorter.sort_document,
                    task.doc_id,
                    task.content,
                    task.user_id
                )

                if result['success']:
                    task.status = TaskStatus.COMPLETED
                    task.category_id = result.get('category_id')
                    task.completed_at = datetime.now()
                    logger.info(f"Task {task_id} completed successfully")
                else:
                    # Retry logic
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        task.status = TaskStatus.PENDING
                        heappush(self.queue, (task.priority.value, datetime.now(), task_id))
                        logger.warning(f"Task {task_id} failed, retry {task.retry_count}/{task.max_retries}")
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = result.get('error', 'Unknown error')
                        logger.error(f"Task {task_id} failed after {task.max_retries} retries: {task.error}")

            except Exception as e:
                # Retry on exception
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    heappush(self.queue, (task.priority.value, datetime.now(), task_id))
                    logger.warning(f"Task {task_id} error, retry {task.retry_count}/{task.max_retries}: {e}")
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    logger.error(f"Task {task_id} failed after {task.max_retries} retries: {e}")

        self.is_processing = False

# Global queue manager
task_queue = TaskQueueManager()
