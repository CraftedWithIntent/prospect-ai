"""
Pure functional similarity scoring for semantic cache matching.

No I/O, no side effects. Pure mathematical operations.
"""

import math
from crucible.domain.types import SimilarityScore


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Returns: Float in range [0, 1], where 1.0 = identical, 0.0 = orthogonal
    """
    if len(vec_a) != len(vec_b):
        return 0.0
    
    if len(vec_a) == 0:
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    return dot_product / (magnitude_a * magnitude_b)


def evaluate_similarity(
    query_embedding: list[float],
    cached_embedding: list[float],
    threshold: float,
) -> SimilarityScore:
    """
    Evaluate semantic similarity and return cache hit decision.
    
    Args:
        query_embedding: Embedding of incoming request
        cached_embedding: Embedding of cached response
        threshold: Minimum similarity required (e.g., 0.92)
    
    Returns:
        SimilarityScore with hit/miss decision
    """
    score = cosine_similarity(query_embedding, cached_embedding)
    return SimilarityScore.evaluate(score, threshold)


def batch_similarity_scores(
    query_embedding: list[float],
    cached_embeddings: list[list[float]],
    threshold: float,
) -> list[SimilarityScore]:
    """
    Compute similarity scores for query against multiple cached embeddings.
    
    Useful for finding the best semantic match from a cache pool.
    """
    return [
        evaluate_similarity(query_embedding, cached_emb, threshold)
        for cached_emb in cached_embeddings
    ]


def find_best_match(
    query_embedding: list[float],
    cached_embeddings: list[list[float]],
    threshold: float,
) -> tuple[int, SimilarityScore] | None:
    """
    Find the cached embedding with highest similarity to query.
    
    Returns:
        Tuple of (index, SimilarityScore) if score >= threshold, else None
    """
    scores = batch_similarity_scores(query_embedding, cached_embeddings, threshold)
    
    best_idx = -1
    best_score = None
    
    for idx, score in enumerate(scores):
        if score.is_hit:
            if best_score is None or score.score > best_score.score:
                best_idx = idx
                best_score = score
    
    if best_score is not None:
        return (best_idx, best_score)
    
    return None
