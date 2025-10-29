import os
import psutil
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from threading import Lock, RLock
from queue import Queue
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PooledResource:
    """Wrapper for pooled resources."""
    resource_id: str
    data: Any
    size_bytes: int
    in_use: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)

class MemoryPool:
    """Memory pool manager for efficient resource reuse."""

    def __init__(self, max_pool_size_mb: int = 512, cleanup_threshold: float = 0.85):
        self.max_pool_size_bytes = max_pool_size_mb * 1024 * 1024
        self.cleanup_threshold = cleanup_threshold
        self.current_size = 0
        self.pool: Dict[str, PooledResource] = {}
        self.lock = RLock()
        self.process = psutil.Process(os.getpid())

        logger.info(f"Memory pool initialized: max_size={max_pool_size_mb}MB, threshold={cleanup_threshold}")

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        mem = psutil.virtual_memory()
        return MemoryStats(
            total_mb=mem.total / (1024 * 1024),
            used_mb=mem.used / (1024 * 1024),
            available_mb=mem.available / (1024 * 1024),
            percent=mem.percent
        )

    def should_cleanup(self) -> bool:
        """Check if cleanup is needed based on memory usage."""
        stats = self.get_memory_stats()
        return stats.percent > (self.cleanup_threshold * 100)

    def allocate(self, resource_id: str, data: Any, size_bytes: Optional[int] = None) -> bool:
        """Allocate resource in pool."""
        with self.lock:
            if size_bytes is None:
                if isinstance(data, np.ndarray):
                    size_bytes = data.nbytes
                else:
                    size_bytes = len(str(data))

            if self.current_size + size_bytes > self.max_pool_size_bytes:
                if not self._cleanup_lru():
                    logger.warning(f"Pool full, cannot allocate {size_bytes} bytes for {resource_id}")
                    return False

            resource = PooledResource(
                resource_id=resource_id,
                data=data,
                size_bytes=size_bytes,
                in_use=True
            )

            self.pool[resource_id] = resource
            self.current_size += size_bytes

            logger.debug(f"Allocated {size_bytes} bytes for {resource_id}, pool: {self.current_size}/{self.max_pool_size_bytes}")
            return True

    def get(self, resource_id: str) -> Optional[Any]:
        """Get resource from pool."""
        with self.lock:
            resource = self.pool.get(resource_id)
            if resource:
                resource.in_use = True
                resource.last_used = datetime.now()
                return resource.data
            return None

    def release(self, resource_id: str) -> bool:
        """Release resource back to pool."""
        with self.lock:
            resource = self.pool.get(resource_id)
            if resource:
                resource.in_use = False
                resource.last_used = datetime.now()
                return True
            return False

    def deallocate(self, resource_id: str) -> bool:
        """Remove resource from pool."""
        with self.lock:
            resource = self.pool.pop(resource_id, None)
            if resource:
                self.current_size -= resource.size_bytes
                logger.debug(f"Deallocated {resource.size_bytes} bytes for {resource_id}")
                return True
            return False

    def _cleanup_lru(self) -> bool:
        """Cleanup least recently used resources."""
        with self.lock:
            unused = [r for r in self.pool.values() if not r.in_use]
            if not unused:
                return False

            unused.sort(key=lambda r: r.last_used)
            freed = 0
            target = self.max_pool_size_bytes * 0.3

            for resource in unused:
                if freed >= target:
                    break
                self.pool.pop(resource.resource_id)
                self.current_size -= resource.size_bytes
                freed += resource.size_bytes

            logger.info(f"Cleaned up {freed} bytes from pool")
            return True

    def clear(self):
        """Clear entire pool."""
        with self.lock:
            self.pool.clear()
            self.current_size = 0
            logger.info("Memory pool cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self.lock:
            in_use = sum(1 for r in self.pool.values() if r.in_use)
            return {
                'total_resources': len(self.pool),
                'in_use': in_use,
                'available': len(self.pool) - in_use,
                'current_size_mb': self.current_size / (1024 * 1024),
                'max_size_mb': self.max_pool_size_bytes / (1024 * 1024),
                'utilization': self.current_size / self.max_pool_size_bytes if self.max_pool_size_bytes > 0 else 0
            }

class WorkerPool:
    """Worker pool for managing concurrent tasks."""

    def __init__(self, max_workers: int = 4, memory_per_worker_mb: int = 128):
        self.max_workers = max_workers
        self.memory_per_worker = memory_per_worker_mb * 1024 * 1024
        self.active_workers = 0
        self.worker_resources: Dict[int, int] = {}
        self.lock = Lock()

        logger.info(f"Worker pool initialized: max_workers={max_workers}, memory_per_worker={memory_per_worker_mb}MB")

    def acquire_worker(self, worker_id: int) -> bool:
        """Acquire worker slot."""
        with self.lock:
            if self.active_workers >= self.max_workers:
                return False

            self.active_workers += 1
            self.worker_resources[worker_id] = self.memory_per_worker
            logger.debug(f"Worker {worker_id} acquired, active: {self.active_workers}/{self.max_workers}")
            return True

    def release_worker(self, worker_id: int):
        """Release worker slot."""
        with self.lock:
            if worker_id in self.worker_resources:
                del self.worker_resources[worker_id]
                self.active_workers = max(0, self.active_workers - 1)
                logger.debug(f"Worker {worker_id} released, active: {self.active_workers}/{self.max_workers}")

    def get_available_workers(self) -> int:
        """Get number of available worker slots."""
        with self.lock:
            return self.max_workers - self.active_workers

    def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics."""
        with self.lock:
            return {
                'max_workers': self.max_workers,
                'active_workers': self.active_workers,
                'available_workers': self.max_workers - self.active_workers,
                'total_memory_mb': (sum(self.worker_resources.values()) / (1024 * 1024)) if self.worker_resources else 0
            }

_memory_pool: Optional[MemoryPool] = None
_worker_pool: Optional[WorkerPool] = None
_pool_lock = Lock()

def get_memory_pool() -> MemoryPool:
    """Get or create global memory pool."""
    global _memory_pool
    with _pool_lock:
        if _memory_pool is None:
            _memory_pool = MemoryPool()
        return _memory_pool

def get_worker_pool(max_workers: int = 4) -> WorkerPool:
    """Get or create global worker pool."""
    global _worker_pool
    with _pool_lock:
        if _worker_pool is None:
            _worker_pool = WorkerPool(max_workers=max_workers)
        return _worker_pool
