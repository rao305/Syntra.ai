"""Cancellation token management for long-running requests."""
from __future__ import annotations

import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading


class CancellationRegistry:
    """Registry to track and cancel active requests."""
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._cancelled: Dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def register(self, request_id: str, task: asyncio.Task) -> None:
        """Register a task that can be cancelled."""
        with self._lock:
            self._tasks[request_id] = task
    
    def cancel(self, request_id: str) -> bool:
        """Cancel a request by ID. Returns True if cancelled, False if not found."""
        with self._lock:
            task = self._tasks.get(request_id)
            if task and not task.done():
                task.cancel()
                self._cancelled[request_id] = datetime.utcnow()
                return True
            return False
    
    def is_cancelled(self, request_id: str) -> bool:
        """Check if a request has been cancelled."""
        with self._lock:
            return request_id in self._cancelled
    
    def unregister(self, request_id: str) -> None:
        """Unregister a completed task."""
        with self._lock:
            self._tasks.pop(request_id, None)
            # Clean up old cancellation records (older than 1 hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            self._cancelled = {
                k: v for k, v in self._cancelled.items() 
                if v > cutoff
            }


# Global registry instance
cancellation_registry = CancellationRegistry()









