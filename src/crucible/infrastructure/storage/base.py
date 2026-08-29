"""Abstract base class for pluggable cache storage backends."""

from abc import ABC, abstractmethod
from crucible.domain.types import CacheEntry


class CacheStorageBackend(ABC):
    """
    Abstract cache storage interface.
    
    Implementations: Memory, SQLite-vec, Redis, Qdrant
    """

    @abstractmethod
    async def get_by_hash(self, hash_key: str) -> CacheEntry | None:
        """Retrieve cached entry by SHA-256 hash (L1 exact match)."""
        pass

    @abstractmethod
    async def search_semantic(
        self, embedding: list[float], threshold: float, limit: int = 10
    ) -> list[tuple[CacheEntry, float]]:
        """
        Semantic vector search (L2 similarity match).
        
        Returns: List of (CacheEntry, similarity_score) tuples sorted by score desc.
        """
        pass

    @abstractmethod
    async def store(self, entry: CacheEntry) -> None:
        """Store new cache entry."""
        pass

    @abstractmethod
    async def delete_by_hash(self, hash_key: str) -> bool:
        """Delete cached entry. Returns True if found and deleted."""
        pass

    @abstractmethod
    async def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate cache entries by tag (Phase 2).
        
        Returns: Number of entries deleted.
        """
        pass

    @abstractmethod
    async def stats(self) -> dict:
        """Return storage statistics (entry count, memory usage, etc.)."""
        pass
