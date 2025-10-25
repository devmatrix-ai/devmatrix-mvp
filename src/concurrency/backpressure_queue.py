"""
BackpressureQueue - Smart request queuing with backpressure

Queues incoming requests when system is at capacity and applies backpressure
to prevent overload.
"""
import asyncio
import logging
from typing import Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """Queued request metadata"""
    request_id: str
    priority: int  # Lower = higher priority
    enqueued_at: datetime
    payload: Any


class BackpressureQueue:
    """
    Smart request queuing with priority and backpressure

    Features:
    - Priority-based queueing
    - Backpressure signals when queue is full
    - Timeout for queued requests
    - Queue statistics
    """

    def __init__(
        self,
        max_queue_size: int = 1000,
        request_timeout_seconds: int = 300
    ):
        """
        Initialize BackpressureQueue

        Args:
            max_queue_size: Maximum queue size (backpressure threshold)
            request_timeout_seconds: Timeout for queued requests
        """
        self.max_queue_size = max_queue_size
        self.request_timeout_seconds = request_timeout_seconds

        # Priority queue (lower priority number = higher priority)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)

        # Statistics
        self._enqueued_count = 0
        self._dequeued_count = 0
        self._timeout_count = 0
        self._rejected_count = 0

    async def enqueue(
        self,
        request_id: str,
        payload: Any,
        priority: int = 5
    ) -> bool:
        """
        Enqueue a request

        Args:
            request_id: Unique request identifier
            payload: Request payload
            priority: Priority (0 = highest, 10 = lowest)

        Returns:
            True if enqueued, False if queue is full (backpressure)
        """
        if self._queue.full():
            self._rejected_count += 1
            logger.warning(
                f"Queue full ({self.max_queue_size}), rejecting request {request_id}"
            )
            return False

        request = QueuedRequest(
            request_id=request_id,
            priority=priority,
            enqueued_at=datetime.utcnow(),
            payload=payload
        )

        try:
            # Use priority as sort key
            await self._queue.put((priority, request))
            self._enqueued_count += 1

            logger.debug(
                f"Enqueued request {request_id} with priority {priority} "
                f"(queue size: {self._queue.qsize()})"
            )

            return True

        except asyncio.QueueFull:
            self._rejected_count += 1
            logger.warning(f"Failed to enqueue request {request_id} (queue full)")
            return False

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[QueuedRequest]:
        """
        Dequeue a request (highest priority first)

        Args:
            timeout: Optional timeout in seconds

        Returns:
            QueuedRequest or None if queue is empty/timeout
        """
        try:
            priority, request = await asyncio.wait_for(
                self._queue.get(),
                timeout=timeout
            )

            self._dequeued_count += 1

            # Check if request has timed out
            age_seconds = (datetime.utcnow() - request.enqueued_at).total_seconds()
            if age_seconds > self.request_timeout_seconds:
                self._timeout_count += 1
                logger.warning(
                    f"Request {request.request_id} timed out in queue "
                    f"(age: {age_seconds:.1f}s)"
                )
                return None

            logger.debug(
                f"Dequeued request {request.request_id} "
                f"(queue size: {self._queue.qsize()})"
            )

            return request

        except asyncio.TimeoutError:
            return None

    def is_at_capacity(self, threshold: float = 0.8) -> bool:
        """
        Check if queue is at capacity

        Args:
            threshold: Capacity threshold (0-1)

        Returns:
            True if queue usage >= threshold
        """
        usage = self._queue.qsize() / self.max_queue_size
        return usage >= threshold

    def get_statistics(self) -> dict:
        """
        Get queue statistics

        Returns:
            Dict with stats: {
                'current_size': int,
                'max_size': int,
                'usage_percent': float,
                'enqueued_total': int,
                'dequeued_total': int,
                'timeout_count': int,
                'rejected_count': int
            }
        """
        current_size = self._queue.qsize()
        usage_percent = (current_size / self.max_queue_size) * 100

        return {
            'current_size': current_size,
            'max_size': self.max_queue_size,
            'usage_percent': usage_percent,
            'enqueued_total': self._enqueued_count,
            'dequeued_total': self._dequeued_count,
            'timeout_count': self._timeout_count,
            'rejected_count': self._rejected_count
        }

    async def clear(self):
        """Clear all queued requests"""
        while not self._queue.empty():
            try:
                await self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("Cleared request queue")
