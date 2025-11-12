"""
Unit tests for RequestBatcher

Tests:
- Batch collection (500ms window)
- Batch size limiting (max 5)
- Prompt combination
- Response parsing
- Parsing error handling
- Future resolution
- Metrics emission
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from dataclasses import dataclass

from src.mge.v2.caching.request_batcher import RequestBatcher, BatchedRequest


@dataclass
class MockLLMResponse:
    """Mock LLM response"""

    text: str


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client"""
    client = Mock()
    client.generate = AsyncMock()
    return client


class TestBatchCollection:
    """Test batch collection logic"""

    @pytest.mark.asyncio
    async def test_batches_requests_within_window(self, mock_llm_client):
        """Requests within batch window should be batched together"""
        batcher = RequestBatcher(mock_llm_client, max_batch_size=5, batch_window_ms=100, enabled=True)

        mock_llm_client.generate.return_value = MockLLMResponse(
            text="RESPONSE 1:\nAnswer 1\n\nRESPONSE 2:\nAnswer 2"
        )

        # Submit 2 requests quickly
        task1 = asyncio.create_task(
            batcher.execute_with_batching(uuid4(), "Prompt 1")
        )
        task2 = asyncio.create_task(
            batcher.execute_with_batching(uuid4(), "Prompt 2")
        )

        # Wait for both
        results = await asyncio.gather(task1, task2)

        # Should have called LLM once (batched)
        assert mock_llm_client.generate.call_count == 1

        # Should have 2 results
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_respects_max_batch_size(self, mock_llm_client):
        """Should not exceed max batch size"""
        batcher = RequestBatcher(mock_llm_client, max_batch_size=2, batch_window_ms=100, enabled=True)

        mock_llm_client.generate.return_value = MockLLMResponse(
            text="RESPONSE 1:\nAnswer 1\n\nRESPONSE 2:\nAnswer 2"
        )

        # Submit 3 requests
        tasks = [
            asyncio.create_task(batcher.execute_with_batching(uuid4(), f"Prompt {i}"))
            for i in range(3)
        ]

        await asyncio.gather(*tasks)

        # Should have called LLM twice (2 batches: 2 + 1)
        assert mock_llm_client.generate.call_count == 2


class TestPromptCombination:
    """Test prompt combination logic"""

    def test_combine_prompts_format(self):
        """Combined prompt should have correct format"""
        client = Mock()
        batcher = RequestBatcher(client)

        batch = [
            BatchedRequest(uuid4(), "Prompt 1", asyncio.Future()),
            BatchedRequest(uuid4(), "Prompt 2", asyncio.Future()),
        ]

        combined = batcher._combine_prompts(batch)

        assert "--- PROMPT 1" in combined
        assert "--- PROMPT 2" in combined
        assert "Prompt 1" in combined
        assert "Prompt 2" in combined
        assert "--- END PROMPTS ---" in combined
        assert "RESPONSE 1:" in combined

    def test_combine_prompts_includes_atom_ids(self):
        """Combined prompt should include atom IDs"""
        client = Mock()
        batcher = RequestBatcher(client)

        atom_id = uuid4()
        batch = [BatchedRequest(atom_id, "Prompt 1", asyncio.Future())]

        combined = batcher._combine_prompts(batch)

        assert str(atom_id) in combined


