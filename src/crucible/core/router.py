"""
Pure functional routing logic for provider fallback and selection.

Determines which upstream provider to use based on availability and fallback rules.
"""

from typing import Any
from crucible.domain.types import ProviderName, UpstreamRoute


def select_primary_route(payload: dict[str, Any]) -> UpstreamRoute:
    """
    Select primary upstream route based on request model and config.
    
    Phase 1: Simple route (one primary provider).
    Phase 2: Model affinity routing, load balancing, cost optimization.
    """
    model = payload.get("model", "gpt-4")
    
    # Simplified Phase 1 routing: infer provider from model name
    if "gpt" in model.lower():
        provider = ProviderName.OPENAI
    elif "claude" in model.lower():
        provider = ProviderName.ANTHROPIC
    elif "bedrock" in model.lower():
        provider = ProviderName.BEDROCK
    else:
        provider = ProviderName.OPENAI  # Default
    
    return UpstreamRoute(
        provider=provider,
        model=model,
        api_key_idx=0,\n        is_fallback=False,
    )


def select_fallback_route(
    primary: UpstreamRoute,
    available_providers: list[ProviderName],
) -> UpstreamRoute | None:
    """
    Select fallback provider if primary fails.
    
    Prefers alternative providers in order of likelihood.
    """
    if not available_providers:
        return None
    
    # Prioritize fallback order: Anthropic -> Azure -> Bedrock -> OpenAI
    fallback_order = [
        ProviderName.ANTHROPIC,
        ProviderName.AZURE,
        ProviderName.BEDROCK,
        ProviderName.OPENAI,
    ]
    
    for preferred_provider in fallback_order:
        if preferred_provider in available_providers and preferred_provider != primary.provider:
            return UpstreamRoute(
                provider=preferred_provider,
                model=primary.model,  # Attempt same model on fallback
                api_key_idx=0,
                is_fallback=True,
            )
    
    return None


def is_rate_limited(status_code: int) -> bool:
    """Check if HTTP status code indicates rate limiting."""
    return status_code in (429, 503)


def should_fallback(status_code: int) -> bool:
    """Determine if upstream error warrants immediate fallback."""
    return status_code >= 500 or status_code == 429
