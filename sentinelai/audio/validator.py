"""Validation logic for audio inputs, file headers, duration, and numerical integrity."""

import io
from pathlib import Path
from typing import BinaryIO, Tuple, Union
import numpy as np

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.exceptions import (
    AudioDurationError,
    AudioFileCorruptedError,
    AudioValidationError,
    EmptyAudioFileError,
    InvalidAudioValueError,
    SilentAudioError,
)
from sentinelai.audio.metrics import AudioMetrics


def validate_audio_header(
    source: Union[bytes, BinaryIO, Path, str],
    allowed_formats: Tuple[str, ...] = ("WAV", "FLAC"),
) -> str:
    """Verify that the input has a valid container header for supported formats (WAV, FLAC).

    Args:
        source: Audio source as bytes, open binary buffer, or file path.
        allowed_formats: Tuple of allowed format names (default: ("WAV", "FLAC")).

    Returns:
        Detected format string: 'WAV' or 'FLAC'.

    Raises:
        EmptyAudioFileError: If source is zero bytes.
        AudioFileCorruptedError: If header does not conform to WAV or FLAC specifications.
    """
    header_bytes: bytes

    if isinstance(source, bytes):
        if len(source) == 0:
            raise EmptyAudioFileError("Provided audio byte buffer is empty (0 bytes).")
        if len(source) < 4:
            raise AudioFileCorruptedError("Audio buffer is truncated (less than 4 bytes).")
        header_bytes = source[:12]
    elif isinstance(source, (io.BytesIO, io.BufferedReader)):
        current_pos = source.tell()
        header_bytes = source.read(12)
        source.seek(current_pos)
        if len(header_bytes) == 0:
            raise EmptyAudioFileError("Audio stream is empty (0 bytes).")
        if len(header_bytes) < 4:
            raise AudioFileCorruptedError("Audio stream is truncated (less than 4 bytes).")
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            raise FileNotFoundError(f"Audio file does not exist: {p}")
        if not p.is_file():
            raise AudioValidationError(f"Audio path is not a regular file: {p}")
        size = p.stat().st_size
        if size == 0:
            raise EmptyAudioFileError(f"Audio file is empty (0 bytes): {p}")
        if size < 4:
            raise AudioFileCorruptedError(f"Audio file is truncated (only {size} bytes): {p}")
        with open(p, "rb") as f:
            header_bytes = f.read(12)
    else:
        raise AudioValidationError(f"Unsupported source type for header check: {type(source)}")

    chunk_id = header_bytes[:4]

    # 1. FLAC container check: starts with 'fLaC' stream marker
    if chunk_id == b"fLaC":
        if "FLAC" not in allowed_formats:
            raise AudioFileCorruptedError(
                f"Audio format 'FLAC' detected but not permitted in allowed formats: {allowed_formats}"
            )
        return "FLAC"

    # 2. WAV container check: starts with RIFF/RIFX and has WAVE at offset 8..12
    if chunk_id in (b"RIFF", b"RIFX"):
        if len(header_bytes) < 12:
            raise AudioFileCorruptedError("Audio buffer is truncated (less than 12 bytes).")
        format_id = header_bytes[8:12]
        if format_id != b"WAVE":
            raise AudioFileCorruptedError(
                f"Invalid WAV container header: Expected RIFF/WAVE signature, "
                f"got chunk_id={chunk_id!r}, format_id={format_id!r}."
            )
        if "WAV" not in allowed_formats:
            raise AudioFileCorruptedError(
                f"Audio format 'WAV' detected but not permitted in allowed formats: {allowed_formats}"
            )
        return "WAV"

    # Neither valid signature
    raise AudioFileCorruptedError(
        f"Invalid audio container header: Expected RIFF/WAVE or fLaC signature, "
        f"got chunk_id={chunk_id!r}."
    )


def validate_wav_header(source: Union[bytes, BinaryIO, Path, str]) -> None:
    """Verify that the input has a valid RIFF/WAVE header.

    Retained for backward compatibility with strict WAV-only verification workflows.

    Args:
        source: Audio source as bytes, open binary buffer, or file path.

    Raises:
        EmptyAudioFileError: If source is zero bytes.
        AudioFileCorruptedError: If header does not conform to the RIFF/WAVE specification.
    """
    validate_audio_header(source, allowed_formats=("WAV",))


def validate_audio_numeric(audio: np.ndarray) -> None:
    """Detect invalid numerical values such as NaNs, Infs, or empty arrays.

    Args:
        audio: Decoded numpy audio array.

    Raises:
        EmptyAudioFileError: If array contains zero samples.
        InvalidAudioValueError: If array contains NaN or Infinite values.
    """
    if not isinstance(audio, np.ndarray):
        raise InvalidAudioValueError(f"Expected numpy.ndarray, got {type(audio)}")

    if audio.size == 0:
        raise EmptyAudioFileError("Decoded audio contains 0 samples.")

    if np.isnan(audio).any():
        raise InvalidAudioValueError("Audio signal contains invalid numerical values: NaN detected.")

    if np.isinf(audio).any():
        raise InvalidAudioValueError("Audio signal contains invalid numerical values: Infinity detected.")


def validate_duration(
    duration_sec: float,
    min_duration_sec: float,
    max_duration_sec: float,
) -> None:
    """Validate that audio recording duration is within acceptable research module boundaries.

    Args:
        duration_sec: Measured audio duration in seconds.
        min_duration_sec: Minimum acceptable duration.
        max_duration_sec: Maximum acceptable duration.

    Raises:
        AudioDurationError: If duration is below minimum or exceeds maximum.
    """
    if duration_sec < min_duration_sec:
        raise AudioDurationError(
            f"Audio duration {duration_sec:.2f}s is shorter than minimum allowed "
            f"{min_duration_sec:.2f}s.",
            duration_sec=duration_sec,
            min_duration_sec=min_duration_sec,
            max_duration_sec=max_duration_sec,
        )

    if duration_sec > max_duration_sec:
        raise AudioDurationError(
            f"Audio duration {duration_sec:.2f}s exceeds maximum allowed "
            f"{max_duration_sec:.2f}s.",
            duration_sec=duration_sec,
            min_duration_sec=min_duration_sec,
            max_duration_sec=max_duration_sec,
        )


def validate_signal_content(
    audio: np.ndarray,
    metrics: AudioMetrics,
    config: AudioPreprocessingConfig,
) -> None:
    """Validate signal dynamics, checking for silence and clipping.

    Args:
        audio: Mono audio array.
        metrics: Computed audio metrics.
        config: Validation configuration.

    Raises:
        SilentAudioError: If signal is completely silent and detect_silence is True.
        InvalidAudioValueError: If signal exceeds clipping threshold and allow_clipping is False.
    """
    if config.detect_silence and metrics.is_silent:
        raise SilentAudioError(
            f"Audio recording is completely silent or energy is below threshold "
            f"(measured RMS={metrics.rms_energy:.6f}, minimum threshold={config.min_rms_energy:.6f}).",
            rms_energy=metrics.rms_energy,
            min_rms_energy=config.min_rms_energy,
        )

    if not config.allow_clipping and metrics.is_clipped:
        raise InvalidAudioValueError(
            f"Audio signal exceeds acceptable amplitude boundaries "
            f"(peak={metrics.peak_amplitude:.4f}, max_allowed={config.max_peak_amplitude:.4f}). "
            f"Clipping detected."
        )