class TestResponseParsing:
    """Test response parsing logic"""

    def test_parse_batched_response_single(self):
        """Should parse single response correctly"""
        client = Mock()
        batcher = RequestBatcher(client)

        response_text = "RESPONSE 1:\nThis is the answer"

        responses = batcher._parse_batched_response(response_text, 1)

        assert len(responses) == 1
        assert responses[0] == "This is the answer"

    def test_parse_batched_response_multiple(self):
        """Should parse multiple responses correctly"""
        client = Mock()
        batcher = RequestBatcher(client)

        response_text = "RESPONSE 1:\nAnswer 1\n\nRESPONSE 2:\nAnswer 2\n\nRESPONSE 3:\nAnswer 3"

        responses = batcher._parse_batched_response(response_text, 3)

        assert len(responses) == 3
        assert responses[0] == "Answer 1"
        assert responses[1] == "Answer 2"
        assert responses[2] == "Answer 3"

    def test_parse_batched_response_multiline(self):
        """Should handle multiline responses"""
        client = Mock()
        batcher = RequestBatcher(client)

        response_text = "RESPONSE 1:\nLine 1\nLine 2\nLine 3\n\nRESPONSE 2:\nAnother response"

        responses = batcher._parse_batched_response(response_text, 2)

        assert len(responses) == 2
        assert "Line 1\nLine 2\nLine 3" in responses[0]

    def test_parse_batched_response_pads_missing(self):
        """Should pad with empty strings if responses missing"""
        client = Mock()
        batcher = RequestBatcher(client)

        response_text = "RESPONSE 1:\nAnswer 1"

        # Expect 3 responses but only got 1
        responses = batcher._parse_batched_response(response_text, 3)

        assert len(responses) == 3
        assert responses[0] == "Answer 1"
        assert responses[1] == ""
        assert responses[2] == ""


@pytest.mark.asyncio
class TestFutureResolution:
    """Test future resolution logic"""

    async def test_futures_resolved_correctly(self, mock_llm_client):
        """Each request's future should be resolved with correct response"""
        batcher = RequestBatcher(mock_llm_client, max_batch_size=5, batch_window_ms=100, enabled=True)

        mock_llm_client.generate.return_value = MockLLMResponse(
            text="RESPONSE 1:\nAnswer A\n\nRESPONSE 2:\nAnswer B"
        )

        # Submit 2 requests concurrently
        task1 = asyncio.create_task(batcher.execute_with_batching(uuid4(), "Prompt 1"))
        task2 = asyncio.create_task(batcher.execute_with_batching(uuid4(), "Prompt 2"))

        result1, result2 = await asyncio.gather(task1, task2)

        # Each should get correct response
        assert "Answer A" in result1 or "Answer B" in result1
        assert result1 != result2  # Should be different responses

    async def test_futures_fail_on_exception(self, mock_llm_client):
        """Futures should be failed if batch processing fails"""
        batcher = RequestBatcher(mock_llm_client, max_batch_size=5, batch_window_ms=100, enabled=True)

        mock_llm_client.generate.side_effect = Exception("LLM error")

        # Submit request
        with pytest.raises(Exception, match="LLM error"):
            await batcher.execute_with_batching(uuid4(), "Prompt 1")


@pytest.mark.asyncio
class TestMetricsEmission:
    """Test metrics emission"""

    async def test_emits_batch_size_metric(self, mock_llm_client):
        """Should emit batch size metric"""
        batcher = RequestBatcher(mock_llm_client, max_batch_size=5, batch_window_ms=100, enabled=True)

        mock_llm_client.generate.return_value = MockLLMResponse(
            text="RESPONSE 1:\nAnswer 1\n\nRESPONSE 2:\nAnswer 2"
        )

        with patch.object(batcher, "_emit_batch_metrics") as mock_emit:
            # Submit 2 requests
            task1 = asyncio.create_task(
                batcher.execute_with_batching(uuid4(), "Prompt 1")
            )
            task2 = asyncio.create_task(
                batcher.execute_with_batching(uuid4(), "Prompt 2")
            )

            await asyncio.gather(task1, task2)

            # Should emit batch size = 2
            mock_emit.assert_called_once_with(2)

    async def test_emits_requests_processed_metric(self, mock_llm_client):
        """Should emit requests processed metric"""
        batcher = RequestBatcher(mock_llm_client, max_batch_size=5, batch_window_ms=100, enabled=True)

        mock_llm_client.generate.return_value = MockLLMResponse(
            text="RESPONSE 1:\nAnswer 1\n\nRESPONSE 2:\nAnswer 2\n\nRESPONSE 3:\nAnswer 3"
        )

        with patch.object(batcher, "_emit_batch_metrics") as mock_emit:
            # Submit 3 requests
            tasks = [
                asyncio.create_task(batcher.execute_with_batching(uuid4(), f"Prompt {i}"))
                for i in range(3)
            ]

            await asyncio.gather(*tasks)

            # Should emit batch size = 3
            mock_emit.assert_called_once_with(3)
