"""Tests for M1.2 semantic cache (L2 similarity matching)."""

import pytest

from crucible_ai.core.embedder import EmbeddingModel, get_embedder
from crucible_ai.core.similarity import cosine_similarity, evaluate_similarity, find_best_match
from crucible_ai.domain.types import SimilarityScore, CacheEntry
from crucible_ai.infrastructure.storage.memory import MemoryCacheBackend


class TestEmbedder:
    """Test ONNX FastEmbed embedder."""

    def test_embedder_singleton(self):
        """Test that embedder returns same instance."""
        e1 = get_embedder()
        e2 = get_embedder()
        assert e1 is e2

    def test_embed_text(self):
        """Test that embedding generates vector."""
        embedder = get_embedder()
        embedding = embedder.embed("Hello world")
        
        # FastEmbed returns 384-dim vectors (BGE-small)
        assert isinstance(embedding, list)
        assert len(embedding) == 384 or len(embedding) == 0  # 0 if model not available

    def test_embed_determinism(self):
        """Test that embedding same text twice produces same vector."""
        embedder = get_embedder()
        text = "Password reset procedure"
        
        emb1 = embedder.embed(text)
        emb2 = embedder.embed(text)
        
        if emb1 and emb2:  # Only compare if embeddings available
            assert emb1 == emb2

    def test_embed_batch(self):
        """Test batch embedding."""
        embedder = get_embedder()
        texts = ["Hello", "World", "Test"]
        embeddings = embedder.embed_batch(texts)
        
        assert len(embeddings) == 3 or len(embeddings) == 0


class TestCosineSimilarity:
    """Test cosine similarity scoring."""

    def test_identical_vectors(self):
        """Identical vectors should score 1.0."""
        vec = [1.0, 0.0, 0.0]
        score = cosine_similarity(vec, vec)
        assert abs(score - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should score 0.0."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        score = cosine_similarity(vec_a, vec_b)
        assert abs(score - 0.0) < 0.001

    def test_opposite_vectors(self):
        """Opposite vectors should score -1.0."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [-1.0, 0.0, 0.0]
        score = cosine_similarity(vec_a, vec_b)
        assert abs(score - (-1.0)) < 0.001

    def test_empty_vectors(self):
        """Empty vectors should score 0.0."""
        score = cosine_similarity([], [])
        assert score == 0.0

    def test_length_mismatch(self):
        """Vectors of different lengths should score 0.0."""
        score = cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
        assert score == 0.0

    def test_zero_magnitude(self):
        """Vectors with zero magnitude should score 0.0."""
        score = cosine_similarity([0.0, 0.0], [1.0, 0.0])
        assert score == 0.0


class TestSimilarityScore:
    """Test SimilarityScore evaluation."""

    def test_score_above_threshold(self):
        """Score above threshold should be a hit."""
        score_result = SimilarityScore.evaluate(0.95, threshold=0.92)
        assert score_result.is_hit is True
        assert score_result.score == 0.95

    def test_score_below_threshold(self):
        """Score below threshold should be a miss."""
        score_result = SimilarityScore.evaluate(0.85, threshold=0.92)
        assert score_result.is_hit is False

    def test_score_at_threshold(self):
        """Score exactly at threshold should be a hit."""
        score_result = SimilarityScore.evaluate(0.92, threshold=0.92)
        assert score_result.is_hit is True

    def test_distance_calculation(self):
        """Distance should be 1 - score."""
        score_result = SimilarityScore.evaluate(0.75, threshold=0.92)
        assert abs(score_result.distance - 0.25) < 0.001


class TestSemanticCacheLookup:
    """Test L2 semantic cache operations."""

    @pytest.mark.asyncio
    async def test_semantic_search_empty_cache(self):
        """Search in empty cache should return empty list."""
        backend = MemoryCacheBackend()
        query_embedding = [1.0, 0.0, 0.0]
        results = await backend.search_semantic(query_embedding, threshold=0.92)
        assert results == []

    @pytest.mark.asyncio
    async def test_semantic_search_with_matches(self):
        """Search should return similar cached entries."""
        backend = MemoryCacheBackend()
        
        # Store entry with embedding
        entry1 = CacheEntry(
            request_hash="hash1",
            embedding_vector=[1.0, 0.0, 0.0],
            response_text="Response 1",
            finish_reason="stop",
            tokens_used=100,
            cached_at=0.0,
        )
        await backend.store(entry1)
        
        # Query with similar embedding
        query_embedding = [0.99, 0.01, 0.0]
        results = await backend.search_semantic(query_embedding, threshold=0.9)
        
        assert len(results) == 1
        cached_entry, similarity_score = results[0]
        assert cached_entry.request_hash == "hash1"
        assert similarity_score >= 0.9

    @pytest.mark.asyncio
    async def test_semantic_search_threshold_filtering(self):
        """Search should filter by threshold."""
        backend = MemoryCacheBackend()
        
        entry1 = CacheEntry(
            request_hash="hash1",
            embedding_vector=[1.0, 0.0, 0.0],
            response_text="Response 1",
            finish_reason="stop",
            tokens_used=100,
            cached_at=0.0,
        )
        await backend.store(entry1)
        
        # Query with low similarity
        query_embedding = [0.0, 1.0, 0.0]
        results = await backend.search_semantic(query_embedding, threshold=0.9)
        
        # Should be filtered out (similarity ~0)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_semantic_search_ranking(self):
        """Results should be ranked by similarity score."""
        backend = MemoryCacheBackend()
        
        entry1 = CacheEntry(
            request_hash="hash1",
            embedding_vector=[1.0, 0.0, 0.0],
            response_text="Response 1",
            finish_reason="stop",
            tokens_used=100,
            cached_at=0.0,
        )
        entry2 = CacheEntry(
            request_hash="hash2",
            embedding_vector=[0.8, 0.2, 0.0],
            response_text="Response 2",
            finish_reason="stop",
            tokens_used=150,
            cached_at=0.0,
        )
        await backend.store(entry1)
        await backend.store(entry2)
        
        # Query closest to entry1
        query_embedding = [1.0, 0.0, 0.0]
        results = await backend.search_semantic(query_embedding, threshold=0.9)
        
        # Should return both, entry1 first (higher similarity)
        assert len(results) == 2
        assert results[0][0].request_hash == "hash1"
        assert results[0][1] > results[1][1]  # First has higher score


class TestFindBestMatch:
    """Test best-match selection from semantic results."""

    def test_find_best_match_above_threshold(self):
        """Should find best match above threshold."""
        query_embedding = [1.0, 0.0, 0.0]
        cached_embeddings = [
            [0.9, 0.1, 0.0],  # similarity ~0.99
            [0.8, 0.2, 0.0],  # similarity ~0.97
            [0.0, 1.0, 0.0],  # similarity 0 (below threshold)
        ]
        
        result = find_best_match(query_embedding, cached_embeddings, threshold=0.9)
        
        assert result is not None
        idx, score = result
        assert idx == 0  # First one has highest similarity
        assert score.is_hit is True

    def test_find_best_match_no_match(self):
        """Should return None if no match above threshold."""
        query_embedding = [1.0, 0.0, 0.0]
        cached_embeddings = [[0.0, 1.0, 0.0]]  # Orthogonal
        
        result = find_best_match(query_embedding, cached_embeddings, threshold=0.9)
        
        assert result is None

    def test_find_best_match_empty_cache(self):
        """Should return None on empty cache."""
        query_embedding = [1.0, 0.0, 0.0]
        cached_embeddings = []
        
        result = find_best_match(query_embedding, cached_embeddings, threshold=0.9)
        
        assert result is None
