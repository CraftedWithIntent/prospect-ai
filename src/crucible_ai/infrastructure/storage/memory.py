"""In-memory cache storage backend."""

from typing import Any
from crucible_ai.domain.types import CacheEntry
from crucible_ai.infrastructure.storage.base import CacheStorageBackend
from crucible_ai.core.similarity import cosine_similarity


class MemoryCacheBackend(CacheStorageBackend):
    """Simple in-memory cache (ephemeral, per-process)."""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._exact_cache: dict[str, CacheEntry] = {}
        self._embedding_cache: list[tuple[str, CacheEntry]] = []

    async def get_by_hash(self, hash_key: str) -> CacheEntry | None:
        """O(1) exact match lookup."""
        return self._exact_cache.get(hash_key)

    async def search_semantic(
        self, embedding: list[float], threshold: float, limit: int = 10
    ) -> list[tuple[CacheEntry, float]]:
        """O(n) semantic search with threshold filtering."""
        results: list[tuple[CacheEntry, float]] = []

        for _, cached_entry in self._embedding_cache:
            score = cosine_similarity(embedding, cached_entry.embedding_vector)
            if score >= threshold:
                results.append((cached_entry, score))

        # Sort by score descending and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def store(self, entry: CacheEntry) -> None:
        """Store entry in both exact and semantic caches."""
        if len(self._exact_cache) >= self.max_entries:
            # Simple FIFO eviction
            oldest_key = next(iter(self._exact_cache))
            del self._exact_cache[oldest_key]
            self._embedding_cache = [
                (k, e) for k, e in self._embedding_cache if k != oldest_key
            ]

        self._exact_cache[entry.request_hash] = entry
        self._embedding_cache.append((entry.request_hash, entry))

    async def delete_by_hash(self, hash_key: str) -> bool:
        """Remove entry from caches."""
        if hash_key in self._exact_cache:
            del self._exact_cache[hash_key]
            self._embedding_cache = [
                (k, e) for k, e in self._embedding_cache if k != hash_key
            ]
            return True
        return False

    async def invalidate_by_tag(self, tag: str) -> int:
        """Phase 2: Tag-based invalidation (stub for MVP)."""
        # Phase 1: Not implemented
        return 0

    async def stats(self) -> dict[str, Any]:
        """Return storage statistics."""
        return {
            "backend": "memory",
            "entries": len(self._exact_cache),
            "max_entries": self.max_entries,
        }
