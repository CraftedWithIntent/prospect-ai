"""Crucible core functional logic."""

from crucible.core.normalizer import (
    normalize_messages,
    normalize_payload,
    payload_to_cache_key,
    strip_whitespace,
)
from crucible.core.router import (
    is_rate_limited,
    select_fallback_route,
    select_primary_route,
    should_fallback,
)
from crucible.core.similarity import (
    batch_similarity_scores,
    cosine_similarity,
    evaluate_similarity,
    find_best_match,
)

__all__ = [
    "normalize_messages",
    "normalize_payload",
    "payload_to_cache_key",
    "strip_whitespace",
    "is_rate_limited",
    "select_fallback_route",
    "select_primary_route",
    "should_fallback",
    "batch_similarity_scores",
    "cosine_similarity",
    "evaluate_similarity",
    "find_best_match",
]
