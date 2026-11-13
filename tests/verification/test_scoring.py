"""Unit tests for the Speaker Similarity Scoring Component."""

import numpy as np
import pytest
import torch

from sentinelai.verification.exceptions import VerificationScoringError
from sentinelai.verification.scoring import compute_verification_score


class TestVerificationScoring:
    """Mathematical and numerical tests for compute_verification_score."""

    def test_identical_embeddings_similarity_is_one(self) -> None:
        """Identical unit-normalized vectors should yield a cosine similarity of 1.0."""
        vec = np.random.randn(192).astype(np.float32)
        vec = vec / np.linalg.norm(vec)

        score = compute_verification_score(vec, vec)
        assert pytest.approx(score, abs=1e-5) == 1.0

    def test_orthogonal_embeddings_similarity_is_zero(self) -> None:
        """Orthogonal vectors should yield a cosine similarity of ~0.0."""
        vec_a = np.zeros(192, dtype=np.float32)
        vec_b = np.zeros(192, dtype=np.float32)
        vec_a[:96] = 1.0
        vec_b[96:] = 1.0

        score = compute_verification_score(vec_a, vec_b)
        assert pytest.approx(score, abs=1e-6) == 0.0

    def test_opposite_embeddings_similarity_is_minus_one(self) -> None:
        """Diametrically opposite vectors should yield a cosine similarity of -1.0."""
        vec = np.random.randn(192).astype(np.float32)
        vec = vec / np.linalg.norm(vec)

        score = compute_verification_score(vec, -vec)
        assert pytest.approx(score, abs=1e-5) == -1.0

    def test_score_is_strictly_clipped_within_negative_one_and_one(self) -> None:
        """Any minute floating-point rounding excess must be clipped to [-1.0, 1.0]."""
        vec = np.ones(192, dtype=np.float32)
        score = compute_verification_score(vec, vec)
        assert -1.0 <= score <= 1.0

    def test_dimension_mismatch_raises_scoring_error(self) -> None:
        """Mismatched embedding dimensions must raise VerificationScoringError."""
        vec_192 = np.ones(192, dtype=np.float32)
        vec_512 = np.ones(512, dtype=np.float32)

        with pytest.raises(VerificationScoringError, match="Embedding dimension mismatch"):
            compute_verification_score(vec_192, vec_512)

    def test_nan_values_raise_scoring_error(self) -> None:
        """Embeddings with NaN values must raise VerificationScoringError."""
        vec_valid = np.ones(192, dtype=np.float32)
        vec_nan = np.ones(192, dtype=np.float32)
        vec_nan[10] = np.nan

        with pytest.raises(VerificationScoringError, match="NaN detected"):
            compute_verification_score(vec_valid, vec_nan)

    def test_inf_values_raise_scoring_error(self) -> None:
        """Embeddings with Inf values must raise VerificationScoringError."""
        vec_valid = np.ones(192, dtype=np.float32)
        vec_inf = np.ones(192, dtype=np.float32)
        vec_inf[10] = np.inf

        with pytest.raises(VerificationScoringError, match="Infinity detected"):
            compute_verification_score(vec_valid, vec_inf)

    def test_zero_vector_raises_scoring_error(self) -> None:
        """Zero-norm vectors must raise VerificationScoringError."""
        vec_valid = np.ones(192, dtype=np.float32)
        vec_zero = np.zeros(192, dtype=np.float32)

        with pytest.raises(VerificationScoringError, match="zero vector"):
            compute_verification_score(vec_valid, vec_zero)

    def test_empty_vector_raises_scoring_error(self) -> None:
        """Empty vectors must raise VerificationScoringError."""
        vec_valid = np.ones(192, dtype=np.float32)
        vec_empty = np.array([], dtype=np.float32)

        with pytest.raises(VerificationScoringError, match="0 elements"):
            compute_verification_score(vec_valid, vec_empty)

    def test_accepts_torch_tensors_and_numpy_arrays(self) -> None:
        """Function should seamlessly handle both PyTorch Tensors and NumPy arrays."""
        arr = np.random.randn(192).astype(np.float32)
        tensor = torch.from_numpy(arr)

        score = compute_verification_score(tensor, arr)
        assert pytest.approx(score, abs=1e-5) == 1.0

