import asyncio
from typing import Dict, Optional
from collections import deque
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

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

class TaskQueueManager:
    """Manages file processing tasks in a queue"""
    
    def __init__(self):
        self.queue: deque = deque()
        self.tasks: Dict[str, QueuedTask] = {}
        self.is_processing = False
        
    def add_task(self, task_id: str, doc_id: str, user_id: str, content: str) -> QueuedTask:
        """Add a task to the queue"""
        task = QueuedTask(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        self.queue.append(task_id)
        self.tasks[task_id] = task
        logger.info(f"Task {task_id} added to queue. Queue size: {len(self.queue)}")
        return task
    
    def get_task_status(self, task_id: str) -> Optional[QueuedTask]:
        """Get the status of a task"""
        return self.tasks.get(task_id)
    
    async def process_queue(self, sorter):
        """Process tasks in the queue"""
        if self.is_processing:
            return
            
        self.is_processing = True
        
        while self.queue:
            task_id = self.queue.popleft()
            task = self.tasks.get(task_id)
            
            if not task:
                continue
                
            task.status = TaskStatus.PROCESSING
            logger.info(f"Processing task {task_id}")
            
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
                    task.status = TaskStatus.FAILED
                    task.error = result.get('error', 'Unknown error')
                    logger.error(f"Task {task_id} failed: {task.error}")
                    
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"Task {task_id} error: {e}")
        
        self.is_processing = False

# Global queue manager
task_queue = TaskQueueManager()
