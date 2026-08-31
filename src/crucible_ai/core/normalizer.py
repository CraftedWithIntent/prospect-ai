"""
Pure functional request normalization for caching.

Canonicalize requests so semantically identical queries hash to the same value.
"""

import json
import re
from typing import Any


def strip_whitespace(text: str) -> str:
    """Remove extra whitespace and normalize line breaks."""
    return " ".join(text.split())


def normalize_messages(messages: list[dict[str, Any]]) -> str:
    """
    Normalize message list for caching.
    
    - Strips system prompts (configurable in Phase 2)
    - Canonicalizes JSON representation
    - Removes extra whitespace
    """
    normalized: list[dict[str, str]] = []
    
    for msg in messages:
        role = msg.get("role", "").strip().lower()
        content = msg.get("content", "").strip()
        
        # Skip system prompts (Phase 1 simplified)
        if role == "system":
            continue
        
        # Normalize content
        normalized_content = strip_whitespace(content)
        
        normalized.append({
            "role": role,
            "content": normalized_content,
        })
    
    return json.dumps(normalized, separators=(",", ":"), sort_keys=True)


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize OpenAI-format LLM request for caching.
    
    Returns a canonical version suitable for hashing.
    """
    normalized = {
        "model": payload.get("model", "").strip(),
        "messages": normalize_messages(payload.get("messages", [])),
        "temperature": round(payload.get("temperature", 0.7), 2),
        "max_tokens": payload.get("max_tokens"),
        "top_p": payload.get("top_p"),
        "frequency_penalty": payload.get("frequency_penalty", 0.0),
        "presence_penalty": payload.get("presence_penalty", 0.0),
    }
    
    return normalized


def payload_to_cache_key(payload: dict[str, Any]) -> str:
    """
    Convert normalized payload to deterministic cache key (SHA-256 hash).
    
    Used for L1 exact match.
    """
    import hashlib
    
    normalized = normalize_payload(payload)
    canonical_json = json.dumps(normalized, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical_json.encode()).hexdigest()
