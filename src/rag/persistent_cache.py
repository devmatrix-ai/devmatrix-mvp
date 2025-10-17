"""
Persistent Embedding Cache

Provides persistent caching of query embeddings to improve RAG performance.
Supports cache warming, intelligent invalidation, and usage statistics.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import sqlite3
from threading import Lock

from ..observability import get_logger

logger = get_logger("rag.persistent_cache")


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    embedding: List[float]
    query: str
    created_at: float
    last_accessed: float
    access_count: int
    embedding_time_ms: float


@dataclass
class CacheStats:
    """Cache statistics."""

    total_entries: int
    total_hits: int
    total_misses: int
    hit_rate: float
    avg_embedding_time_saved_ms: float
    total_time_saved_ms: float
    cache_size_mb: float
    oldest_entry_age_hours: float
    most_accessed_queries: List[Tuple[str, int]]


class PersistentEmbeddingCache:
    """
    Persistent cache for query embeddings.

    Features:
    - SQLite-based persistent storage
    - Thread-safe operations
    - Automatic cache warming
    - LRU eviction policy
    - Usage statistics tracking
    """

    def __init__(
        self,
        cache_dir: str = ".cache/rag",
        max_entries: int = 10000,
        ttl_days: int = 30,
        enable_stats: bool = True,
    ):
        """
        Initialize persistent cache.

        Args:
            cache_dir: Directory for cache database
            max_entries: Maximum number of cache entries
            ttl_days: Time-to-live for cache entries in days
            enable_stats: Enable statistics tracking
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "embeddings.db"
        self.max_entries = max_entries
        self.ttl = timedelta(days=ttl_days)
        self.enable_stats = enable_stats

        self.lock = Lock()

        # Initialize database
        self._init_database()

        # Load stats
        self.stats = self._load_stats()

        logger.info(
            "Persistent cache initialized",
            db_path=str(self.db_path),
            max_entries=max_entries,
            ttl_days=ttl_days,
        )

    def _init_database(self):
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    key TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    query TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    embedding_time_ms REAL NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_last_accessed
                ON embeddings(last_accessed)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_access_count
                ON embeddings(access_count DESC)
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            conn.commit()

    def _generate_key(self, query: str, model: str = "default") -> str:
        """Generate cache key from query and model."""
        content = f"{model}:{query}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, query: str, model: str = "default") -> Optional[List[float]]:
        """
        Get embedding from cache.

        Args:
            query: Query string
            model: Embedding model identifier

        Returns:
            Cached embedding or None if not found
        """
        key = self._generate_key(query, model)

        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT embedding, created_at
                    FROM embeddings
                    WHERE key = ?
                    """,
                    (key,),
                )

                row = cursor.fetchone()

                if row is None:
                    # Cache miss
                    if self.enable_stats:
                        self._update_stat("total_misses", increment=1)

                    return None

                embedding_json, created_at = row

                # Check TTL
                age = time.time() - created_at

                if age > self.ttl.total_seconds():
                    # Entry expired
                    conn.execute("DELETE FROM embeddings WHERE key = ?", (key,))
                    conn.commit()

                    if self.enable_stats:
                        self._update_stat("total_misses", increment=1)

                    logger.debug("Cache entry expired", query=query[:50], age_days=age / 86400)

                    return None

                # Cache hit - update access stats
                conn.execute(
                    """
                    UPDATE embeddings
                    SET last_accessed = ?,
                        access_count = access_count + 1
                    WHERE key = ?
                    """,
                    (time.time(), key),
                )

                conn.commit()

                if self.enable_stats:
                    self._update_stat("total_hits", increment=1)

                embedding = json.loads(embedding_json)

                logger.debug("Cache hit", query=query[:50], age_seconds=age)

                return embedding

    def put(
        self,
        query: str,
        embedding: List[float],
        model: str = "default",
        embedding_time_ms: float = 0.0,
    ):
        """
        Store embedding in cache.

        Args:
            query: Query string
            embedding: Embedding vector
            model: Embedding model identifier
            embedding_time_ms: Time taken to generate embedding
        """
        key = self._generate_key(query, model)

        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Check if we need to evict entries
                cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
                count = cursor.fetchone()[0]

                if count >= self.max_entries:
                    self._evict_lru(conn)

                # Insert or replace entry
                now = time.time()

                conn.execute(
                    """
                    INSERT OR REPLACE INTO embeddings
                    (key, embedding, query, created_at, last_accessed, access_count, embedding_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        json.dumps(embedding),
                        query,
                        now,
                        now,
                        1,
                        embedding_time_ms,
                    ),
                )

                conn.commit()

                logger.debug("Cache put", query=query[:50])

    def _evict_lru(self, conn: sqlite3.Connection):
        """Evict least recently used entries."""
        # Remove 10% of oldest entries
        evict_count = max(1, self.max_entries // 10)

        conn.execute(
            """
            DELETE FROM embeddings
            WHERE key IN (
                SELECT key FROM embeddings
                ORDER BY last_accessed ASC
                LIMIT ?
            )
            """,
            (evict_count,),
        )

        logger.info(f"Evicted {evict_count} LRU cache entries")

    def warm_cache(self, queries: List[str], embed_func, model: str = "default"):
        """
        Warm cache with frequently used queries.

        Args:
            queries: List of queries to pre-compute
            embed_func: Function to generate embeddings
            model: Embedding model identifier
        """
        logger.info(f"Warming cache with {len(queries)} queries...")

        warmed = 0
        skipped = 0

        for query in queries:
            # Check if already cached
            if self.get(query, model) is not None:
                skipped += 1
                continue

            # Generate and cache embedding
            start = time.time()
            embedding = embed_func(query)
            duration = (time.time() - start) * 1000

            self.put(query, embedding, model, embedding_time_ms=duration)

            warmed += 1

        logger.info(
            f"Cache warming complete",
            warmed=warmed,
            skipped=skipped,
            total=len(queries),
        )

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Total entries
                cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
                total_entries = cursor.fetchone()[0]

                # Hits and misses
                total_hits = self._get_stat("total_hits")
                total_misses = self._get_stat("total_misses")

                total_requests = total_hits + total_misses
                hit_rate = total_hits / total_requests if total_requests > 0 else 0.0

                # Average embedding time saved
                cursor = conn.execute(
                    """
                    SELECT AVG(embedding_time_ms), SUM(embedding_time_ms * access_count)
                    FROM embeddings
                    """
                )

                row = cursor.fetchone()
                avg_time_saved = row[0] or 0.0
                total_time_saved = (row[1] or 0.0) - total_entries * avg_time_saved

                # Cache size
                cache_size_mb = self.db_path.stat().st_size / (1024 * 1024)

                # Oldest entry age
                cursor = conn.execute(
                    """
                    SELECT MIN(created_at) FROM embeddings
                    """
                )

                oldest = cursor.fetchone()[0]

                if oldest:
                    oldest_age_hours = (time.time() - oldest) / 3600
                else:
                    oldest_age_hours = 0.0

                # Most accessed queries
                cursor = conn.execute(
                    """
                    SELECT query, access_count
                    FROM embeddings
                    ORDER BY access_count DESC
                    LIMIT 10
                    """
                )

                most_accessed = cursor.fetchall()

                return CacheStats(
                    total_entries=total_entries,
                    total_hits=total_hits,
                    total_misses=total_misses,
                    hit_rate=hit_rate,
                    avg_embedding_time_saved_ms=avg_time_saved,
                    total_time_saved_ms=total_time_saved,
                    cache_size_mb=cache_size_mb,
                    oldest_entry_age_hours=oldest_age_hours,
                    most_accessed_queries=most_accessed,
                )

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
                count = cursor.fetchone()[0]

                conn.execute("DELETE FROM embeddings")
                conn.commit()

                logger.info(f"Cache cleared", entries_removed=count)

                return count

    def invalidate_pattern(self, pattern: str):
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: SQL LIKE pattern for query matching
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM embeddings
                    WHERE query LIKE ?
                    """,
                    (pattern,),
                )

                count = cursor.fetchone()[0]

                conn.execute(
                    """
                    DELETE FROM embeddings
                    WHERE query LIKE ?
                    """,
                    (pattern,),
                )

                conn.commit()

                logger.info(
                    f"Cache invalidation",
                    pattern=pattern,
                    entries_removed=count,
                )

                return count

    def _update_stat(self, key: str, increment: int = 0, value: Any = None):
        """Update a statistics value."""
        if not self.enable_stats:
            return

        with sqlite3.connect(self.db_path) as conn:
            if increment:
                # Increment existing value
                cursor = conn.execute(
                    "SELECT value FROM stats WHERE key = ?", (key,)
                )

                row = cursor.fetchone()
                current = int(row[0]) if row else 0
                new_value = current + increment

                conn.execute(
                    """
                    INSERT OR REPLACE INTO stats (key, value)
                    VALUES (?, ?)
                    """,
                    (key, str(new_value)),
                )

            elif value is not None:
                # Set absolute value
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stats (key, value)
                    VALUES (?, ?)
                    """,
                    (key, str(value)),
                )

            conn.commit()

    def _get_stat(self, key: str, default: Any = 0) -> Any:
        """Get a statistics value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM stats WHERE key = ?", (key,))

            row = cursor.fetchone()

            if row:
                # Try to convert to int/float
                try:
                    return int(row[0])
                except ValueError:
                    try:
                        return float(row[0])
                    except ValueError:
                        return row[0]

            return default

    def _load_stats(self) -> Dict[str, Any]:
        """Load all statistics."""
        stats = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key, value FROM stats")

            for key, value in cursor.fetchall():
                try:
                    stats[key] = int(value)
                except ValueError:
                    try:
                        stats[key] = float(value)
                    except ValueError:
                        stats[key] = value

        return stats

    def export_frequent_queries(self, top_n: int = 100) -> List[Tuple[str, int]]:
        """
        Export most frequently accessed queries.

        Args:
            top_n: Number of top queries to export

        Returns:
            List of (query, access_count) tuples
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT query, access_count
                FROM embeddings
                ORDER BY access_count DESC
                LIMIT ?
                """,
                (top_n,),
            )

            return cursor.fetchall()


# Global cache instance (singleton)
_cache_instance: Optional[PersistentEmbeddingCache] = None


def get_cache(
    cache_dir: str = ".cache/rag",
    max_entries: int = 10000,
    ttl_days: int = 30,
) -> PersistentEmbeddingCache:
    """
    Get or create global cache instance.

    Args:
        cache_dir: Directory for cache database
        max_entries: Maximum number of cache entries
        ttl_days: Time-to-live for cache entries in days

    Returns:
        Persistent cache instance
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = PersistentEmbeddingCache(
            cache_dir=cache_dir,
            max_entries=max_entries,
            ttl_days=ttl_days,
        )

    return _cache_instance
