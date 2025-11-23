"""
Prompt Cache Manager for Anthropic's Prompt Caching

Implements Anthropic's prompt caching feature (90% discount on cached tokens).
This is CRITICAL for MVP cost reduction (32% overall savings).

How it works:
- Mark cacheable sections (system prompt, discovery, RAG examples, schema)
- Anthropic caches these sections for 5 minutes
- Subsequent requests using same cacheable content get 90% discount

References:
- https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
"""

import logging
import hashlib
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


def json_serializable(obj):
    """Helper to serialize non-JSON types like UUID."""
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@dataclass
class CacheableContext:
    """
    Cacheable context section.

    This will be marked for Anthropic's caching system.
    """
    key: str  # Unique identifier
    content: str  # Content to cache
    type: str  # Type: system, discovery, rag, schema, etc.
    estimated_tokens: int  # Estimated token count


class PromptCacheManager:
    """
    Manages Anthropic's prompt caching for cost optimization.

    MVP Strategy:
    - Cache system prompts (3K tokens)
    - Cache discovery documents (8K tokens)
    - Cache RAG examples (20K tokens)
    - Cache database schema (3K tokens)
    Total cacheable: ~34K tokens

    Savings: 90% on cached tokens = 58% reduction in task execution cost

    Usage:
        cache_mgr = PromptCacheManager()

        # Build cacheable context
        cacheable = cache_mgr.build_cacheable_context(
            system_prompt="You are...",
            discovery_doc=discovery.to_dict(),
            rag_examples=rag_examples,
            db_schema=schema
        )

        # Use in API call
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            system=cache_mgr.format_system_for_caching(cacheable),
            messages=[...]
        )
    """

    def __init__(self):
        """Initialize prompt cache manager"""
        self.cache_markers = {}  # Track what we've cached
        self.cache_stats = {
            "cache_writes": 0,
            "cache_reads": 0,
            "tokens_cached": 0
        }

    def build_cacheable_context(
        self,
        system_prompt: Optional[str] = None,
        discovery_doc: Optional[Dict] = None,
        rag_examples: Optional[List[Dict]] = None,
        db_schema: Optional[Dict] = None,
        project_structure: Optional[Dict] = None
    ) -> List[CacheableContext]:
        """
        Build list of cacheable context sections.

        Args:
            system_prompt: System instructions (3K tokens)
            discovery_doc: Discovery document (8K tokens)
            rag_examples: RAG examples (20K tokens)
            db_schema: Database schema (3K tokens)
            project_structure: Project structure (2K tokens)

        Returns:
            List of CacheableContext objects
        """
        cacheable_sections = []

        # 1. System prompt (always cacheable)
        if system_prompt:
            cacheable_sections.append(CacheableContext(
                key="system_prompt",
                content=system_prompt,
                type="system",
                estimated_tokens=self._estimate_tokens(system_prompt)
            ))

        # 2. Discovery document
        if discovery_doc:
            discovery_str = json.dumps(discovery_doc, indent=2, default=json_serializable)
            cacheable_sections.append(CacheableContext(
                key=f"discovery_{self._hash_content(discovery_str)}",
                content=discovery_str,
                type="discovery",
                estimated_tokens=self._estimate_tokens(discovery_str)
            ))

        # 3. RAG examples (highly cacheable - same for similar tasks)
        if rag_examples:
            rag_str = json.dumps(rag_examples, indent=2, default=json_serializable)
            cacheable_sections.append(CacheableContext(
                key=f"rag_{self._hash_content(rag_str)}",
                content=rag_str,
                type="rag",
                estimated_tokens=self._estimate_tokens(rag_str)
            ))

        # 4. Database schema
        if db_schema:
            schema_str = json.dumps(db_schema, indent=2, default=json_serializable)
            cacheable_sections.append(CacheableContext(
                key=f"schema_{self._hash_content(schema_str)}",
                content=schema_str,
                type="schema",
                estimated_tokens=self._estimate_tokens(schema_str)
            ))

        # 5. Project structure
        if project_structure:
            structure_str = json.dumps(project_structure, indent=2, default=json_serializable)
            cacheable_sections.append(CacheableContext(
                key=f"structure_{self._hash_content(structure_str)}",
                content=structure_str,
                type="structure",
                estimated_tokens=self._estimate_tokens(structure_str)
            ))

        return cacheable_sections

    def format_system_for_caching(
        self,
        cacheable_sections: List[CacheableContext]
    ) -> List[Dict[str, Any]]:
        """
        Format system parameter for Anthropic API with cache markers.

        Anthropic expects system as array of dicts with cache_control.

        Args:
            cacheable_sections: List of CacheableContext objects

        Returns:
            Formatted system array for API
        """
        system_blocks = []

        for section in cacheable_sections:
            # Add content block with cache control marker
            system_blocks.append({
                "type": "text",
                "text": f"# {section.type.upper()}\n{section.content}",
                "cache_control": {"type": "ephemeral"}  # ← Cache marker
            })

            # Track cache write
            self._track_cache_write(section)

        return system_blocks

    def format_prompt_with_caching(
        self,
        cacheable_context: List[CacheableContext],
        variable_prompt: str
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Format complete prompt with caching.

        Separates cacheable (system) from variable (messages).

        Args:
            cacheable_context: List of cacheable sections
            variable_prompt: Variable prompt for this specific task

        Returns:
            Tuple of (system, messages) for API
        """
        # System with cache markers
        system = self.format_system_for_caching(cacheable_context)

        # Messages with variable content
        messages = [{
            "role": "user",
            "content": variable_prompt
        }]

        return system, messages

    def extract_cache_stats_from_response(
        self,
        response: Any
    ) -> Dict[str, int]:
        """
        Extract cache statistics from Anthropic response.

        Args:
            response: Anthropic API response object

        Returns:
            Dict with cache_creation_input_tokens, cache_read_input_tokens
        """
        usage = response.usage

        stats = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0)
        }

        # Track cache reads
        if stats["cache_read_input_tokens"] > 0:
            self.cache_stats["cache_reads"] += 1
            logger.debug(
                f"Cache HIT: {stats['cache_read_input_tokens']} tokens from cache "
                f"(saved {stats['cache_read_input_tokens'] * 0.90 / 1_000_000 * 3:.4f} USD)"
            )

        return stats

    def calculate_savings(
        self,
        uncached_input: int,
        cached_input: int,
        output_tokens: int,
        model_pricing: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate cost savings from prompt caching.

        Args:
            uncached_input: Input tokens not cached
            cached_input: Input tokens from cache
            output_tokens: Output tokens
            model_pricing: Dict with input/output/input_cached prices

        Returns:
            Dict with cost breakdown and savings
        """
        # Cost without caching
        cost_without_cache = (
            (uncached_input + cached_input) / 1_000_000 * model_pricing["input"] +
            output_tokens / 1_000_000 * model_pricing["output"]
        )

        # Cost with caching
        uncached_cost = uncached_input / 1_000_000 * model_pricing["input"]
        cached_cost = cached_input / 1_000_000 * model_pricing["input_cached"]
        output_cost = output_tokens / 1_000_000 * model_pricing["output"]
        cost_with_cache = uncached_cost + cached_cost + output_cost

        savings = cost_without_cache - cost_with_cache
        savings_percent = (savings / cost_without_cache * 100) if cost_without_cache > 0 else 0

        return {
            "cost_without_cache": cost_without_cache,
            "cost_with_cache": cost_with_cache,
            "savings": savings,
            "savings_percent": savings_percent,
            "cached_tokens": cached_input,
            "uncached_tokens": uncached_input,
            "output_tokens": output_tokens
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dict with cache_writes, cache_reads, hit_rate, tokens_cached
        """
        total_requests = self.cache_stats["cache_writes"]
        cache_reads = self.cache_stats["cache_reads"]

        hit_rate = (cache_reads / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_writes": self.cache_stats["cache_writes"],
            "cache_reads": cache_reads,
            "hit_rate_percent": hit_rate,
            "total_tokens_cached": self.cache_stats["tokens_cached"],
            "cache_markers": len(self.cache_markers)
        }

    def _track_cache_write(self, section: CacheableContext):
        """Track cache write"""
        self.cache_markers[section.key] = True
        self.cache_stats["cache_writes"] += 1
        self.cache_stats["tokens_cached"] += section.estimated_tokens

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.

        Rough estimation: 1 token ≈ 4 characters
        """
        return len(text) // 4

    def _hash_content(self, content: str) -> str:
        """Generate hash for content"""
        return hashlib.md5(content.encode()).hexdigest()[:8]


# Example usage for documentation
if __name__ == "__main__":
    # Example: Building cacheable context
    cache_mgr = PromptCacheManager()

    cacheable = cache_mgr.build_cacheable_context(
        system_prompt="You are an expert software architect...",
        discovery_doc={
            "domain": "User Management",
            "bounded_contexts": ["Auth", "Users"]
        },
        rag_examples=[
            {"task": "Create User model", "code": "class User: ..."}
        ],
        db_schema={"tables": ["users", "roles"]}
    )

    # Format for API
    system, messages = cache_mgr.format_prompt_with_caching(
        cacheable_context=cacheable,
        variable_prompt="Create a User API endpoint with authentication"
    )

    print("System blocks with cache markers:")
    print(json.dumps(system, indent=2, default=json_serializable))

    print("\nEstimated cacheable tokens:")
    print(sum(s.estimated_tokens for s in cacheable))
