"""Audio preprocessing configuration models and validation settings."""

from pydantic import BaseModel, Field, model_validator


class AudioPreprocessingConfig(BaseModel):
    """Configuration settings for audio validation and preprocessing pipeline.

    Attributes:
        target_sample_rate: Target sample rate in Hz (default: 16000 Hz for ECAPA-TDNN).
        min_duration_sec: Minimum acceptable audio duration in seconds.
        max_duration_sec: Maximum acceptable audio duration in seconds.
        min_rms_energy: Minimum RMS energy threshold for silence detection.
        detect_silence: Whether to reject recordings that fall below min_rms_energy.
        allow_clipping: Whether to allow signals with peak amplitude exceeding max_peak_amplitude.
        max_peak_amplitude: Maximum peak amplitude threshold for unnormalized inputs.
        normalize_audio: Whether to perform peak normalization on valid audio.
        target_peak: Target peak amplitude when normalization is active (e.g. 0.95).
        strict_wav_format: Whether to enforce RIFF/WAVE container header validation.
        ensure_2d_tensor: Whether the returned PyTorch tensor has shape [1, N] (ECAPA-TDNN batch format).
    """

    target_sample_rate: int = Field(
        default=16000,
        gt=0,
        description="Target sample rate in Hz. ECAPA-TDNN pretrained models standard is 16kHz.",
    )
    min_duration_sec: float = Field(
        default=0.5,
        ge=0.0,
        description="Minimum audio duration in seconds required for speaker verification.",
    )
    max_duration_sec: float = Field(
        default=30.0,
        gt=0.0,
        description="Maximum allowed audio duration in seconds.",
    )
    min_rms_energy: float = Field(
        default=1e-4,
        ge=0.0,
        description="Minimum RMS energy below which audio is flagged as silence.",
    )
    detect_silence: bool = Field(
        default=True,
        description="Reject completely silent or near-silent recordings.",
    )
    allow_clipping: bool = Field(
        default=False,
        description="If False, input signals with peak > max_peak_amplitude will be flagged.",
    )
    max_peak_amplitude: float = Field(
        default=1.0,
        gt=0.0,
        description="Maximum acceptable raw peak amplitude before normalization.",
    )
    normalize_audio: bool = Field(
        default=True,
        description="If True, normalizes peak amplitude of signal to target_peak.",
    )
    target_peak: float = Field(
        default=0.95,
        gt=0.0,
        le=1.0,
        description="Target peak amplitude when normalize_audio is True.",
    )
    strict_wav_format: bool = Field(
        default=True,
        description="Strictly check WAV container RIFF/WAVE header signatures.",
    )
    ensure_2d_tensor: bool = Field(
        default=True,
        description="If True, audio_tensor has shape [1, N]; if False, shape is [N].",
    )

    @model_validator(mode="after")
    def validate_duration_bounds(self) -> "AudioPreprocessingConfig":
        """Ensure min_duration_sec is strictly less than max_duration_sec."""
        if self.min_duration_sec >= self.max_duration_sec:
            raise ValueError(
                f"min_duration_sec ({self.min_duration_sec}s) must be strictly less than "
                f"max_duration_sec ({self.max_duration_sec}s)."
            )
        return self

