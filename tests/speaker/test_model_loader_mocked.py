"""Mocked unit tests for the ECAPAModelLoader.

These tests run purely in memory without hitting the network or downloading checkpoints.
"""

from unittest.mock import MagicMock, patch
import pytest

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.exceptions import ModelLoadError
from sentinelai.speaker.model import ECAPAModelLoader


class TestECAPAModelLoaderMocked:
    """Test suite covering lazy loading, caching, device resolution, and lifecycle methods."""

    def test_lazy_initialization(self) -> None:
        """Requirement: Model should not be loaded into memory until load() is called."""
        config = SpeakerConfig(device="cpu")
        loader = ECAPAModelLoader(config=config)
        assert loader.is_loaded is False

    def test_model_loading_and_caching(self, mock_ecapa_model: MagicMock) -> None:
        """Requirement: Repeated load() calls return the cached instance without reloading."""
        config = SpeakerConfig(device="cpu")
        loader = ECAPAModelLoader(config=config)

        with patch("speechbrain.inference.speaker.EncoderClassifier.from_hparams", return_value=mock_ecapa_model) as mock_from_hparams:
            # First call -> loads and caches
            model1 = loader.load()
            assert loader.is_loaded is True
            assert model1 is mock_ecapa_model
            assert mock_from_hparams.call_count == 1

            # Second call -> returns cached instance without calling from_hparams again
            model2 = loader.load()
            assert model2 is model1
            assert mock_from_hparams.call_count == 1

    def test_force_reload(self, mock_ecapa_model: MagicMock) -> None:
        """Verify force_reload=True triggers re-initialization."""
        config = SpeakerConfig(device="cpu")
        loader = ECAPAModelLoader(config=config)

        with patch("speechbrain.inference.speaker.EncoderClassifier.from_hparams", return_value=mock_ecapa_model) as mock_from_hparams:
            loader.load()
            loader.load(force_reload=True)
            assert mock_from_hparams.call_count == 2

    def test_unload_lifecycle(self, mock_ecapa_model: MagicMock) -> None:
        """Verify unload() frees the model and resets is_loaded state."""
        config = SpeakerConfig(device="cpu")
        loader = ECAPAModelLoader(config=config)
        loader._model = mock_ecapa_model
        assert loader.is_loaded is True

        loader.unload()
        assert loader.is_loaded is False
        assert loader._model is None

    def test_model_loading_failure_raises_model_load_error(self) -> None:
        """Requirement: Clear errors if model loading fails."""
        config = SpeakerConfig(device="cpu")
        loader = ECAPAModelLoader(config=config)

        with patch(
            "speechbrain.inference.speaker.EncoderClassifier.from_hparams",
            side_effect=RuntimeError("Simulated network timeout during download"),
        ):
            with pytest.raises(ModelLoadError) as exc_info:
                loader.load()

            assert "Failed to load pretrained ECAPA-TDNN model" in str(exc_info.value)
            assert loader.is_loaded is False

