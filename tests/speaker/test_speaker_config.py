"""Unit tests for the SpeakerConfig settings."""

from pathlib import Path
from unittest.mock import patch
import pytest
import torch

from sentinelai.speaker.config import SpeakerConfig


class TestSpeakerConfig:
    """Test suite covering configuration loading, path normalization, and device resolution."""

    def test_default_config_values(self) -> None:
        """Verify standard ECAPA-TDNN default configuration."""
        config = SpeakerConfig()
        assert config.model_source == "speechbrain/spkrec-ecapa-voxceleb"
        assert isinstance(config.savedir, Path)
        assert config.expected_sample_rate == 16000
        assert config.normalize_embeddings is True
        assert config.device == "auto"

    def test_savedir_string_conversion(self) -> None:
        """Verify string path is automatically normalized to pathlib.Path."""
        config = SpeakerConfig(savedir="custom/cache/dir")
        assert isinstance(config.savedir, Path)
        assert config.savedir == Path("custom/cache/dir")

    def test_auto_device_resolution_on_cpu(self) -> None:
        """Verify device='auto' resolves to 'cpu' when CUDA is unavailable."""
        with patch.object(torch.cuda, "is_available", return_value=False):
            config = SpeakerConfig(device="auto")
            assert config.resolved_device == "cpu"
            assert config.torch_device == torch.device("cpu")

    def test_auto_device_resolution_on_cuda(self) -> None:
        """Verify device='auto' resolves to 'cuda' when CUDA is available."""
        with patch.object(torch.cuda, "is_available", return_value=True):
            config = SpeakerConfig(device="auto")
            assert config.resolved_device == "cuda"
            assert config.torch_device == torch.device("cuda")

    def test_explicit_cuda_requested_when_unavailable_raises_error(self) -> None:
        """Requirement: Explicitly validate CUDA availability when CUDA is requested."""
        with patch.object(torch.cuda, "is_available", return_value=False):
            with pytest.raises(ValueError) as exc_info:
                SpeakerConfig(device="cuda")
            assert "CUDA device was explicitly requested" in str(exc_info.value)
            assert "not available on this system" in str(exc_info.value)

    def test_explicit_cpu_request(self) -> None:
        """Verify device='cpu' is respected even if CUDA were available."""
        with patch.object(torch.cuda, "is_available", return_value=True):
            config = SpeakerConfig(device="cpu")
            assert config.resolved_device == "cpu"

    def test_invalid_sample_rate_rejected(self) -> None:
        """Verify non-positive sample rate is rejected by Pydantic."""
        with pytest.raises(Exception):
            SpeakerConfig(expected_sample_rate=0)

