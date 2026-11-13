"""Mocked unit tests for SpeakerEmbeddingExtractor.

Verifies tensor manipulation, dynamic dimension determination, L2 normalization,
and error handling without executing heavy deep learning neural nets.
"""

from unittest.mock import MagicMock
import numpy as np
import pytest
import torch

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor, SpeakerEmbeddingResult
from sentinelai.speaker.exceptions import EmbeddingExtractionError, InvalidEmbeddingError
from sentinelai.speaker.model import ECAPAModelLoader
from tests.speaker.conftest import MockECAPAModel


class TestSpeakerEmbeddingExtractorMocked:
    """Test suite covering embedding extraction mechanics, normalization, and validation."""

    def test_embedding_extraction_from_tensor(self, mock_loader: ECAPAModelLoader) -> None:
        """Requirement: Extract embedding from audio tensor and verify output structure."""
        extractor = SpeakerEmbeddingExtractor(loader=mock_loader)
        # Synthetic 16kHz audio tensor (1 second = 16000 samples)
        audio_tensor = torch.zeros((1, 16000), dtype=torch.float32)

        result = extractor.extract(audio_tensor, source_id="test-tensor")

        assert isinstance(result, SpeakerEmbeddingResult)
        assert isinstance(result.embedding, np.ndarray)
        assert isinstance(result.embedding_tensor, torch.Tensor)
        assert result.embedding.ndim == 1
        assert result.dimension == 192
        assert result.device == "cpu"
        assert result.normalized is True
        assert pytest.approx(float(np.linalg.norm(result.embedding)), abs=1e-5) == 1.0
        assert result.metadata["source_id"] == "test-tensor"

    def test_dynamic_dimension_determination(self) -> None:
        """Requirement: Dynamically determine embedding dimension without hardcoding 192."""
        # Test with a mock model outputting 256 dimensions
        mock_256 = MockECAPAModel(embedding_dim=256)
        config = SpeakerConfig(device="cpu")
        loader = ECAPAModelLoader(config=config)
        loader._model = mock_256

        extractor = SpeakerEmbeddingExtractor(config=config, loader=loader)
        audio_tensor = torch.randn((1, 16000), dtype=torch.float32)

        result = extractor.extract(audio_tensor)
        # Asserts dimension was dynamically read as 256, not hardcoded
        assert result.dimension == 256
        assert len(result.embedding) == 256
        assert result.embedding_tensor.shape == (256,)

    def test_l2_normalization_disabled(self, mock_loader: ECAPAModelLoader) -> None:
        """Verify normalize_embeddings=False retains raw model scaling."""
        config = SpeakerConfig(device="cpu", normalize_embeddings=False)
        extractor = SpeakerEmbeddingExtractor(config=config, loader=mock_loader)
        audio_tensor = torch.randn((1, 16000), dtype=torch.float32)

        result = extractor.extract(audio_tensor)
        assert result.normalized is False

    def test_detect_nan_in_model_output(self) -> None:
        """Requirement: Detection of NaN values in model output embeddings."""
        mock_model = MagicMock()
        # Mock returning an embedding containing NaN
        mock_model.encode_batch.return_value = torch.tensor([[[0.1, np.nan, 0.3]]], dtype=torch.float32)

        loader = ECAPAModelLoader(config=SpeakerConfig(device="cpu"))
        loader._model = mock_model
        extractor = SpeakerEmbeddingExtractor(loader=loader)

        with pytest.raises(InvalidEmbeddingError) as exc_info:
            extractor.extract(torch.zeros((1, 16000)))
        assert "NaN detected" in str(exc_info.value)

    def test_detect_inf_in_model_output(self) -> None:
        """Requirement: Detection of Inf values in model output embeddings."""
        mock_model = MagicMock()
        mock_model.encode_batch.return_value = torch.tensor([[[0.1, np.inf, 0.3]]], dtype=torch.float32)

        loader = ECAPAModelLoader(config=SpeakerConfig(device="cpu"))
        loader._model = mock_model
        extractor = SpeakerEmbeddingExtractor(loader=loader)

        with pytest.raises(InvalidEmbeddingError) as exc_info:
            extractor.extract(torch.zeros((1, 16000)))
        assert "Infinity detected" in str(exc_info.value)

    def test_zero_vector_normalization_rejection(self) -> None:
        """Requirement: Rejection of degenerate zero vectors during L2 normalization."""
        mock_model = MagicMock()
        mock_model.encode_batch.return_value = torch.zeros((1, 1, 192), dtype=torch.float32)

        loader = ECAPAModelLoader(config=SpeakerConfig(device="cpu"))
        loader._model = mock_model
        extractor = SpeakerEmbeddingExtractor(loader=loader)

        with pytest.raises(InvalidEmbeddingError) as exc_info:
            extractor.extract(torch.zeros((1, 16000)))
        assert "zero vector" in str(exc_info.value).lower()

    def test_model_inference_exception_wrapped(self) -> None:
        """Verify model runtime exceptions are wrapped in EmbeddingExtractionError."""
        mock_model = MagicMock()
        mock_model.encode_batch.side_effect = RuntimeError("CUDA out of memory or device fault")

        loader = ECAPAModelLoader(config=SpeakerConfig(device="cpu"))
        loader._model = mock_model
        extractor = SpeakerEmbeddingExtractor(loader=loader)

        with pytest.raises(EmbeddingExtractionError) as exc_info:
            extractor.extract(torch.zeros((1, 16000)))
        assert "inference failed" in str(exc_info.value).lower()

    def test_result_to_dict_serialization(self, mock_loader: ECAPAModelLoader) -> None:
        """Verify JSON-serializable dictionary structure."""
        extractor = SpeakerEmbeddingExtractor(loader=mock_loader)
        result = extractor.extract(torch.zeros((1, 16000)), source_id="rec-001")
        d = result.to_dict()

        assert d["model_id"] == "speechbrain/spkrec-ecapa-voxceleb"
        assert d["dimension"] == 192
        assert d["device"] == "cpu"
        assert d["normalized"] is True
        assert pytest.approx(d["embedding_l2_norm"], abs=1e-5) == 1.0
        assert "extraction_timestamp" in d

