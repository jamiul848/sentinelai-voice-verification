"""Audio signal metrics computation (duration, sample rate, RMS energy, peak amplitude)."""

import math
from typing import Optional
import numpy as np
from pydantic import BaseModel, Field


class AudioMetrics(BaseModel):
    """Structured container for audio quantitative metrics.

    Attributes:
        sample_rate: Sample rate in Hz.
        duration_sec: Audio duration in seconds.
        num_samples: Total number of discrete audio samples.
        num_channels: Channel count (1 for mono).
        rms_energy: Root Mean Square energy of the audio signal.
        peak_amplitude: Maximum absolute amplitude of the signal.
        rms_dbfs: RMS energy in decibels relative to full scale (dBFS).
        peak_dbfs: Peak amplitude in decibels relative to full scale (dBFS).
        is_silent: True if RMS energy is below the silence threshold.
        is_clipped: True if peak amplitude strictly exceeds 1.0 (or max peak threshold).
    """

    sample_rate: int = Field(..., gt=0, description="Audio sample rate in Hz.")
    duration_sec: float = Field(..., ge=0.0, description="Duration in seconds.")
    num_samples: int = Field(..., ge=0, description="Total sample count.")
    num_channels: int = Field(default=1, ge=1, description="Number of channels.")
    rms_energy: float = Field(..., ge=0.0, description="Root Mean Square (RMS) energy.")
    peak_amplitude: float = Field(..., ge=0.0, description="Peak absolute amplitude.")
    rms_dbfs: float = Field(..., description="RMS energy in dBFS.")
    peak_dbfs: float = Field(..., description="Peak amplitude in dBFS.")
    is_silent: bool = Field(default=False, description="Flag indicating silent/low-energy audio.")
    is_clipped: bool = Field(default=False, description="Flag indicating potential digital clipping.")


def compute_audio_metrics(
    audio: np.ndarray,
    sample_rate: int,
    min_rms_energy: float = 1e-4,
    max_peak_amplitude: float = 1.0,
    num_channels: Optional[int] = None,
) -> AudioMetrics:
    """Calculate key acoustic and signal metrics for an audio array.

    Args:
        audio: 1D or 2D numpy array representing floating point audio samples.
        sample_rate: Sample rate in Hz.
        min_rms_energy: Minimum RMS energy threshold for silence classification.
        max_peak_amplitude: Peak threshold beyond which clipping is detected.
        num_channels: Optional channel count override (defaults to 1 or audio shape).

    Returns:
        AudioMetrics model populated with calculated values.
    """
    if sample_rate <= 0:
        raise ValueError(f"Sample rate must be positive, got {sample_rate}")

    if audio.size == 0:
        return AudioMetrics(
            sample_rate=sample_rate,
            duration_sec=0.0,
            num_samples=0,
            num_channels=num_channels or 1,
            rms_energy=0.0,
            peak_amplitude=0.0,
            rms_dbfs=-120.0,
            peak_dbfs=-120.0,
            is_silent=True,
            is_clipped=False,
        )

    # Flatten audio for overall signal-level statistics
    flat_audio = audio.astype(np.float64, copy=False).ravel()

    # Peak amplitude
    peak = float(np.max(np.abs(flat_audio)))

    # RMS energy = sqrt(mean(x^2))
    mean_square = float(np.mean(flat_audio**2))
    rms = float(np.sqrt(mean_square))

    # Calculate dBFS with a floor of -120 dBFS
    eps = 1e-9
    peak_dbfs = 20.0 * math.log10(max(peak, eps))
    rms_dbfs = 20.0 * math.log10(max(rms, eps))

    # Clamp dbfs floor
    peak_dbfs = max(peak_dbfs, -120.0)
    rms_dbfs = max(rms_dbfs, -120.0)

    # In 1D arrays, samples = len(audio)
    num_samples = len(audio) if audio.ndim == 1 else audio.shape[0]
    duration_sec = float(num_samples / sample_rate)

    detected_channels = num_channels if num_channels is not None else (audio.shape[1] if audio.ndim > 1 else 1)

    is_silent = rms < min_rms_energy
    # Tolerant epsilon for floating precision
    is_clipped = peak > (max_peak_amplitude + 1e-4)

    return AudioMetrics(
        sample_rate=sample_rate,
        duration_sec=duration_sec,
        num_samples=num_samples,
        num_channels=detected_channels,
        rms_energy=rms,
        peak_amplitude=peak,
        rms_dbfs=round(rms_dbfs, 2),
        peak_dbfs=round(peak_dbfs, 2),
        is_silent=is_silent,
        is_clipped=is_clipped,
    )

