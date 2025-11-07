"""
Streaming JSON Parser for incremental processing of LLM output.

Detects and extracts complete JSON objects from partial stream,
enabling real-time entity discovery and event emission.
"""

import json
import logging
from typing import Callable, Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class StreamingJSONParser:
    """
    Parser that detects and extracts complete JSON objects from a stream.

    Handles:
    - Nested objects and arrays
    - Escaped strings with quotes
    - Multiple consecutive JSON objects
    - Partial/incomplete JSON (buffered until complete)

    Usage:
        parser = StreamingJSONParser(
            entity_callback=lambda obj: print(f"Found: {obj}"),
            progress_callback=lambda p: print(f"Progress: {p}")
        )

        async for chunk in stream:
            objects = parser.process_chunk(chunk)
            for obj in objects:
                # obj is a complete, parsed JSON object
                pass
    """

    def __init__(
        self,
        entity_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        target_keys: Optional[List[str]] = None
    ):
        """
        Initialize parser.

        Args:
            entity_callback: Called when a complete JSON object is found
            progress_callback: Called with progress info (chunk_count, objects_found, etc.)
            target_keys: Optional list of keys to filter objects (e.g., ["phases", "tasks"])
        """
        self.buffer = ""
        self.entity_callback = entity_callback
        self.progress_callback = progress_callback
        self.target_keys = target_keys or []

        # Statistics
        self.chunk_count = 0
        self.objects_found = 0
        self.total_chars = 0

    def process_chunk(self, chunk: str) -> List[Dict[str, Any]]:
        """
        Process a chunk of text, extracting complete JSON objects.

        Args:
            chunk: Text chunk from stream

        Returns:
            List of complete JSON objects found in this chunk
        """
        self.buffer += chunk
        self.chunk_count += 1
        self.total_chars += len(chunk)

        # Try to extract complete objects
        extracted_objects = []

        while True:
            # Find potential JSON start (opening brace or bracket)
            obj_start = self._find_json_start()

            if obj_start == -1:
                # No JSON found, clear non-JSON prefix
                self.buffer = self.buffer[max(0, len(self.buffer) - 100):]
                break

            # Try to extract complete object from this position
            obj_end = self._find_json_end(obj_start)

            if obj_end == -1:
                # Incomplete object, wait for more chunks
                break

            # Extract and parse the object
            json_str = self.buffer[obj_start:obj_end + 1]

            try:
                obj = json.loads(json_str)

                # Filter if target_keys specified
                if not self.target_keys or self._matches_target_keys(obj):
                    extracted_objects.append(obj)
                    self.objects_found += 1

                    # Emit callback if provided
                    if self.entity_callback:
                        try:
                            self.entity_callback(obj)
                        except Exception as e:
                            logger.error(f"Error in entity callback: {e}")

                # Remove processed object from buffer
                self.buffer = self.buffer[obj_end + 1:].lstrip()

            except json.JSONDecodeError as e:
                # Invalid JSON, skip this position
                logger.debug(f"JSON decode error: {e}, skipping")
                self.buffer = self.buffer[obj_start + 1:]
                continue

        # Emit progress callback
        if self.progress_callback:
            try:
                self.progress_callback({
                    "chunk_count": self.chunk_count,
                    "objects_found": self.objects_found,
                    "total_chars": self.total_chars,
                    "buffer_size": len(self.buffer)
                })
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

        return extracted_objects

    def _find_json_start(self) -> int:
        """Find position of next JSON object start ('{' or '[')."""
        for i, char in enumerate(self.buffer):
            if char in ('{', '['):
                # Check it's not inside a string
                if not self._is_in_string(i):
                    return i
        return -1

    def _find_json_end(self, start: int) -> int:
        """Find position of matching closing brace/bracket."""
        if start >= len(self.buffer):
            return -1

        opening = self.buffer[start]
        closing = '}' if opening == '{' else ']'

        depth = 0
        i = start

        while i < len(self.buffer):
            char = self.buffer[i]

            # Handle escaped characters
            if i > 0 and self.buffer[i - 1] == '\\':
                i += 1
                continue

            # Handle strings
            if char == '"':
                # Find closing quote
                i += 1
                while i < len(self.buffer):
                    if self.buffer[i] == '"' and (i == 0 or self.buffer[i - 1] != '\\'):
                        break
                    i += 1
                i += 1
                continue

            # Track nesting depth
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return -1  # Incomplete object

    def _is_in_string(self, pos: int) -> bool:
        """Check if position is inside a quoted string."""
        in_string = False
        i = 0

        while i < pos and i < len(self.buffer):
            if self.buffer[i] == '"' and (i == 0 or self.buffer[i - 1] != '\\'):
                in_string = not in_string
            i += 1

        return in_string

    def _matches_target_keys(self, obj: Dict[str, Any]) -> bool:
        """Check if object contains any of the target keys."""
        if not self.target_keys:
            return True

        for key in self.target_keys:
            if key in obj:
                return True

        return False

    def finalize(self) -> List[Dict[str, Any]]:
        """
        Call when stream ends to attempt parsing remaining buffer.

        Returns:
            Any additional objects found in remaining buffer
        """
        remaining = []

        try:
            # Try to parse entire remaining buffer
            remaining_objects = json.loads(self.buffer)

            # Handle both single objects and arrays
            if isinstance(remaining_objects, list):
                remaining = remaining_objects
            else:
                remaining = [remaining_objects]

            for obj in remaining:
                if not self.target_keys or self._matches_target_keys(obj):
                    self.objects_found += 1
                    if self.entity_callback:
                        try:
                            self.entity_callback(obj)
                        except Exception as e:
                            logger.error(f"Error in finalize callback: {e}")

        except json.JSONDecodeError:
            # No valid JSON in remaining buffer
            if self.buffer.strip():
                logger.debug(f"Remaining buffer not valid JSON: {self.buffer[:100]}")

        return remaining

    def get_stats(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        return {
            "chunk_count": self.chunk_count,
            "objects_found": self.objects_found,
            "total_chars": self.total_chars,
            "buffer_size": len(self.buffer),
            "avg_chunk_size": self.total_chars / max(1, self.chunk_count),
            "objects_per_chunk": self.objects_found / max(1, self.chunk_count)
        }
