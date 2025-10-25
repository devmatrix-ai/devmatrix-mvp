"""
Request Batcher - Batch multiple atoms' prompts into single LLM call

Reduces overhead and improves throughput by batching requests.

Features:
- Configurable batch window (default 500ms)
- Max batch size (default 5 atoms)
- Async future-based request handling
- Thread-safe queue management
- Prometheus metrics integration

Benefits:
- Fewer HTTP requests → lower overhead
- More tokens per request → better throughput
- Lower latency per atom (amortized)

Performance:
- Batch window: 500ms (configurable)
- Max batch size: 5 atoms (configurable)
- Thread-safe with asyncio.Lock
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import List, Callable, Any
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class BatchedRequest:
    """Single request in batch"""

    atom_id: UUID
    prompt: str
    future: asyncio.Future


class RequestBatcher:
    """
    Batch multiple atoms' prompts into single LLM call

    Strategy:
    1. Collect requests for batch_window_ms (500ms)
    2. Combine prompts with separator
    3. Send single LLM call
    4. Parse response back to individual atoms
    5. Resolve each future with its response

    Example:
        batcher = RequestBatcher(llm_client, max_batch_size=5, batch_window_ms=500)

        # Execute with batching
        response = await batcher.execute_with_batching(atom_id, prompt)
    """

    def __init__(
        self,
        llm_client,
        max_batch_size: int = 5,
        batch_window_ms: int = 500,
    ):
        """
        Initialize RequestBatcher

        Args:
            llm_client: LLM client instance with generate() method
            max_batch_size: Maximum number of requests per batch (default: 5)
            batch_window_ms: Batch window in milliseconds (default: 500)
        """
        self.llm_client = llm_client
        self.max_batch_size = max_batch_size
        self.batch_window_ms = batch_window_ms / 1000  # Convert to seconds

        self._pending_requests: List[BatchedRequest] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task = None

        # Metrics will be imported later to avoid circular dependency
        self._metrics_initialized = False

    async def execute_with_batching(self, atom_id: UUID, prompt: str) -> str:
        """
        Execute atom prompt with batching

        Args:
            atom_id: Atom UUID
            prompt: LLM prompt

        Returns:
            LLM response text for this atom
        """
        # Create future for this request
        future = asyncio.Future()

        batched_request = BatchedRequest(
            atom_id=atom_id, prompt=prompt, future=future
        )

        async with self._batch_lock:
            self._pending_requests.append(batched_request)

            # Start batch task if not running
            if not self._batch_task or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._process_batch())

        # Wait for result
        response = await future
        return response

    async def _process_batch(self):
        """
        Wait for batch window, then process all pending requests
        """
        # Wait for batch window to collect more requests
        await asyncio.sleep(self.batch_window_ms)

        async with self._batch_lock:
            if not self._pending_requests:
                return

            # Take up to max_batch_size requests
            batch = self._pending_requests[: self.max_batch_size]
            self._pending_requests = self._pending_requests[self.max_batch_size :]

        logger.info(f"Processing batch of {len(batch)} requests")

        try:
            # Combine prompts
            combined_prompt = self._combine_prompts(batch)

            # Send single LLM call
            response = await self.llm_client.generate(
                prompt=combined_prompt,
                model="claude-3-5-sonnet-20241022",  # Default model
                temperature=0.7,
            )

            # Parse response back to individual atoms
            individual_responses = self._parse_batched_response(
                response.text, len(batch)
            )

            # Resolve each future
            for batched_request, response_text in zip(batch, individual_responses):
                batched_request.future.set_result(response_text)

            # Emit metrics
            self._emit_batch_metrics(len(batch))

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")

            # Fail all futures
            for batched_request in batch:
                if not batched_request.future.done():
                    batched_request.future.set_exception(e)

    def _combine_prompts(self, batch: List[BatchedRequest]) -> str:
        """
        Combine multiple prompts into single batched prompt

        Format:
        ---
        Process the following prompts separately and return responses in the same order:

        --- PROMPT 1 (atom: uuid) ---
        {prompt_1}

        --- PROMPT 2 (atom: uuid) ---
        {prompt_2}

        --- END PROMPTS ---

        Return responses in format:
        RESPONSE 1:
        {response_1}

        RESPONSE 2:
        {response_2}
        ---

        Args:
            batch: List of BatchedRequest objects

        Returns:
            Combined prompt string
        """
        combined = "Process the following prompts separately and return responses in the same order:\n\n"

        for idx, batched_request in enumerate(batch):
            combined += f"--- PROMPT {idx + 1} (atom: {batched_request.atom_id}) ---\n"
            combined += f"{batched_request.prompt}\n\n"

        combined += "--- END PROMPTS ---\n\n"
        combined += "Return responses in format:\n"
        combined += "RESPONSE 1:\n{response_1}\n\n"
        combined += "RESPONSE 2:\n{response_2}\n\n"
        combined += "etc."

        return combined

    def _parse_batched_response(
        self, response_text: str, expected_count: int
    ) -> List[str]:
        """
        Parse batched response back to individual responses

        Args:
            response_text: LLM response text with multiple responses
            expected_count: Expected number of responses

        Returns:
            List of individual response texts
        """
        # Split by RESPONSE markers
        pattern = r"RESPONSE (\d+):\s*(.*?)(?=RESPONSE \d+:|$)"
        matches = re.findall(pattern, response_text, re.DOTALL)

        if len(matches) != expected_count:
            logger.warning(
                f"Expected {expected_count} responses, got {len(matches)}"
            )

        # Extract response texts
        responses = [match[1].strip() for match in matches]

        # Pad with empty responses if needed
        while len(responses) < expected_count:
            responses.append("")
            logger.warning(f"Padding missing response at index {len(responses)}")

        return responses[:expected_count]

    def _emit_batch_metrics(self, batch_size: int):
        """
        Emit Prometheus batch metrics

        Args:
            batch_size: Number of requests in batch
        """
        try:
            # Import metrics here to avoid circular dependency
            if not self._metrics_initialized:
                from .metrics import BATCH_SIZE, BATCH_REQUESTS_PROCESSED

                self._BATCH_SIZE = BATCH_SIZE
                self._BATCH_REQUESTS_PROCESSED = BATCH_REQUESTS_PROCESSED
                self._metrics_initialized = True

            self._BATCH_SIZE.observe(batch_size)
            self._BATCH_REQUESTS_PROCESSED.inc(batch_size)

        except ImportError:
            # Metrics not available yet (during initial setup)
            pass
        except Exception as e:
            logger.debug(f"Failed to emit batch metrics: {e}")
