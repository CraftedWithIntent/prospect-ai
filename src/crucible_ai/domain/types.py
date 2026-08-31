"""
Immutable domain types for Crucible semantic cache.

Pure data structures representing cache entries, routing decisions, and metrics.
No I/O, no side effects — just value objects.
"""

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, Literal
import hashlib


class CacheHitType(StrEnum):
    """Type of cache hit."""
    EXACT = "exact"  # L1: SHA-256 hash match
    SEMANTIC = "semantic"  # L2: Cosine similarity >= threshold
    MISS = "miss"  # No hit (upstream required)
    FALLBACK = "fallback"  # Hit from secondary provider


class ProviderName(StrEnum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    BEDROCK = "bedrock"


@dataclass(frozen=True)
class CacheEntry:
    """Immutable cached LLM response."""
    request_hash: str  # SHA-256 of normalized request
    embedding_vector: list[float]  # Embedding for semantic matching
    response_text: str  # Full cached response
    finish_reason: str  # stop, length, etc.
    tokens_used: int  # Cached token count
    cached_at: float  # Unix timestamp (seconds)
    metadata: dict[str, Any] = field(default_factory=dict)  # type: ignore[misc]

    @staticmethod
    def from_request(
        normalized_request: str,
        embedding: list[float],
        response: str,
        finish_reason: str,
        tokens: int,
        cached_at: float,
    ) -> "CacheEntry":
        """Construct cache entry from request and response."""
        request_hash = hashlib.sha256(normalized_request.encode()).hexdigest()
        return CacheEntry(
            request_hash=request_hash,
            embedding_vector=embedding,
            response_text=response,
            finish_reason=finish_reason,
            tokens_used=tokens,
            cached_at=cached_at,
        )


@dataclass(frozen=True)
class SimilarityScore:
    """Result of semantic similarity comparison."""
    score: float  # 0.0-1.0 cosine similarity
    threshold: float  # Required threshold for cache hit
    is_hit: bool  # score >= threshold
    distance: float = field(init=False)  # Euclidean distance (1 - score)

    def __post_init__(self) -> None:
        object.__setattr__(self, "distance", 1.0 - self.score)

    @staticmethod
    def evaluate(score: float, threshold: float) -> "SimilarityScore":
        """Evaluate if score meets threshold."""
        return SimilarityScore(
            score=score,
            threshold=threshold,
            is_hit=score >= threshold,
        )


@dataclass(frozen=True)
class UpstreamRoute:
    """Routing decision for upstream provider."""
    provider: ProviderName
    model: str  # Model name (gpt-4, claude-3, etc.)
    api_key_idx: int = 0  # Index of API key to use (for multi-key fallback)
    is_fallback: bool = False  # True if primary provider failed


@dataclass(frozen=True)
class CachedResponse:
    """Response metadata from cache retrieval."""
    hit_type: CacheHitType
    response_text: str
    tokens_saved: int
    latency_ms: float
    cache_entry: CacheEntry | None = None
    fallback_route: UpstreamRoute | None = None


@dataclass(frozen=True)
class TokenMetrics:
    """Token spend and cache efficiency metrics."""
    total_requests: int
    cache_hits: int
    cache_misses: int
    exact_hits: int
    semantic_hits: int
    fallback_hits: int
    tokens_requested: int
    tokens_cached_saved: int
    tokens_upstream: int

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of requests served from cache."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100

    @property
    def token_savings_rate(self) -> float:
        """Percentage of requested tokens saved by cache."""
        if self.tokens_requested == 0:
            return 0.0
        return (self.tokens_cached_saved / self.tokens_requested) * 100

    @property
    def cost_savings_usd(self) -> float:
        """Estimated USD savings (assuming GPT-4 pricing: $0.03 per 1K tokens)."""
        # Rough estimate; actual depends on model mix
        return (self.tokens_cached_saved / 1000) * 0.03


@dataclass(frozen=True)
class NormalizedRequest:
    """Canonical form of LLM request for caching."""
    messages: str  # JSON-serialized and normalized messages
    model: str
    temperature: float
    max_tokens: int | None
    top_p: float | None
    system_prompt_removed: bool  # Flag: system prompt was stripped

    @staticmethod
    def from_openai_payload(payload: dict[str, Any]) -> "NormalizedRequest":
        """Construct from OpenAI-format request payload."""
        import json

        messages_text = json.dumps(payload.get("messages", []), separators=(",", ":"))
        return NormalizedRequest(
            messages=messages_text,
            model=payload.get("model", ""),
            temperature=payload.get("temperature", 0.7),
            max_tokens=payload.get("max_tokens"),
            top_p=payload.get("top_p"),
            system_prompt_removed=False,
        )
