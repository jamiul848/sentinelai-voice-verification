"""SentinelAI Speaker Recognition and ECAPA-TDNN Module.

Exports model loaders, embedding extractors, configuration, exceptions,
and similarity functions for speaker verification.
"""

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor, SpeakerEmbeddingResult
from sentinelai.speaker.exceptions import (
    EmbeddingExtractionError,
    InvalidEmbeddingError,
    ModelLoadError,
    SpeakerRecognitionError,
)
from sentinelai.speaker.model import ECAPAModelLoader, get_model_loader
from sentinelai.speaker.similarity import compute_cosine_similarity

__all__ = [
    "SpeakerConfig",
    "ECAPAModelLoader",
    "get_model_loader",
    "SpeakerEmbeddingExtractor",
    "SpeakerEmbeddingResult",
    "compute_cosine_similarity",
    "SpeakerRecognitionError",
    "ModelLoadError",
    "InvalidEmbeddingError",
    "EmbeddingExtractionError",
]

