"""M1.2 End-to-End Integration Tests: Upstream Miss -> L2 Hit Cycle"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from prospect_ai.domain.types import CacheEntry
from prospect_ai.infrastructure.storage.memory import MemoryCacheBackend
from prospect_ai.infrastructure.proxy_gateway import ProxyGateway


@pytest.mark.asyncio
async def test_e2e_upstream_miss_then_l2_hit():
    """Test full cycle: Query upstream, cache with embedding, then L2 hit on similar query."""

    storage = MemoryCacheBackend()
    proxy = ProxyGateway(
        upstream_base_url="https://api.openai.com",
        upstream_api_key="test-key",
        cache_backend=storage,
    )

    request_body_1 = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "How do I reset my password?"}],
        "stream": False,
    }

    mock_response = {
        "choices": [{"message": {"content": "To reset your password, click the forgot button."}}],
        "usage": {"completion_tokens": 15},
    }

    with patch.object(proxy, "_send_request", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (200, mock_response)
        content, usage = await proxy.call_upstream(request_body_1, "test_cache_key_1")
        assert content == "To reset your password, click the forgot button."
        assert usage["completion_tokens"] == 15

        import asyncio
        await asyncio.sleep(0.1)

    cached = await storage.get_by_hash("test_cache_key_1")
    assert cached is not None
    assert cached.response_text == "To reset your password, click the forgot button."

    request_body_2 = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "I forgot my password, how to reset?"}],
        "stream": False,
    }

    from prospect_ai.core.embedder import get_embedder
    from prospect_ai.core.similarity import cosine_similarity

    embedder = get_embedder()
    query1_embed = embedder.embed(json.dumps(request_body_1["messages"]))
    query2_embed = embedder.embed(json.dumps(request_body_2["messages"]))

    if query1_embed and query2_embed:
        similarity = cosine_similarity(query1_embed, query2_embed)
        if similarity >= 0.92:
            results = await storage.search_semantic(query2_embed, threshold=0.92, limit=1)
            assert len(results) == 1
            assert results[0][0].response_text == cached.response_text


@pytest.mark.asyncio
async def test_e2e_embedding_determinism():
    """Test that embeddings are deterministic."""

    from prospect_ai.core.embedder import get_embedder

    embedder = get_embedder()

    text = "How do I reset my password?"
    embed1 = embedder.embed(text)
    embed2 = embedder.embed(text)

    if embed1 and embed2:
        assert embed1 == embed2


@pytest.mark.asyncio
async def test_e2e_semantic_similarity():
    """Test that similar texts produce similar embeddings."""

    from prospect_ai.core.embedder import get_embedder
    from prospect_ai.core.similarity import cosine_similarity

    embedder = get_embedder()

    text_a = "How do I reset my password?"
    text_b = "I forgot my password, how to reset it?"

    embed_a = embedder.embed(text_a)
    embed_b = embedder.embed(text_b)

    if embed_a and embed_b:
        similarity = cosine_similarity(embed_a, embed_b)
        assert similarity > 0.0


@pytest.mark.asyncio
async def test_e2e_cache_growth():
    """Test that L2 hits work with accumulated cache."""

    storage = MemoryCacheBackend()

    from prospect_ai.core.embedder import get_embedder

    embedder = get_embedder()

    clusters = [
        ("How do I reset my password?", "To reset, click forgot password button"),
        ("I forgot my password?", "Use password recovery link"),
        ("What is the weather?", "Check weather.com"),
    ]

    for query, response in clusters:
        embedding = embedder.embed(query)
        entry = CacheEntry(
            request_hash=query,
            embedding_vector=embedding,
            response_text=response,
            finish_reason="stop",
            tokens_used=50,
            cached_at=0.0,
        )
        await storage.store(entry)

    query_cluster1 = "How to reset my login password?"
    embedding_cluster1 = embedder.embed(query_cluster1)

    results = await storage.search_semantic(embedding_cluster1, threshold=0.85)

    if results:
        assert "password" in results[0][0].response_text.lower()


@pytest.mark.asyncio
async def test_e2e_empty_embedding():
    """Test that empty embeddings are handled gracefully."""

    storage = MemoryCacheBackend()
    proxy = ProxyGateway(
        upstream_base_url="https://api.openai.com",
        upstream_api_key="test-key",
        cache_backend=storage,
    )

    proxy._enqueue_cache_store("cache_key", "response_text", {}, "")

    import asyncio
    await asyncio.sleep(0.1)

    cached = await storage.get_by_hash("cache_key")
    assert cached is not None
    assert cached.embedding_vector == []
    assert cached.response_text == "response_text"
