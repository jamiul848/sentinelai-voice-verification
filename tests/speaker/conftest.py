"""Test fixtures and mock helpers for the speaker module tests.

IMPORTANT SCIENTIFIC GUARDRAIL:
All test audio signals and synthetic vectors used in these tests are purely mathematical
test fixtures (sine waves, harmonic tones, random arrays) designed strictly to verify
code paths, API contracts, tensor shapes, and numerical stability. They are NOT real human
speaker recordings and carry no biometric validity.
"""

from typing import Tuple
from unittest.mock import MagicMock
import numpy as np
import pytest
import torch

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.model import ECAPAModelLoader


class MockECAPAModel:
    """Mock SpeechBrain EncoderClassifier for fast, offline unit testing.

    Simulates the forward pass of ECAPA-TDNN without requiring network downloads
    or heavy PyTorch neural network forward computation.
    """

    def __init__(self, embedding_dim: int = 192) -> None:
        self.embedding_dim = embedding_dim
        self.eval_called = False

    def eval(self) -> "MockECAPAModel":
        self.eval_called = True
        return self

    def encode_batch(self, wavs: torch.Tensor, wav_lens: torch.Tensor = None) -> torch.Tensor:
        """Simulate SpeechBrain's encode_batch output: shape [batch, 1, embedding_dim]."""
        batch_size = wavs.shape[0] if wavs.ndim >= 2 else 1
        # Generate deterministic, non-zero mock embeddings based on input mean
        seed_val = float(torch.mean(wavs).item()) if wavs.numel() > 0 else 0.5
        generator = torch.Generator().manual_seed(int(abs(seed_val) * 10000) % 100000 + 1)
        raw_emb = torch.randn((batch_size, 1, self.embedding_dim), generator=generator, dtype=torch.float32)
        return raw_emb


@pytest.fixture
def mock_ecapa_model() -> MockECAPAModel:
    """Provide a mock ECAPA-TDNN model with standard 192-dim output."""
    return MockECAPAModel(embedding_dim=192)


@pytest.fixture
def mock_ecapa_model_custom_dim() -> MockECAPAModel:
    """Provide a mock model with non-standard 256-dim output to test dynamic dimension handling."""
    return MockECAPAModel(embedding_dim=256)


@pytest.fixture
def mock_loader(mock_ecapa_model: MockECAPAModel) -> ECAPAModelLoader:
    """Provide an ECAPAModelLoader backed by a MockECAPAModel."""
    config = SpeakerConfig(device="cpu")
    loader = ECAPAModelLoader(config=config)
    loader._model = mock_ecapa_model
    return loader


@pytest.fixture
def sample_embedding_pair_similar() -> Tuple[np.ndarray, np.ndarray]:
    """Generate two highly collinear (similar) synthetic embedding vectors."""
    np.random.seed(42)
    vec1 = np.random.randn(192).astype(np.float32)
    vec1 /= np.linalg.norm(vec1)
    # Add minor noise
    vec2 = vec1 + 0.05 * np.random.randn(192).astype(np.float32)
    vec2 /= np.linalg.norm(vec2)
    return vec1, vec2


@pytest.fixture
def sample_embedding_pair_orthogonal() -> Tuple[np.ndarray, np.ndarray]:
    """Generate two orthogonal synthetic vectors."""
    vec1 = np.zeros(192, dtype=np.float32)
    vec1[:96] = 1.0 / np.sqrt(96)
    vec2 = np.zeros(192, dtype=np.float32)
    vec2[96:] = 1.0 / np.sqrt(96)
    return vec1, vec2

