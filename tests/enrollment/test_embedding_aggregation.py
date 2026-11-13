"""Unit tests for the reference embedding aggregation algorithm."""

from typing import List
import numpy as np
import pytest

from sentinelai.enrollment.aggregation import aggregate_embeddings
from sentinelai.enrollment.exceptions import AggregationError


class TestEmbeddingAggregation:
    """Test suite covering vector averaging, L2 normalization, and numerical checks."""

    def test_aggregation_mean_and_l2_norm(self) -> None:
        """Requirement: Calculate mean vector and L2-normalize the result."""
        # 3 deterministic orthogonal-ish vectors
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        v3 = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        result = aggregate_embeddings([v1, v2, v3])

        # Expected arithmetic mean is [1/3, 1/3, 1/3]
        # L2 norm of [1/3, 1/3, 1/3] is sqrt(3/9) = 1/sqrt(3)
        # Normalized vector is [1/sqrt(3), 1/sqrt(3), 1/sqrt(3)]
        expected = np.array([1.0 / np.sqrt(3), 1.0 / np.sqrt(3), 1.0 / np.sqrt(3)], dtype=np.float32)
        np.testing.assert_allclose(result.reference_embedding, expected, atol=1e-6)

        # Assert reference embedding has Euclidean norm == 1.0
        norm = float(np.linalg.norm(result.reference_embedding))
        assert pytest.approx(norm, abs=1e-5) == 1.0

        assert result.dimension == 3
        assert result.sample_count == 3
        assert len(result.individual_embeddings) == 3

    def test_dimension_mismatch_raises_error(self) -> None:
        """Requirement: Reject incompatible embedding dimensions."""
        v1 = np.ones(192, dtype=np.float32)
        v2 = np.ones(192, dtype=np.float32)
        v3 = np.ones(256, dtype=np.float32)  # Mismatched dimension

        with pytest.raises(AggregationError) as exc_info:
            aggregate_embeddings([v1, v2, v3])
        assert "dimension mismatch at index 2" in str(exc_info.value).lower()

    def test_nan_embedding_raises_error(self) -> None:
        """Requirement: Reject NaN values in embeddings."""
        v1 = np.ones(192, dtype=np.float32)
        v2 = np.array([np.nan] * 192, dtype=np.float32)

        with pytest.raises(AggregationError) as exc_info:
            aggregate_embeddings([v1, v2])
        assert "NaN values" in str(exc_info.value)

    def test_infinity_embedding_raises_error(self) -> None:
        """Requirement: Reject Infinity values in embeddings."""
        v1 = np.ones(192, dtype=np.float32)
        v2 = np.array([np.inf] * 192, dtype=np.float32)

        with pytest.raises(AggregationError) as exc_info:
            aggregate_embeddings([v1, v2])
        assert "Infinite values" in str(exc_info.value)

    def test_zero_vector_raises_error(self) -> None:
        """Requirement: Reject zero-norm vectors."""
        v1 = np.ones(192, dtype=np.float32)
        v2 = np.zeros(192, dtype=np.float32)

        with pytest.raises(AggregationError) as exc_info:
            aggregate_embeddings([v1, v2])
        assert "zero-vector" in str(exc_info.value).lower()

    def test_empty_list_raises_error(self) -> None:
        """Requirement: Reject empty embedding list."""
        with pytest.raises(AggregationError) as exc_info:
            aggregate_embeddings([])
        assert "empty list" in str(exc_info.value).lower()

    def test_pairwise_consistency_metrics(self) -> None:
        """Requirement: Calculate intra-session pairwise consistency diagnostics."""
        # 3 identical vectors
        v = np.random.randn(192).astype(np.float32)
        v /= np.linalg.norm(v)

        result = aggregate_embeddings([v, v, v])
        assert pytest.approx(result.mean_pairwise_similarity, abs=1e-4) == 1.0
        assert pytest.approx(result.min_pairwise_similarity, abs=1e-4) == 1.0
        assert result.metrics["sample_count"] == 3

