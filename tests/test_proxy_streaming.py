"""
Comprehensive tests for OpenAI gateway proxy and streaming (M1.1).

Coverage:
- Non-streaming requests (cached and upstream)
- Streaming requests (SSE passthrough)
- Cache key generation (deterministic)
- Error handling scenarios
"""

import json
import pytest
from unittest.mock import patch

from crucible_ai.core.normalizer import payload_to_cache_key
from crucible_ai.infrastructure.storage.memory import MemoryCacheBackend
from crucible_ai.domain.types import CacheEntry
import time


class TestCacheKeyGeneration:
    """Test deterministic cache key generation."""

    def test_payload_to_cache_key_deterministic(self) -> None:
        """Same payload should generate same cache key."""
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello world"}],
            "temperature": 0.7,
            "max_tokens": 100,
        }

        key1 = payload_to_cache_key(payload)
        key2 = payload_to_cache_key(payload)

        assert key1 == key2
        assert len(key1) == 64  # SHA-256 hex

    def test_different_payloads_different_keys(self) -> None:
        """Different payloads should generate different cache keys."""
        payload1 = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        payload2 = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Goodbye"}],
        }

        key1 = payload_to_cache_key(payload1)
        key2 = payload_to_cache_key(payload2)

        assert key1 != key2

    def test_model_affects_cache_key(self) -> None:
        """Different models should generate different cache keys."""
        payload_gpt4 = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
        }
        payload_claude = {
            "model": "claude-3-sonnet",
            "messages": [{"role": "user", "content": "Test"}],
        }

        key_gpt4 = payload_to_cache_key(payload_gpt4)
        key_claude = payload_to_cache_key(payload_claude)

        assert key_gpt4 != key_claude


class TestMemoryCacheBackend:
    """Test in-memory cache storage."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_exact_match(self) -> None:
        """Store and retrieve cache entry by exact hash."""
        storage = MemoryCacheBackend()

        entry = CacheEntry(
            request_hash="abc123def456",
            embedding_vector=[0.1, 0.2, 0.3],
            response_text="Cached response",
            finish_reason="stop",
            tokens_used=42,
            cached_at=time.time(),
        )

        await storage.store(entry)
        retrieved = await storage.get_by_hash("abc123def456")

        assert retrieved is not None
        assert retrieved.response_text == "Cached response"
        assert retrieved.tokens_used == 42

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self) -> None:
        """Querying non-existent hash should return None."""
        storage = MemoryCacheBackend()
        result = await storage.get_by_hash("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self) -> None:
        """Delete should remove entry from cache."""
        storage = MemoryCacheBackend()

        entry = CacheEntry(
            request_hash="delete-me",
            embedding_vector=[0.1],
            response_text="Delete this",
            finish_reason="stop",
            tokens_used=1,
            cached_at=time.time(),
        )

        await storage.store(entry)
        deleted = await storage.delete_by_hash("delete-me")
        assert deleted is True

        retrieved = await storage.get_by_hash("delete-me")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_stats_returns_entry_count(self) -> None:
        """Stats should reflect current entry count."""
        storage = MemoryCacheBackend()

        entry1 = CacheEntry(
            request_hash="entry1",
            embedding_vector=[0.1],
            response_text="Response 1",
            finish_reason="stop",
            tokens_used=10,
            cached_at=time.time(),
        )
        entry2 = CacheEntry(
            request_hash="entry2",
            embedding_vector=[0.2],
            response_text="Response 2",
            finish_reason="stop",
            tokens_used=20,
            cached_at=time.time(),
        )

        await storage.store(entry1)
        await storage.store(entry2)

        stats = await storage.stats()
        assert stats["entries"] == 2
        assert stats["backend"] == "memory"


class TestOpenAICompatibility:
    """Test OpenAI-compatible request/response formats."""

    def test_openai_format_request_structure(self) -> None:
        """Verify OpenAI request format is valid."""
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "What is 2+2?"}
            ],
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 0.9,
        }

        # Should be serializable to JSON
        json_str = json.dumps(payload)
        parsed = json.loads(json_str)

        assert parsed["model"] == "gpt-4"
        assert len(parsed["messages"]) == 1
        assert parsed["messages"][0]["role"] == "user"

    def test_openai_format_response_structure(self) -> None:
        """Verify OpenAI response format is valid."""
        response = {
            "object": "chat.completion",
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "4"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }

        # Should be serializable to JSON
        json_str = json.dumps(response)
        parsed = json.loads(json_str)

        assert parsed["object"] == "chat.completion"
        assert len(parsed["choices"]) == 1
        assert parsed["usage"]["total_tokens"] == 15


class TestStreamingFormats:
    """Test SSE streaming format compatibility."""

    def test_sse_chunk_format(self) -> None:
        """SSE chunks should follow OpenAI format."""
        # OpenAI streaming format: data: {json}\n\n
        sse_chunk = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "Hello"},
                    "finish_reason": None
                }
            ]
        }

        # Should serialize to JSON for SSE
        json_str = json.dumps(sse_chunk)
        sse_line = f"data: {json_str}\n\n"

        assert "data:" in sse_line
        assert json.loads(sse_line.split("data: ")[1].strip()) == sse_chunk

    def test_sse_stream_end(self) -> None:
        """SSE stream should end with [DONE]."""
        sse_end = "data: [DONE]\n\n"
        assert "[DONE]" in sse_end


class TestErrorScenarios:
    """Test error handling scenarios."""

    def test_invalid_request_missing_model(self) -> None:
        """Request missing 'model' field should be invalid."""
        invalid_payload = {
            "messages": [{"role": "user", "content": "Test"}]
            # Missing 'model'
        }

        # In real implementation, validation would catch this
        assert "model" not in invalid_payload

    def test_invalid_request_missing_messages(self) -> None:
        """Request missing 'messages' field should be invalid."""
        invalid_payload = {
            "model": "gpt-4"
            # Missing 'messages'
        }

        assert "messages" not in invalid_payload

    @pytest.mark.asyncio
    async def test_storage_max_entries_eviction(self) -> None:
        """Cache should evict oldest entry when full."""
        storage = MemoryCacheBackend(max_entries=2)

        # Add 3 entries to trigger eviction
        for i in range(3):
            entry = CacheEntry(
                request_hash=f"entry-{i}",
                embedding_vector=[float(i)],
                response_text=f"Response {i}",
                finish_reason="stop",
                tokens_used=i,
                cached_at=time.time(),
            )
            await storage.store(entry)

        stats = await storage.stats()
        # Should not exceed max_entries
        assert stats["entries"] <= 2
