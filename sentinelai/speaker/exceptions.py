"""SentinelAI Speaker Recognition Exceptions.

Defines domain-specific exceptions for pretrained model loading, embedding extraction,
and acoustic similarity computation.
"""

from typing import Optional


class SpeakerRecognitionError(Exception):
    """Base exception for all speaker recognition module errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class ModelLoadError(SpeakerRecognitionError):
    """Raised when the pretrained model cannot be downloaded, cached, or initialized."""
    pass


class InvalidEmbeddingError(SpeakerRecognitionError):
    """Raised when an embedding is malformed, contains NaNs/Infs, has zero norm, or has invalid dimensions."""
    pass


class EmbeddingExtractionError(SpeakerRecognitionError):
    """Raised when embedding extraction fails during model inference."""
    pass

