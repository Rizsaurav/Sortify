"""
Task manager - Handles background task queue for document processing.
Coordinates document chunking and categorization.
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from collections import deque

from models import TaskInfo, TaskStatus
from services import get_document_service, get_improved_categorization_service
from utils import get_logger

logger = get_logger(__name__)


class TaskManager:
    """
    Manages background task queue for document processing.
    Single Responsibility: Task queue management and processing coordination.
    """
    
    def __init__(self):
        """Initialize task manager."""
        self.tasks: Dict[str, TaskInfo] = {}
        self.queue: deque = deque()
        self.is_processing: bool = False
        
        logger.info("TaskManager initialized")
    
    def add_task(
        self,
        task_id: str,
        doc_id: str,
        user_id: str,
        content: str,
        filename: str,
        file_type: str,
        file_size: int
    ) -> None:
        """
        Add a task to the queue.
        
        Args:
            task_id: Unique task ID
            doc_id: Document ID
            user_id: User ID
            content: Document content
            filename: Filename
            file_type: File MIME type
            file_size: File size in bytes
        """
        task = TaskInfo(
            task_id=task_id,
            doc_id=doc_id,
            user_id=user_id,
            content=content,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        
        # Store task with metadata
        self.tasks[task_id] = task
        task.metadata = {
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size
        }
        
        # Add to queue
        self.queue.append(task_id)
        
        logger.info(f"Task {task_id} added to queue (queue size: {len(self.queue)})")
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    async def process_queue(self) -> None:
        """
        Process all tasks in the queue.
        Uses chunk-based categorization.
        """
        if self.is_processing:
            logger.debug("Queue processing already in progress")
            return
        
        self.is_processing = True
        logger.info(f"Starting queue processing ({len(self.queue)} tasks)")
        
        try:
            doc_service = get_document_service()
            cat_service = get_improved_categorization_service()  # Use improved service!
            
            while self.queue:
                task_id = self.queue.popleft()
                task = self.tasks.get(task_id)
                
                if not task:
                    logger.warning(f"Task {task_id} not found")
                    continue
                
                task.status = TaskStatus.PROCESSING
                logger.info(f"Processing task {task_id} (doc={task.doc_id})")
                
                try:
                    # Run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    
                    # 1. Process and store document with chunks
                    metadata = getattr(task, 'metadata', {})
                    chunked_doc = await loop.run_in_executor(
                        None,
                        doc_service.process_and_store_document,
                        task.doc_id,
                        metadata.get('filename', 'unknown'),
                        task.content,
                        task.user_id,
                        metadata.get('file_type', 'unknown'),
                        metadata.get('file_size', 0)
                    )
                    
                    logger.info(
                        f"Document {task.doc_id} chunked into "
                        f"{chunked_doc.total_chunks} chunks"
                    )
                    
                    # 2. Categorize from chunks (with filename for keyword hints)
                    result = await loop.run_in_executor(
                        None,
                        cat_service.categorize_from_chunks,
                        task.doc_id,
                        task.user_id,
                        metadata.get('filename', 'unknown')
                    )
                    
                    if result.get('success'):
                        task.status = TaskStatus.COMPLETED
                        task.category_id = result.get('category_id')
                        task.completed_at = datetime.now()
                        
                        logger.info(
                            f"✓ Task {task_id} completed "
                            f"(category={result.get('category_name')}, "
                            f"chunks={result.get('chunks_processed', 0)})"
                        )
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = result.get('error', 'Unknown error')
                        logger.error(f"Task {task_id} failed: {task.error}")
                
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    logger.error(f"Task {task_id} error: {e}", exc_info=True)
        
        finally:
            self.is_processing = False
            logger.info("Queue processing completed")
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)
    
    def get_stats(self) -> Dict:
        """Get task statistics."""
        stats = {
            'total_tasks': len(self.tasks),
            'pending': sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            'processing': sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING),
            'completed': sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            'failed': sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            'queue_size': len(self.queue),
            'is_processing': self.is_processing
        }
        return stats


# Singleton instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get or create task manager singleton."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


