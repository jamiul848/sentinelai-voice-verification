"""Unit tests for the cosine similarity computation engine."""

import numpy as np
import pytest
import torch

from sentinelai.speaker.embedding import SpeakerEmbeddingResult
from sentinelai.speaker.exceptions import InvalidEmbeddingError
from sentinelai.speaker.similarity import compute_cosine_similarity


class TestCosineSimilarity:
    """Test suite for speaker embedding similarity calculation and validation."""

    def test_identical_embeddings_similarity_is_one(self) -> None:
        """Requirement: Cosine similarity of identical embeddings equals 1.0."""
        vec = np.array([0.2, -0.5, 0.8, 0.1], dtype=np.float32)
        score = compute_cosine_similarity(vec, vec)
        assert pytest.approx(score, abs=1e-6) == 1.0

    def test_opposite_embeddings_similarity_is_minus_one(self) -> None:
        """Requirement: Cosine similarity of diametrically opposite vectors equals -1.0."""
        vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        opposite_vec = -1.0 * vec
        score = compute_cosine_similarity(vec, opposite_vec)
        assert pytest.approx(score, abs=1e-6) == -1.0

    def test_orthogonal_embeddings_similarity_is_zero(
        self, sample_embedding_pair_orthogonal: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Requirement: Cosine similarity of orthogonal vectors equals 0.0."""
        vec_a, vec_b = sample_embedding_pair_orthogonal
        score = compute_cosine_similarity(vec_a, vec_b)
        assert pytest.approx(score, abs=1e-6) == 0.0

    def test_clipping_minor_floating_point_deviations(self) -> None:
        """Requirement: Values slightly exceeding [-1, 1] due to floating precision are clamped."""
        vec = np.array([1.0, 1.0], dtype=np.float32)
        # Identical vector calculation should never exceed 1.0
        score = compute_cosine_similarity(vec, vec)
        assert -1.0 <= score <= 1.0

    def test_dimension_mismatch_raises_error(self) -> None:
        """Requirement: Rejection of mismatched embedding dimensions."""
        vec_192 = np.ones(192, dtype=np.float32)
        vec_256 = np.ones(256, dtype=np.float32)

        with pytest.raises(InvalidEmbeddingError) as exc_info:
            compute_cosine_similarity(vec_192, vec_256)
        assert "dimension mismatch" in str(exc_info.value).lower()
        assert "192" in str(exc_info.value)
        assert "256" in str(exc_info.value)

    def test_zero_vector_rejection(self) -> None:
        """Requirement: Rejection of degenerate zero vectors."""
        zero_vec = np.zeros(192, dtype=np.float32)
        normal_vec = np.ones(192, dtype=np.float32)

        with pytest.raises(InvalidEmbeddingError) as exc_info1:
            compute_cosine_similarity(zero_vec, normal_vec)
        assert "zero vector" in str(exc_info1.value).lower()

        with pytest.raises(InvalidEmbeddingError) as exc_info2:
            compute_cosine_similarity(normal_vec, zero_vec)
        assert "zero vector" in str(exc_info2.value).lower()

    def test_nan_embedding_rejection(self) -> None:
        """Requirement: Detection and rejection of NaN values in embeddings."""
        vec_nan = np.array([0.5, np.nan, 0.2], dtype=np.float32)
        valid_vec = np.array([0.5, 0.1, 0.2], dtype=np.float32)

        with pytest.raises(InvalidEmbeddingError) as exc_info:
            compute_cosine_similarity(vec_nan, valid_vec)
        assert "NaN detected" in str(exc_info.value)

    def test_inf_embedding_rejection(self) -> None:
        """Requirement: Detection and rejection of Inf values in embeddings."""
        vec_inf = np.array([0.5, np.inf, 0.2], dtype=np.float32)
        valid_vec = np.array([0.5, 0.1, 0.2], dtype=np.float32)

        with pytest.raises(InvalidEmbeddingError) as exc_info:
            compute_cosine_similarity(valid_vec, vec_inf)
        assert "Infinity detected" in str(exc_info.value)

    def test_empty_embedding_rejection(self) -> None:
        """Requirement: Detection and rejection of empty arrays."""
        empty_vec = np.array([], dtype=np.float32)
        valid_vec = np.array([0.1, 0.2], dtype=np.float32)

        with pytest.raises(InvalidEmbeddingError) as exc_info:
            compute_cosine_similarity(empty_vec, valid_vec)
        assert "empty" in str(exc_info.value).lower()

    def test_accepts_torch_tensors_and_numpy_arrays(self) -> None:
        """Verify seamless cross-format support between PyTorch and NumPy."""
        vec_np = np.array([0.3, 0.4], dtype=np.float32)
        vec_torch = torch.tensor([0.3, 0.4], dtype=torch.float32)

        score = compute_cosine_similarity(vec_np, vec_torch)
        assert pytest.approx(score, abs=1e-6) == 1.0

    def test_accepts_speaker_embedding_result_object(self) -> None:
        """Verify acceptance of structured SpeakerEmbeddingResult objects."""
        raw_a = np.array([1.0, 0.0], dtype=np.float32)
        raw_b = np.array([0.0, 1.0], dtype=np.float32)

        result_a = SpeakerEmbeddingResult(
            embedding=raw_a,
            embedding_tensor=torch.tensor(raw_a),
            dimension=2,
            model_id="test-model",
            device="cpu",
            audio_duration_sec=1.0,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        result_b = SpeakerEmbeddingResult(
            embedding=raw_b,
            embedding_tensor=torch.tensor(raw_b),
            dimension=2,
            model_id="test-model",
            device="cpu",
            audio_duration_sec=1.0,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )

        score = compute_cosine_similarity(result_a, result_b)
        assert pytest.approx(score, abs=1e-6) == 0.0

