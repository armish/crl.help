"""
Vector similarity utilities for embeddings.

This module provides functions for computing similarity between embedding vectors,
which is essential for semantic search and retrieval in the RAG system.
"""

import math
from typing import List, Tuple


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Cosine similarity measures the cosine of the angle between two vectors,
    ranging from -1 (opposite) to 1 (identical direction).
    It's scale-invariant and works well for comparing embeddings.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between -1 and 1

    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if not vec1 or not vec2:
        raise ValueError("Vectors cannot be empty")

    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimension, got {len(vec1)} and {len(vec2)}"
        )

    # Compute dot product and magnitudes
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute Euclidean distance between two vectors.

    Euclidean distance is the straight-line distance between two points
    in n-dimensional space. Lower values indicate more similar vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Euclidean distance (always >= 0)

    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if not vec1 or not vec2:
        raise ValueError("Vectors cannot be empty")

    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimension, got {len(vec1)} and {len(vec2)}"
        )

    squared_diff_sum = sum((a - b) ** 2 for a, b in zip(vec1, vec2))
    return math.sqrt(squared_diff_sum)


def dot_product(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute dot product of two vectors.

    The dot product is the sum of element-wise products.
    For normalized vectors, this is equivalent to cosine similarity.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Dot product value

    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if not vec1 or not vec2:
        raise ValueError("Vectors cannot be empty")

    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimension, got {len(vec1)} and {len(vec2)}"
        )

    return sum(a * b for a, b in zip(vec1, vec2))


def normalize_vector(vec: List[float]) -> List[float]:
    """
    Normalize a vector to unit length (magnitude = 1).

    Normalization is useful when you want to compare vectors
    based on direction only, ignoring magnitude.

    Args:
        vec: Input vector

    Returns:
        Normalized vector with magnitude 1

    Raises:
        ValueError: If vector is empty or has zero magnitude
    """
    if not vec:
        raise ValueError("Vector cannot be empty")

    magnitude = math.sqrt(sum(x * x for x in vec))

    if magnitude == 0:
        raise ValueError("Cannot normalize zero vector")

    return [x / magnitude for x in vec]


def find_top_k_similar(
    query_vec: List[float],
    candidate_vecs: List[Tuple[str, List[float]]],
    k: int = 5,
    similarity_fn: str = "cosine"
) -> List[Tuple[str, float]]:
    """
    Find top-k most similar vectors to a query vector.

    Args:
        query_vec: Query vector
        candidate_vecs: List of (id, vector) tuples to compare against
        k: Number of top results to return
        similarity_fn: Similarity function to use ("cosine", "dot", or "euclidean")

    Returns:
        List of (id, similarity_score) tuples, sorted by score (descending for
        cosine/dot, ascending for euclidean)

    Raises:
        ValueError: If inputs are invalid or similarity_fn is unknown
    """
    if not query_vec:
        raise ValueError("Query vector cannot be empty")

    if not candidate_vecs:
        raise ValueError("Candidate vectors cannot be empty")

    if k < 1:
        raise ValueError("k must be at least 1")

    # Select similarity function
    if similarity_fn == "cosine":
        score_fn = cosine_similarity
        reverse = True  # Higher is better
    elif similarity_fn == "dot":
        score_fn = dot_product
        reverse = True  # Higher is better
    elif similarity_fn == "euclidean":
        score_fn = euclidean_distance
        reverse = False  # Lower is better
    else:
        raise ValueError(
            f"Unknown similarity function: {similarity_fn}. "
            f"Must be 'cosine', 'dot', or 'euclidean'"
        )

    # Compute similarities
    scores = []
    for cand_id, cand_vec in candidate_vecs:
        try:
            score = score_fn(query_vec, cand_vec)
            scores.append((cand_id, score))
        except ValueError as e:
            # Skip candidates with incompatible dimensions
            continue

    if not scores:
        raise ValueError("No valid candidates found")

    # Sort and return top-k
    scores.sort(key=lambda x: x[1], reverse=reverse)
    return scores[:k]


def vector_magnitude(vec: List[float]) -> float:
    """
    Compute the magnitude (L2 norm) of a vector.

    Args:
        vec: Input vector

    Returns:
        Magnitude of the vector

    Raises:
        ValueError: If vector is empty
    """
    if not vec:
        raise ValueError("Vector cannot be empty")

    return math.sqrt(sum(x * x for x in vec))


def mean_vector(vectors: List[List[float]]) -> List[float]:
    """
    Compute the element-wise mean of multiple vectors.

    All vectors must have the same dimension.

    Args:
        vectors: List of vectors to average

    Returns:
        Mean vector

    Raises:
        ValueError: If vectors is empty or vectors have different dimensions
    """
    if not vectors:
        raise ValueError("Vectors list cannot be empty")

    # Check all vectors have same dimension
    dim = len(vectors[0])
    for i, vec in enumerate(vectors):
        if len(vec) != dim:
            raise ValueError(
                f"All vectors must have same dimension. "
                f"Vector 0 has {dim} dims, vector {i} has {len(vec)} dims"
            )

    # Compute mean
    n = len(vectors)
    mean = [0.0] * dim

    for vec in vectors:
        for i in range(dim):
            mean[i] += vec[i]

    for i in range(dim):
        mean[i] /= n

    return mean
