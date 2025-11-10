"""
Tests for vector utility functions.
"""

import pytest
import math
from app.utils.vector_utils import (
    cosine_similarity,
    euclidean_distance,
    dot_product,
    normalize_vector,
    find_top_k_similar,
    vector_magnitude,
    mean_vector
)


class TestCosineSimilarity:
    """Test cosine similarity function."""

    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        vec = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 1e-10

    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 1e-10

    def test_opposite_vectors(self):
        """Test similarity of opposite vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 1e-10

    def test_different_dimensions_raises_error(self):
        """Test that different dimensions raise ValueError."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError):
            cosine_similarity(vec1, vec2)

    def test_empty_vector_raises_error(self):
        """Test that empty vectors raise ValueError."""
        with pytest.raises(ValueError):
            cosine_similarity([], [1.0, 2.0])


class TestEuclideanDistance:
    """Test Euclidean distance function."""

    def test_identical_vectors(self):
        """Test distance of identical vectors."""
        vec = [1.0, 2.0, 3.0]
        distance = euclidean_distance(vec, vec)
        assert abs(distance - 0.0) < 1e-10

    def test_unit_distance(self):
        """Test unit distance."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        distance = euclidean_distance(vec1, vec2)
        assert abs(distance - 1.0) < 1e-10

    def test_pythagorean_distance(self):
        """Test distance using Pythagorean theorem."""
        vec1 = [0.0, 0.0]
        vec2 = [3.0, 4.0]
        distance = euclidean_distance(vec1, vec2)
        assert abs(distance - 5.0) < 1e-10

    def test_different_dimensions_raises_error(self):
        """Test that different dimensions raise ValueError."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError):
            euclidean_distance(vec1, vec2)


class TestDotProduct:
    """Test dot product function."""

    def test_simple_dot_product(self):
        """Test simple dot product calculation."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [4.0, 5.0, 6.0]
        result = dot_product(vec1, vec2)
        # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        assert abs(result - 32.0) < 1e-10

    def test_orthogonal_vectors_dot_product(self):
        """Test dot product of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        result = dot_product(vec1, vec2)
        assert abs(result - 0.0) < 1e-10


class TestNormalizeVector:
    """Test vector normalization function."""

    def test_normalize_simple_vector(self):
        """Test normalization of a simple vector."""
        vec = [3.0, 4.0]
        normalized = normalize_vector(vec)
        # Magnitude should be 1
        magnitude = math.sqrt(sum(x**2 for x in normalized))
        assert abs(magnitude - 1.0) < 1e-10
        # Direction should be preserved
        assert abs(normalized[0] - 0.6) < 1e-10
        assert abs(normalized[1] - 0.8) < 1e-10

    def test_normalize_unit_vector(self):
        """Test normalization of already normalized vector."""
        vec = [1.0, 0.0, 0.0]
        normalized = normalize_vector(vec)
        assert normalized == vec

    def test_normalize_zero_vector_raises_error(self):
        """Test that zero vector raises ValueError."""
        with pytest.raises(ValueError):
            normalize_vector([0.0, 0.0, 0.0])


class TestFindTopKSimilar:
    """Test top-k similarity search."""

    def test_find_top_k_cosine(self):
        """Test finding top-k similar vectors using cosine similarity."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            ("a", [1.0, 0.0, 0.0]),  # Identical
            ("b", [0.5, 0.5, 0.0]),  # 45 degrees
            ("c", [0.0, 1.0, 0.0]),  # Orthogonal
            ("d", [-1.0, 0.0, 0.0]), # Opposite
        ]

        results = find_top_k_similar(query, candidates, k=2, similarity_fn="cosine")

        assert len(results) == 2
        assert results[0][0] == "a"  # Most similar
        assert results[0][1] > results[1][1]  # Scores decreasing

    def test_find_top_k_euclidean(self):
        """Test finding top-k similar vectors using Euclidean distance."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            ("a", [1.0, 0.0, 0.0]),  # Distance 0
            ("b", [2.0, 0.0, 0.0]),  # Distance 1
            ("c", [0.0, 0.0, 0.0]),  # Distance 1
            ("d", [10.0, 0.0, 0.0]), # Distance 9
        ]

        results = find_top_k_similar(query, candidates, k=2, similarity_fn="euclidean")

        assert len(results) == 2
        assert results[0][0] == "a"  # Closest
        assert results[0][1] < results[1][1]  # Distances increasing

    def test_find_top_k_invalid_similarity_fn(self):
        """Test that invalid similarity function raises error."""
        query = [1.0, 0.0]
        candidates = [("a", [1.0, 0.0])]

        with pytest.raises(ValueError):
            find_top_k_similar(query, candidates, k=1, similarity_fn="invalid")

    def test_find_top_k_empty_candidates_raises_error(self):
        """Test that empty candidates raise error."""
        query = [1.0, 0.0]
        with pytest.raises(ValueError):
            find_top_k_similar(query, [], k=1)


class TestVectorMagnitude:
    """Test vector magnitude function."""

    def test_magnitude_unit_vector(self):
        """Test magnitude of unit vector."""
        vec = [1.0, 0.0, 0.0]
        mag = vector_magnitude(vec)
        assert abs(mag - 1.0) < 1e-10

    def test_magnitude_pythagorean(self):
        """Test magnitude using Pythagorean theorem."""
        vec = [3.0, 4.0]
        mag = vector_magnitude(vec)
        assert abs(mag - 5.0) < 1e-10

    def test_magnitude_zero_vector(self):
        """Test magnitude of zero vector."""
        vec = [0.0, 0.0, 0.0]
        mag = vector_magnitude(vec)
        assert abs(mag - 0.0) < 1e-10


class TestMeanVector:
    """Test mean vector function."""

    def test_mean_of_two_vectors(self):
        """Test mean of two vectors."""
        vecs = [[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]]
        mean = mean_vector(vecs)
        assert mean == [2.0, 3.0, 4.0]

    def test_mean_of_single_vector(self):
        """Test mean of single vector."""
        vecs = [[1.0, 2.0, 3.0]]
        mean = mean_vector(vecs)
        assert mean == [1.0, 2.0, 3.0]

    def test_mean_empty_list_raises_error(self):
        """Test that empty list raises error."""
        with pytest.raises(ValueError):
            mean_vector([])

    def test_mean_different_dimensions_raises_error(self):
        """Test that different dimensions raise error."""
        vecs = [[1.0, 2.0], [1.0, 2.0, 3.0]]
        with pytest.raises(ValueError):
            mean_vector(vecs)
