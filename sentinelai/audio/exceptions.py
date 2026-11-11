"""SentinelAI Audio Preprocessing Exceptions.

Defines custom domain exceptions for audio validation, corruption detection,
and preprocessing failures.
"""

from typing import Optional


class SentinelAudioError(Exception):
    """Base exception for all SentinelAI audio preprocessing errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class AudioFileCorruptedError(SentinelAudioError):
    """Raised when an audio file cannot be decoded or has a corrupt header/payload."""
    pass


class EmptyAudioFileError(SentinelAudioError):
    """Raised when an audio file has zero bytes or contains zero audio samples."""
    pass


class AudioDurationError(SentinelAudioError):
    """Raised when audio recording duration falls outside allowed [min, max] boundaries."""

    def __init__(
        self,
        message: str,
        duration_sec: float,
        min_duration_sec: float,
        max_duration_sec: float,
        details: Optional[dict] = None,
    ) -> None:
        extra = {
            "duration_sec": duration_sec,
            "min_duration_sec": min_duration_sec,
            "max_duration_sec": max_duration_sec,
        }
        if details:
            extra.update(details)
        super().__init__(message, details=extra)
        self.duration_sec = duration_sec
        self.min_duration_sec = min_duration_sec
        self.max_duration_sec = max_duration_sec


class InvalidAudioValueError(SentinelAudioError):
    """Raised when audio array contains invalid numerical values (e.g. NaN, Inf, out of bounds)."""
    pass


class SilentAudioError(SentinelAudioError):
    """Raised when the audio recording is completely silent or below the RMS noise floor."""

    def __init__(
        self,
        message: str,
        rms_energy: float,
        min_rms_energy: float,
        details: Optional[dict] = None,
    ) -> None:
        extra = {
            "rms_energy": rms_energy,
            "min_rms_energy": min_rms_energy,
        }
        if details:
            extra.update(details)
        super().__init__(message, details=extra)
        self.rms_energy = rms_energy
        self.min_rms_energy = min_rms_energy


class AudioValidationError(SentinelAudioError):
    """Raised when general audio validation constraints fail."""
    pass

