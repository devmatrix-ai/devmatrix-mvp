"""
Cognitive Cache for IR-Centric Code Generation.

Caches enhanced code indexed by IR semantics (flow_id, version, patterns)
rather than file paths. This enables:
- Cache hits across different files with same flow semantics
- Automatic invalidation when IR contracts change
- Learning from previous enhancement attempts

Part of Bug #143-160 IR-Centric Cognitive Code Generation.
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

# Try to import Flow for type hints, but don't fail if not available
try:
    from src.cognitive.ir.behavior_model import Flow
except ImportError:
    Flow = Any  # type: ignore


@dataclass
class CachedEnhancement:
    """
    Cached result of a cognitive enhancement.

    Stores the enhanced code along with metadata for validation
    and learning purposes.
    """
    # Cache identification
    cache_key: str
    flow_id: str

    # Enhanced code
    enhanced_code: str
    original_code: str

    # Applied patterns
    anti_patterns_applied: List[str] = field(default_factory=list)
    constraint_types: List[str] = field(default_factory=list)

    # IR contract info for validation
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)

    # Metadata
    ir_version: str = "1.0.0"
    cognitive_pass_version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    # Validation state
    validated: bool = False
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "cache_key": self.cache_key,
            "flow_id": self.flow_id,
            "enhanced_code": self.enhanced_code,
            "original_code": self.original_code,
            "anti_patterns_applied": self.anti_patterns_applied,
            "constraint_types": self.constraint_types,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "ir_version": self.ir_version,
            "cognitive_pass_version": self.cognitive_pass_version,
            "created_at": self.created_at.isoformat(),
            "hit_count": self.hit_count,
            "last_accessed": self.last_accessed.isoformat(),
            "validated": self.validated,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedEnhancement":
        """Deserialize from dictionary."""
        data = data.copy()
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_accessed" in data and isinstance(data["last_accessed"], str):
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        return cls(**data)


class CognitiveCache:
    """
    IR-based cache for cognitive code generation.

    Cache keys are computed from IR semantics rather than file paths:
    - flow_id: Unique identifier for the flow
    - ir_version: Version of the IR contract
    - anti_pattern_ids: Sorted list of patterns being addressed
    - cognitive_pass_version: Version of the cognitive pass

    This enables semantic caching where the same enhancement can be
    reused across different files with equivalent IR flows.

    Example:
        cache = CognitiveCache()

        # Compute cache key from IR flow
        cache_key = cache.compute_cache_key(
            flow_id="add_item_to_cart",
            ir_version="1.0.0",
            anti_pattern_ids=["missing_validation", "no_error_handling"],
            cognitive_pass_version="1.0.0"
        )

        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return cached.enhanced_code

        # Store enhancement
        cache.store(cache_key, enhancement)
    """

    # Default cache settings
    DEFAULT_TTL_HOURS = 24
    DEFAULT_MAX_SIZE = 1000

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        max_size: int = DEFAULT_MAX_SIZE,
        cognitive_pass_version: str = "1.0.0",
    ):
        """
        Initialize the cognitive cache.

        Args:
            storage_path: Optional path for persistent storage
            ttl_hours: Time-to-live for cache entries in hours
            max_size: Maximum number of cached entries
            cognitive_pass_version: Current version of cognitive pass
        """
        self._cache: Dict[str, CachedEnhancement] = {}
        self._storage_path = storage_path
        self._ttl = timedelta(hours=ttl_hours)
        self._max_size = max_size
        self._cognitive_pass_version = cognitive_pass_version

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Load from storage if path provided
        if storage_path and storage_path.exists():
            self._load_from_storage()

    def compute_cache_key(
        self,
        flow_id: str,
        ir_version: str = "1.0.0",
        anti_pattern_ids: Optional[List[str]] = None,
        cognitive_pass_version: Optional[str] = None,
    ) -> str:
        """
        Compute cache key from IR semantics.

        The key is a hash of:
        - flow_id: Identifies the semantic flow
        - ir_version: Contract version
        - anti_pattern_ids: Patterns being addressed
        - cognitive_pass_version: Pass version

        Args:
            flow_id: Unique flow identifier
            ir_version: IR contract version
            anti_pattern_ids: List of pattern IDs being addressed
            cognitive_pass_version: Version of cognitive pass

        Returns:
            SHA256-based cache key string
        """
        anti_patterns = sorted(anti_pattern_ids or [])
        pass_version = cognitive_pass_version or self._cognitive_pass_version

        key_components = {
            "flow_id": flow_id,
            "ir_version": ir_version,
            "anti_patterns": anti_patterns,
            "pass_version": pass_version,
        }

        key_str = json.dumps(key_components, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def compute_cache_key_from_flow(
        self,
        flow: "Flow",
        anti_pattern_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Compute cache key directly from an IR Flow object.

        Args:
            flow: IR Flow object with semantic information
            anti_pattern_ids: List of pattern IDs being addressed

        Returns:
            SHA256-based cache key string
        """
        flow_id = flow.get_flow_id() if hasattr(flow, 'get_flow_id') else flow.name
        version = getattr(flow, 'version', '1.0.0')

        return self.compute_cache_key(
            flow_id=flow_id,
            ir_version=version,
            anti_pattern_ids=anti_pattern_ids,
        )

    def get(self, cache_key: str) -> Optional[CachedEnhancement]:
        """
        Retrieve cached enhancement by key.

        Updates access statistics and validates TTL.

        Args:
            cache_key: The cache key to look up

        Returns:
            CachedEnhancement if found and valid, None otherwise
        """
        if cache_key not in self._cache:
            self._misses += 1
            return None

        cached = self._cache[cache_key]

        # Check TTL
        if datetime.now() - cached.created_at > self._ttl:
            self._evict(cache_key)
            self._misses += 1
            return None

        # Update access stats
        cached.hit_count += 1
        cached.last_accessed = datetime.now()
        self._hits += 1

        return cached

    def store(
        self,
        cache_key: str,
        flow_id: str,
        enhanced_code: str,
        original_code: str,
        anti_patterns_applied: Optional[List[str]] = None,
        constraint_types: Optional[List[str]] = None,
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
        ir_version: str = "1.0.0",
    ) -> CachedEnhancement:
        """
        Store an enhancement in the cache.

        Args:
            cache_key: Pre-computed cache key
            flow_id: Flow identifier
            enhanced_code: The enhanced code to cache
            original_code: Original code before enhancement
            anti_patterns_applied: Patterns that were addressed
            constraint_types: Constraint types involved
            preconditions: IR preconditions for validation
            postconditions: IR postconditions for validation
            ir_version: IR contract version

        Returns:
            The stored CachedEnhancement
        """
        # Evict if at capacity
        if len(self._cache) >= self._max_size:
            self._evict_lru()

        cached = CachedEnhancement(
            cache_key=cache_key,
            flow_id=flow_id,
            enhanced_code=enhanced_code,
            original_code=original_code,
            anti_patterns_applied=anti_patterns_applied or [],
            constraint_types=constraint_types or [],
            preconditions=preconditions or [],
            postconditions=postconditions or [],
            ir_version=ir_version,
            cognitive_pass_version=self._cognitive_pass_version,
        )

        self._cache[cache_key] = cached

        # Persist if storage configured
        if self._storage_path:
            self._save_to_storage()

        return cached

    def invalidate(self, cache_key: str) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            cache_key: Key to invalidate

        Returns:
            True if entry was found and removed
        """
        return self._evict(cache_key)

    def invalidate_by_flow(self, flow_id: str) -> int:
        """
        Invalidate all entries for a specific flow.

        Useful when IR contract changes.

        Args:
            flow_id: Flow identifier

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = [
            key for key, cached in self._cache.items()
            if cached.flow_id == flow_id
        ]

        for key in keys_to_remove:
            self._evict(key)

        return len(keys_to_remove)

    def invalidate_by_version(self, ir_version: str) -> int:
        """
        Invalidate all entries with a specific IR version.

        Useful for bulk invalidation on IR updates.

        Args:
            ir_version: IR version to invalidate

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = [
            key for key, cached in self._cache.items()
            if cached.ir_version == ir_version
        ]

        for key in keys_to_remove:
            self._evict(key)

        return len(keys_to_remove)

    def mark_validated(
        self,
        cache_key: str,
        passed: bool,
        errors: Optional[List[str]] = None,
    ) -> bool:
        """
        Mark a cached entry as validated.

        Args:
            cache_key: Cache key
            passed: Whether validation passed
            errors: List of validation errors if failed

        Returns:
            True if entry was found and updated
        """
        if cache_key not in self._cache:
            return False

        cached = self._cache[cache_key]
        cached.validated = True
        cached.validation_passed = passed
        cached.validation_errors = errors or []

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        validated_count = sum(1 for c in self._cache.values() if c.validated)
        passed_count = sum(1 for c in self._cache.values() if c.validation_passed)

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "validated_entries": validated_count,
            "validation_passed": passed_count,
            "cognitive_pass_version": self._cognitive_pass_version,
        }

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()

        if self._storage_path and self._storage_path.exists():
            self._storage_path.unlink()

        return count

    def _evict(self, cache_key: str) -> bool:
        """Remove a specific cache entry."""
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._evictions += 1
            return True
        return False

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        self._evict(lru_key)

    def _load_from_storage(self) -> None:
        """Load cache from persistent storage."""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, 'r') as f:
                data = json.load(f)

            for entry in data.get("entries", []):
                cached = CachedEnhancement.from_dict(entry)
                # Skip expired entries
                if datetime.now() - cached.created_at <= self._ttl:
                    self._cache[cached.cache_key] = cached

        except (json.JSONDecodeError, KeyError, TypeError):
            # Invalid storage, start fresh
            self._cache.clear()

    def _save_to_storage(self) -> None:
        """Save cache to persistent storage."""
        if not self._storage_path:
            return

        # Ensure directory exists
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self._cognitive_pass_version,
            "entries": [c.to_dict() for c in self._cache.values()],
        }

        with open(self._storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, cache_key: str) -> bool:
        return cache_key in self._cache
