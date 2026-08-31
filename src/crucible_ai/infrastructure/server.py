"""FastAPI server for OpenAI-compatible gateway."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from crucible_ai.core.normalizer import normalize_payload, payload_to_cache_key
from crucible_ai.core.embedder import get_embedder
from crucible_ai.infrastructure.proxy_gateway import ProxyGateway
from crucible_ai.infrastructure.storage.base import CacheStorageBackend

from crucible_ai.infrastructure.proxy_gateway import ProxyGateway
from crucible_ai.infrastructure.storage.base import CacheStorageBackend

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Validation error result."""

    status_code: int
    detail: str


class OpenAIGateway:
    """OpenAI-compatible /v1/chat/completions gateway."""

    def __init__(
        self,
        storage_backend: CacheStorageBackend,
        upstream_base_url: str = "https://api.openai.com/v1",
        upstream_api_key: str = "",
        similarity_threshold: float = 0.92,
    ):
        """Initialize gateway."""
        self.storage = storage_backend
        self.similarity_threshold = similarity_threshold
        self.app = FastAPI(title="Crucible AI Gateway", version="0.1.0")
        self.proxy = ProxyGateway(
            upstream_base_url=upstream_base_url,
            upstream_api_key=upstream_api_key,
            cache_backend=storage_backend,
            similarity_threshold=similarity_threshold,
        )
        self._register_routes()

    def _register_routes(self) -> None:
        """Register FastAPI routes."""

        @self.app.get("/health")
        async def health_check() -> dict[str, str]:
            """Health check."""
            return {"status": "ok", "version": "0.1.0"}

        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: Request) -> Any:
            """OpenAI-compatible endpoint."""
            body_result = await self._parse_request(request)
            if isinstance(body_result, ValidationError):
                raise HTTPException(
                    status_code=body_result.status_code,
                    detail=body_result.detail,
                )

            body = body_result
            validation_err = self._validate_request(body)
            if validation_err:
                raise HTTPException(
                    status_code=validation_err.status_code,
                    detail=validation_err.detail,
                )

            model = body.get("model", "")
            messages = body.get("messages", [])
            temperature = body.get("temperature", 0.7)
            max_tokens = body.get("max_tokens")
            stream = body.get("stream", False)

            if not model or not messages:
                raise HTTPException(
                    status_code=400,
                    detail="model and messages are required",
                )

            norm_result = self._normalize_and_hash(model, messages, temperature, max_tokens)
            if isinstance(norm_result, ValidationError):
                raise HTTPException(
                    status_code=norm_result.status_code,
                    detail=norm_result.detail,
                )

            cache_key = norm_result
            cached_entry = await self.storage.get_by_hash(cache_key)
            if cached_entry:
                logger.info(f"L1 cache hit: {cache_key[:8]}...")
                if cached_entry.response_text and model:
                    return self._format_response(
                        cached_entry.response_text,
                        model,
                        cached_entry.tokens_used,
                        "stop",
                    )


            # L1 miss: try L2 semantic cache
            embedder = get_embedder()
            query_embedding = embedder.embed(json.dumps(messages))
            if query_embedding:
                l2_results = await self.storage.search_semantic(
                    query_embedding, self.similarity_threshold, limit=1
                )
                if l2_results:
                    cached_entry, similarity_score = l2_results[0]
                    logger.info(
                        f"L2 cache hit: {cached_entry.request_hash[:8]}... "
                        f"(similarity={similarity_score:.4f})"
                    )
                    if cached_entry.response_text and model:
                        return self._format_response(
                            cached_entry.response_text,
                            model,
                            cached_entry.tokens_used,
                            "stop",
                        )
            if stream:
                return StreamingResponse(
                    self.proxy.stream_upstream(body, cache_key),
                    media_type="text/event-stream",
                )
            else:
                response_text, usage = await self.proxy.call_upstream(
                    body, cache_key
                )
                return self._format_response(
                    response_text,
                    model,
                    usage.get("completion_tokens", 0),
                    "stop",
                )

        @self.app.post("/v1/completions")
        async def completions(request: Request) -> Any:
            """Backward compat endpoint."""
            return await chat_completions(request)

    async def _parse_request(self, request: Request) -> dict[str, Any] | ValidationError:
        """Parse JSON request body."""
        if not request.headers.get("content-type", "").startswith("application/json"):
            return ValidationError(400, "Content-Type must be application/json")

        body = request.stream()
        data = b""
        async for chunk in body:
            data += chunk

        result = self._decode_json(data)
        return result if isinstance(result, dict) else ValidationError(400, result)

    def _decode_json(self, data: bytes) -> dict[str, Any] | str:
        """Decode JSON safely. Returns dict or error message."""
        if not data:
            return "Empty request body"

        result = json.loads(data.decode("utf-8"))
        return result if isinstance(result, dict) else "Request body must be JSON object"

    def _validate_request(self, body: dict[str, Any]) -> ValidationError | None:
        """Validate required fields."""
        if "model" not in body:
            return ValidationError(400, "Missing required field: model")
        if "messages" not in body:
            return ValidationError(400, "Missing required field: messages")
        return None

    def _normalize_and_hash(
        self,
        model: str,
        messages: list[Any],
        temperature: float,
        max_tokens: int | None,
    ) -> str | ValidationError:
        """Normalize payload and generate cache key."""
        normalized = normalize_payload({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        if not normalized:
            return ValidationError(400, "Request normalization failed")

        cache_key = payload_to_cache_key(normalized)
        return cache_key

    def _format_response(
        self,
        content: str,
        model: str,
        completion_tokens: int,
        finish_reason: str = "stop",
    ) -> dict[str, Any]:
        """Format OpenAI response."""
        return {
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": completion_tokens,
                "total_tokens": 10 + completion_tokens,
            },
        }

    async def start(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        """Start server."""
        import uvicorn  # type: ignore[import-untyped]

        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
