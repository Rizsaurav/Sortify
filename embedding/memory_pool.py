"""
Memory pool management for efficient embedding buffer allocation.
Reduces GC pressure and improves performance for heavy computational tasks.
"""

import numpy as np
import logging
from typing import Optional, List
from threading import Lock
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PoolBuffer:
    """Reusable embedding buffer with metadata"""
    buffer: np.ndarray
    in_use: bool = False
    last_used: datetime = None
    use_count: int = 0

class MemoryPool:
    """Thread-safe memory pool for embedding computation buffers"""

    def __init__(self, buffer_size: int = 1024, initial_buffers: int = 5, max_buffers: int = 20):
        """
        Initialize memory pool with pre-allocated buffers.

        Args:
            buffer_size: Dimension of embedding vectors (default: 1024 for Qwen3)
            initial_buffers: Number of buffers to pre-allocate
            max_buffers: Maximum number of buffers in pool
        """
        self.buffer_size = buffer_size
        self.max_buffers = max_buffers
        self._lock = Lock()
        self._buffers: List[PoolBuffer] = []

        # Pre-allocate initial buffers
        for _ in range(initial_buffers):
            self._create_buffer()

        logger.info(f"Memory pool initialized with {initial_buffers} buffers (dim={buffer_size})")

    def _create_buffer(self) -> PoolBuffer:
        """Create a new buffer and add to pool"""
        buffer = PoolBuffer(
            buffer=np.zeros(self.buffer_size, dtype=np.float32),
            in_use=False,
            last_used=None,
            use_count=0
        )
        self._buffers.append(buffer)
        return buffer

    def acquire(self) -> Optional[np.ndarray]:
        """
        Acquire an available buffer from the pool.
        Creates new buffer if none available and under max limit.

        Returns:
            numpy array buffer or None if pool exhausted
        """
        with self._lock:
            # Find available buffer
            for pool_buffer in self._buffers:
                if not pool_buffer.in_use:
                    pool_buffer.in_use = True
                    pool_buffer.last_used = datetime.now()
                    pool_buffer.use_count += 1
                    return pool_buffer.buffer

            # Create new buffer if under limit
            if len(self._buffers) < self.max_buffers:
                pool_buffer = self._create_buffer()
                pool_buffer.in_use = True
                pool_buffer.last_used = datetime.now()
                pool_buffer.use_count += 1
                logger.info(f"Expanded pool to {len(self._buffers)} buffers")
                return pool_buffer.buffer

            logger.warning("Memory pool exhausted, consider increasing max_buffers")
            return None

    def release(self, buffer: np.ndarray):
        """
        Release a buffer back to the pool.

        Args:
            buffer: The numpy array to release
        """
        with self._lock:
            for pool_buffer in self._buffers:
                if pool_buffer.buffer is buffer:
                    pool_buffer.in_use = False
                    buffer.fill(0)  # Clear buffer data
                    return
            logger.warning("Attempted to release buffer not in pool")

    def get_stats(self) -> dict:
        """Get pool statistics"""
        with self._lock:
            in_use = sum(1 for b in self._buffers if b.in_use)
            total_uses = sum(b.use_count for b in self._buffers)
            return {
                "total_buffers": len(self._buffers),
                "in_use": in_use,
                "available": len(self._buffers) - in_use,
                "total_uses": total_uses,
                "max_buffers": self.max_buffers
            }

    def clear(self):
        """Release all buffers and clear pool"""
        with self._lock:
            self._buffers.clear()
            logger.info("Memory pool cleared")

# Global pool instance
_memory_pool: Optional[MemoryPool] = None

def get_memory_pool(buffer_size: int = 1024, initial_buffers: int = 5) -> MemoryPool:
    """Get or create global memory pool singleton"""
    global _memory_pool
    if _memory_pool is None:
        _memory_pool = MemoryPool(buffer_size=buffer_size, initial_buffers=initial_buffers)
    return _memory_pool
