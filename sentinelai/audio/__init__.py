"""SentinelAI Audio Preprocessing Module.

Exports preprocessor classes, configuration, exceptions, and metric functions.
"""

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.exceptions import (
    AudioDurationError,
    AudioFileCorruptedError,
    AudioValidationError,
    EmptyAudioFileError,
    InvalidAudioValueError,
    SentinelAudioError,
    SilentAudioError,
)
from sentinelai.audio.metrics import AudioMetrics, compute_audio_metrics
from sentinelai.audio.preprocessor import AudioPreprocessingResult, AudioPreprocessor
from sentinelai.audio.validator import (
    validate_audio_header,
    validate_audio_numeric,
    validate_duration,
    validate_signal_content,
    validate_wav_header,
)

__all__ = [
    "AudioPreprocessingConfig",
    "AudioPreprocessingResult",
    "AudioPreprocessor",
    "AudioMetrics",
    "compute_audio_metrics",
    "validate_audio_header",
    "validate_wav_header",
    "validate_audio_numeric",
    "validate_duration",
    "validate_signal_content",
    "SentinelAudioError",
    "AudioFileCorruptedError",
    "EmptyAudioFileError",
    "AudioDurationError",
    "InvalidAudioValueError",
    "SilentAudioError",
    "AudioValidationError",
]

