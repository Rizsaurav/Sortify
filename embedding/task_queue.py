import asyncio
from typing import Dict, Optional
from collections import deque
from queue import PriorityQueue
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskPriority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0

@dataclass
class QueuedTask:
    task_id: str
    doc_id: str
    user_id: str
    content: str
    status: TaskStatus
    created_at: datetime
    priority: TaskPriority = TaskPriority.NORMAL
    completed_at: Optional[datetime] = None
    category_id: Optional[int] = None
    error: Optional[str] = None
    worker_id: Optional[int] = None

    def __lt__(self, other):
        """Compare tasks by priority for priority queue."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

class TaskQueueManager:
    """Manages file processing tasks with priority and worker pool."""

    def __init__(self, max_workers: int = 4):
        self.priority_queue: PriorityQueue = PriorityQueue()
        self.tasks: Dict[str, QueuedTask] = {}
        self.is_processing = False
        self.max_workers = max_workers
        self.active_tasks = 0

    def add_task(
        self,
        task_id: str,
        doc_id: str,
        user_id: str,
        content: str,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> QueuedTask:
        """Add a task to the priority queue."""
        task = QueuedTask(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            priority=priority
        )
        self.priority_queue.put((priority.value, task))
        self.tasks[task_id] = task
        logger.info(f"Task {task_id} added with priority {priority.name}. Queue size: {self.priority_queue.qsize()}")
        return task
    
    def get_task_status(self, task_id: str) -> Optional[QueuedTask]:
        """Get the status of a task"""
        return self.tasks.get(task_id)
    
    async def process_queue(self, sorter):
        """Process tasks from priority queue with worker pool."""
        if self.is_processing:
            return

        self.is_processing = True

        while not self.priority_queue.empty():
            if self.active_tasks >= self.max_workers:
                await asyncio.sleep(0.1)
                continue

            _, task = self.priority_queue.get()

            if not task:
                continue

            self.active_tasks += 1
            task.status = TaskStatus.PROCESSING
            task.worker_id = self.active_tasks
            logger.info(f"Processing task {task.task_id} (priority: {task.priority.name}, worker: {task.worker_id})")

            try:
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
                    logger.info(f"Task {task.task_id} completed (worker: {task.worker_id})")
                else:
                    task.status = TaskStatus.FAILED
                    task.error = result.get('error', 'Unknown error')
                    logger.error(f"Task {task.task_id} failed: {task.error}")

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"Task {task.task_id} error: {e}")
            finally:
                self.active_tasks -= 1

        self.is_processing = False

    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)

        return {
            'total_tasks': len(self.tasks),
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'queue_size': self.priority_queue.qsize(),
            'active_workers': self.active_tasks,
            'max_workers': self.max_workers
        }

# Global queue manager
task_queue = TaskQueueManager()
