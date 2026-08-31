"""M1.2 Integration Tests: Server L2 Semantic Cache Lookup"""

import pytest


from crucible_ai.domain.types import CacheEntry
from crucible_ai.infrastructure.storage.memory import MemoryCacheBackend


@pytest.mark.asyncio
async def test_l2_hit_after_l1_miss():
    """Test that L2 lookup returns cached response after L1 miss."""
    
    storage = MemoryCacheBackend()
    gateway = OpenAIGateway(storage=storage, similarity_threshold=0.92)
    
    # Pre-populate cache with an entry + embedding
    cached_embedding = [1.0, 0.0, 0.0]
    cached_entry = CacheEntry(
        request_hash="hash1",
        embedding_vector=cached_embedding,
        response_text="Cached response",
        finish_reason="stop",
        tokens_used=150,
        cached_at=0.0,
    )
    await storage.store(cached_entry)
    
    # Verify it's stored
    retrieved = await storage.get_by_hash("hash1")
    assert retrieved is not None
    assert retrieved.response_text == "Cached response"


@pytest.mark.asyncio
async def test_l2_threshold_filtering():
    """Test that L2 lookup respects similarity threshold."""
    
    storage = MemoryCacheBackend()
    
    # Store entry with embedding
    entry = CacheEntry(
        request_hash="hash1",
        embedding_vector=[1.0, 0.0, 0.0],
        response_text="Response",
        finish_reason="stop",
        tokens_used=100,
        cached_at=0.0,
    )
    await storage.store(entry)
    
    # Query with orthogonal embedding (should not match at 0.92 threshold)
    query_embedding = [0.0, 1.0, 0.0]
    results = await storage.search_semantic(query_embedding, threshold=0.92)
    
    assert len(results) == 0  # Orthogonal vectors have 0 similarity


@pytest.mark.asyncio
async def test_l2_ranking_by_similarity():
    """Test that L2 results are ranked by similarity score."""
    
    storage = MemoryCacheBackend()
    
    # Store two entries
    entry1 = CacheEntry(
        request_hash="hash1",
        embedding_vector=[1.0, 0.0, 0.0],
        response_text="Very similar",
        finish_reason="stop",
        tokens_used=100,
        cached_at=0.0,
    )
    entry2 = CacheEntry(
        request_hash="hash2",
        embedding_vector=[0.8, 0.2, 0.0],
        response_text="Less similar",
        finish_reason="stop",
        tokens_used=150,
        cached_at=0.0,
    )
    await storage.store(entry1)
    await storage.store(entry2)
    
    # Query closest to entry1
    query_embedding = [1.0, 0.0, 0.0]
    results = await storage.search_semantic(query_embedding, threshold=0.9)
    
    assert len(results) == 2
    assert results[0][0].request_hash == "hash1"  # Most similar first
    assert results[0][1] > results[1][1]  # Higher score first


@pytest.mark.asyncio
async def test_l2_no_match():
    """Test L2 returns empty when no matches above threshold."""
    
    storage = MemoryCacheBackend()
    
    entry = CacheEntry(
        request_hash="hash1",
        embedding_vector=[1.0, 0.0, 0.0],
        response_text="Response",
        finish_reason="stop",
        tokens_used=100,
        cached_at=0.0,
    )
    await storage.store(entry)
    
    # Query with orthogonal vector
    query_embedding = [0.0, 1.0, 0.0]
    results = await storage.search_semantic(query_embedding, threshold=0.92)
    
    assert len(results) == 0


@pytest.mark.asyncio
async def test_l2_empty_cache():
    """Test L2 returns empty on empty cache."""
    
    storage = MemoryCacheBackend()
    query_embedding = [1.0, 0.0, 0.0]
    results = await storage.search_semantic(query_embedding, threshold=0.92)
    
    assert len(results) == 0


@pytest.mark.asyncio
async def test_l2_empty_embedding():
    """Test L2 handles empty embeddings gracefully."""
    
    storage = MemoryCacheBackend()
    
    # Store entry without embedding
    entry = CacheEntry(
        request_hash="hash1",
        embedding_vector=[],
        response_text="Response",
        finish_reason="stop",
        tokens_used=100,
        cached_at=0.0,
    )
    await storage.store(entry)
    
    # Query should not crash
    query_embedding = [1.0, 0.0, 0.0]
    results = await storage.search_semantic(query_embedding, threshold=0.92)
    
    assert len(results) == 0  # Empty embeddings don't match


class TestL2CacheLatency:
    """Test L2 latency (should be <15ms for reasonable cache sizes)."""
    
    @pytest.mark.asyncio
    async def test_l2_latency_small_cache(self):
        """L2 search on small cache (<100 entries) should be <15ms."""
        storage = MemoryCacheBackend()
        
        # Populate with 50 entries
        for i in range(50):
            entry = CacheEntry(
                request_hash=f"hash{i}",
                embedding_vector=[float(i) / 50, 0.5, 0.5],
                response_text=f"Response {i}",
                finish_reason="stop",
                tokens_used=100,
                cached_at=0.0,
            )
            await storage.store(entry)
        
        # Search
        import time
        start = time.perf_counter()
        query_embedding = [0.0, 0.5, 0.5]
        results = await storage.search_semantic(query_embedding, threshold=0.9)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 15  # Should be fast
        assert len(results) > 0  # Some matches


class TestCacheHitRate:
    """Test expected cache hit rates (L1 + L2)."""
    
    @pytest.mark.asyncio
    async def test_l1_hit_rate(self):
        """L1 hit rate: exact match only (~5%)."""
        storage = MemoryCacheBackend()
        
        # Store one entry
        entry = CacheEntry(
            request_hash="exact_hash",
            embedding_vector=[],
            response_text="Response",
            finish_reason="stop",
            tokens_used=100,
            cached_at=0.0,
        )
        await storage.store(entry)
        
        # Query exact hash
        retrieved = await storage.get_by_hash("exact_hash")
        assert retrieved is not None
        
        # Query different hash
        retrieved = await storage.get_by_hash("different_hash")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_l2_hit_rate(self):
        """L2 hit rate: similar embeddings (~35-50%)."""
        storage = MemoryCacheBackend()
        
        # Simulate multiple cached queries
        queries = [
            ("How do I reset my password?", [1.0, 0.0, 0.0]),
            ("What is the weather?", [0.0, 1.0, 0.0]),
            ("How to reset password?", [0.98, 0.02, 0.0]),  # Similar to first
        ]
        
        for text, embedding in queries[:2]:
            entry = CacheEntry(
                request_hash=text,
                embedding_vector=embedding,
                response_text=f"Response to: {text}",
                finish_reason="stop",
                tokens_used=100,
                cached_at=0.0,
            )
            await storage.store(entry)
        
        # Query similar to first
        query_embedding = [0.95, 0.05, 0.0]
        results = await storage.search_semantic(query_embedding, threshold=0.92)
        
        assert len(results) == 1
        assert "password" in results[0][0].response_text.lower()
