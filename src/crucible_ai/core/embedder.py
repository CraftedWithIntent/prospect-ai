"""Local embedding generation using ONNX FastEmbed."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Lightweight wrapper for ONNX FastEmbed model."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """Initialize embedder with model name.

        Args:
            model_name: HuggingFace model ID for FastEmbed
        """
        self.model_name = model_name
        self.model: Any = None
        self._load_model()

    def _load_model(self) -> None:
        """Load ONNX FastEmbed model lazily."""
        try:
            from fastembed import FlagModel  # type: ignore[import-untyped]

            self.model = FlagModel(self.model_name, cache_folder=".cache/fastembed")
            logger.info(f"Loaded embedding model: {self.model_name}")
        except ImportError:
            logger.warning("fastembed not installed. Embeddings disabled.")
            self.model = None

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Input text to embed

        Returns:
            List of floats (embedding vector), or empty list if disabled
        """
        if not self.model or not text:
            return []

        embeddings = self.model.embed([text])
        return embeddings[0].tolist() if embeddings else []

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not self.model or not texts:
            return []

        embeddings = self.model.embed(texts)
        return [e.tolist() for e in embeddings]


# Global singleton
_embedder: EmbeddingModel | None = None


def get_embedder(model_name: str = "BAAI/bge-small-en-v1.5") -> EmbeddingModel:
    """Get or create global embedder instance.

    Args:
        model_name: HuggingFace model ID

    Returns:
        EmbeddingModel singleton
    """
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingModel(model_name)
    return _embedder
