"""SentinelAI Audio Preprocessing Module.

Preprocesses WAV audio for ECAPA-TDNN speaker verification pipelines:
- Converts stereo/multi-channel to mono.
- Resamples to the target model sample rate (default: 16 kHz).
- Validates recording duration boundaries.
- Rejects empty, corrupted, and invalid numerical audio.
- Calculates RMS energy, peak amplitude, duration, and dBFS metrics.
- Provides peak normalization and outputs structured PyTorch tensors.
"""

from dataclasses import dataclass, field
import io
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import librosa
import numpy as np
import soundfile as sf
import torch

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.exceptions import (
    AudioFileCorruptedError,
    AudioValidationError,
    EmptyAudioFileError,
    InvalidAudioValueError,
)
from sentinelai.audio.metrics import AudioMetrics, compute_audio_metrics
from sentinelai.audio.validator import (
    validate_audio_numeric,
    validate_duration,
    validate_signal_content,
    validate_wav_header,
)


@dataclass
class AudioPreprocessingResult:
    """Structured container returned by the AudioPreprocessor pipeline.

    Attributes:
        audio_tensor: PyTorch FloatTensor ready for ECAPA-TDNN model ingestion.
        audio_numpy: 1D NumPy float32 array of the preprocessed audio samples.
        sample_rate: Processed sample rate in Hz (e.g. 16000).
        original_sample_rate: Original input sample rate in Hz.
        duration_sec: Final duration in seconds.
        original_duration_sec: Input duration in seconds.
        num_channels: Original channel count before downmixing (1=mono, 2=stereo, etc.).
        num_samples: Total sample count in the processed signal.
        rms_energy: Root Mean Square energy of the processed signal.
        peak_amplitude: Maximum absolute amplitude of the processed signal.
        metrics: Complete quantitative acoustic metrics model.
        metadata: Pipeline metadata (processing timestamps, settings, source type).
        is_valid: Boolean status flag indicating successful verification and preprocessing.
    """

    audio_tensor: torch.Tensor
    audio_numpy: np.ndarray
    sample_rate: int
    original_sample_rate: int
    duration_sec: float
    original_duration_sec: float
    num_channels: int
    num_samples: int
    rms_energy: float
    peak_amplitude: float
    metrics: AudioMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True

    def save_wav(self, output_path: Union[str, Path], subtype: str = "PCM_16") -> Path:
        """Export the preprocessed audio to a standard WAV file.

        Args:
            output_path: Destination path on disk.
            subtype: SoundFile subtype format (default: 'PCM_16').

        Returns:
            Path object pointing to the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(path), self.audio_numpy, self.sample_rate, subtype=subtype)
        return path

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary summary (omitting heavy array buffers)."""
        return {
            "is_valid": self.is_valid,
            "sample_rate": self.sample_rate,
            "original_sample_rate": self.original_sample_rate,
            "duration_sec": round(self.duration_sec, 4),
            "original_duration_sec": round(self.original_duration_sec, 4),
            "num_channels": self.num_channels,
            "num_samples": self.num_samples,
            "rms_energy": float(self.rms_energy),
            "peak_amplitude": float(self.peak_amplitude),
            "rms_dbfs": self.metrics.rms_dbfs,
            "peak_dbfs": self.metrics.peak_dbfs,
            "tensor_shape": list(self.audio_tensor.shape),
            "metadata": self.metadata,
        }

    def summary(self) -> str:
        """Format a human-readable one-line summary."""
        return (
            f"PreprocessedAudio(sr={self.sample_rate}Hz, "
            f"duration={self.duration_sec:.2f}s, "
            f"samples={self.num_samples}, "
            f"peak={self.peak_amplitude:.3f}, "
            f"rms={self.rms_energy:.4f}, "
            f"tensor={tuple(self.audio_tensor.shape)})"
        )


class AudioPreprocessor:
    """Preprocesses and validates audio signals for voice verification research.

    Enforces 16 kHz mono sampling required by pretrained ECAPA-TDNN models,
    detects corrupted and silent recordings, prevents NaN/Inf numerical bugs,
    and returns structured tensors ready for inference.
    """

    def __init__(self, config: Optional[AudioPreprocessingConfig] = None) -> None:
        """Initialize the AudioPreprocessor.

        Args:
            config: Optional preprocessing configuration. If None, default settings are used.
        """
        self.config = config or AudioPreprocessingConfig()

    def load_audio(
        self,
        source: Union[str, Path, bytes, io.BytesIO],
    ) -> Tuple[np.ndarray, int, int]:
        """Load audio data from a file path, byte array, or stream.

        Args:
            source: Path to WAV file, raw WAV bytes, or a binary IO stream.

        Returns:
            Tuple of (audio_array, sample_rate, original_num_channels).

        Raises:
            FileNotFoundError: If a file path does not exist.
            EmptyAudioFileError: If file or byte buffer is empty.
            AudioFileCorruptedError: If file header or audio data is malformed.
        """
        # Validate container header if strict WAV format checking is enabled
        if self.config.strict_wav_format:
            validate_wav_header(source)

        audio: np.ndarray
        sr: int

        try:
            if isinstance(source, bytes):
                if len(source) == 0:
                    raise EmptyAudioFileError("Audio byte payload is empty.")
                with io.BytesIO(source) as buffer:
                    audio, sr = sf.read(buffer, dtype="float32", always_2d=False)
            elif isinstance(source, io.BytesIO):
                source.seek(0)
                audio, sr = sf.read(source, dtype="float32", always_2d=False)
            elif isinstance(source, (str, Path)):
                p = Path(source)
                if not p.exists():
                    raise FileNotFoundError(f"Audio file does not exist: {p}")
                if p.stat().st_size == 0:
                    raise EmptyAudioFileError(f"Audio file is zero bytes: {p}")
                audio, sr = sf.read(str(p), dtype="float32", always_2d=False)
            else:
                raise AudioValidationError(f"Unsupported source type: {type(source)}")
        except (sf.LibsndfileError, sf.SoundFileError, RuntimeError, ValueError) as err:
            raise AudioFileCorruptedError(
                f"Failed to decode audio file. Possible corruption or invalid format: {err}"
            ) from err

        if audio.size == 0:
            raise EmptyAudioFileError("Audio source decoded to 0 samples.")

        # Detect channel count
        num_channels = 1 if audio.ndim == 1 else audio.shape[1]

        return audio, sr, num_channels

    @staticmethod
    def convert_to_mono(audio: np.ndarray) -> np.ndarray:
        """Convert multi-channel (e.g. stereo) audio into single-channel mono.

        Computes the channel mean across channels.

        Args:
            audio: NumPy array of shape (N,) or (N, C) or (C, N).

        Returns:
            1D NumPy array of shape (N,) representing mono audio.
        """
        if audio.ndim == 1:
            return audio.astype(np.float32, copy=False)

        if audio.ndim == 2:
            # SoundFile returns shape (samples, channels)
            # If channels is the second dimension
            if audio.shape[1] <= 8:
                mono = np.mean(audio, axis=1, dtype=np.float32)
            else:
                # If transposed (channels, samples)
                mono = np.mean(audio, axis=0, dtype=np.float32)
            return mono.astype(np.float32, copy=False)

        raise InvalidAudioValueError(
            f"Expected 1D or 2D audio array, got ndim={audio.ndim} with shape {audio.shape}"
        )

    def resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample 1D mono audio to the target model sample rate.

        Args:
            audio: 1D mono audio numpy array.
            orig_sr: Original sample rate in Hz.
            target_sr: Target sample rate in Hz.

        Returns:
            1D mono audio numpy array sampled at target_sr.
        """
        if orig_sr == target_sr:
            return audio.astype(np.float32, copy=False)

        # High-quality polyphase / soxr resampling via librosa
        resampled = librosa.resample(
            audio,
            orig_sr=orig_sr,
            target_sr=target_sr,
            res_type="soxr_hq" if "soxr_hq" in librosa.core.resample.__doc__ or True else "kaiser_best",
        )
        return resampled.astype(np.float32, copy=False)

    def normalize(self, audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
        """Apply peak amplitude normalization to scale signal without digital clipping.

        Args:
            audio: 1D mono audio array.
            target_peak: Desired absolute peak amplitude (0.0 to 1.0].

        Returns:
            Normalized 1D mono audio array.
        """
        peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
        if peak > 1e-8:
            scale = target_peak / peak
            return (audio * scale).astype(np.float32)
        return audio.astype(np.float32, copy=False)

    def process(
        self,
        source: Union[str, Path, bytes, io.BytesIO],
        source_id: Optional[str] = None,
    ) -> AudioPreprocessingResult:
        """Execute the full audio validation and preprocessing pipeline.

        Pipeline steps:
        1. Decode audio and validate container header.
        2. Detect empty files and corruption.
        3. Validate numerical integrity (no NaN / Inf values).
        4. Validate initial recording duration.
        5. Downmix stereo/multi-channel to mono.
        6. Resample audio to required model sample rate (default: 16 kHz).
        7. Re-verify numerical and duration integrity post-resampling.
        8. Validate acoustic dynamics (silence and clipping detection).
        9. Peak normalize signal if configured.
        10. Compute comprehensive metrics (duration, RMS energy, peak amplitude, dBFS).
        11. Construct PyTorch FloatTensor ready for ECAPA-TDNN model input.

        Args:
            source: File path, byte buffer, or stream containing a WAV audio recording.
            source_id: Optional tracking identifier for metadata logging.

        Returns:
            AudioPreprocessingResult containing preprocessed tensor, numpy array, and metrics.

        Raises:
            FileNotFoundError: If file path cannot be found.
            EmptyAudioFileError: If audio is 0 bytes or 0 samples.
            AudioFileCorruptedError: If audio file is malformed or undecodable.
            AudioDurationError: If duration violates min_duration_sec or max_duration_sec.
            InvalidAudioValueError: If NaN, Inf, or unallowed clipping is detected.
            SilentAudioError: If audio is silent and detect_silence is True.
        """
        # Step 1 & 2: Load and decode audio
        raw_audio, original_sr, original_channels = self.load_audio(source)

        # Step 3: Check numerical integrity of decoded samples
        validate_audio_numeric(raw_audio)

        # Calculate original duration
        original_samples = len(raw_audio) if raw_audio.ndim == 1 else raw_audio.shape[0]
        original_duration_sec = float(original_samples / original_sr)

        # Step 4: Validate original duration boundaries
        validate_duration(
            original_duration_sec,
            min_duration_sec=self.config.min_duration_sec,
            max_duration_sec=self.config.max_duration_sec,
        )

        # Step 5: Convert stereo/multi-channel to mono
        mono_audio = self.convert_to_mono(raw_audio)

        # Step 6: Resample to target model sample rate
        target_sr = self.config.target_sample_rate
        resampled_audio = self.resample(mono_audio, orig_sr=original_sr, target_sr=target_sr)

        # Step 7: Verify post-resampling numerical integrity and duration
        validate_audio_numeric(resampled_audio)
        processed_samples = len(resampled_audio)
        processed_duration_sec = float(processed_samples / target_sr)

        validate_duration(
            processed_duration_sec,
            min_duration_sec=self.config.min_duration_sec,
            max_duration_sec=self.config.max_duration_sec,
        )

        # Step 8: Compute pre-normalization metrics and validate dynamics
        pre_metrics = compute_audio_metrics(
            resampled_audio,
            sample_rate=target_sr,
            min_rms_energy=self.config.min_rms_energy,
            max_peak_amplitude=self.config.max_peak_amplitude,
            num_channels=1,
        )
        validate_signal_content(resampled_audio, pre_metrics, self.config)

        # Step 9: Peak normalization
        if self.config.normalize_audio:
            final_audio = self.normalize(resampled_audio, target_peak=self.config.target_peak)
        else:
            final_audio = resampled_audio

        # Step 10: Compute final quantitative metrics
        final_metrics = compute_audio_metrics(
            final_audio,
            sample_rate=target_sr,
            min_rms_energy=self.config.min_rms_energy,
            max_peak_amplitude=self.config.max_peak_amplitude,
            num_channels=1,
        )

        # Step 11: Format PyTorch FloatTensor for ECAPA-TDNN
        # Standard SpeechBrain ECAPA-TDNN expects shape [batch_size, time_steps] = [1, N]
        if self.config.ensure_2d_tensor:
            audio_tensor = torch.from_numpy(final_audio).unsqueeze(0).float()
        else:
            audio_tensor = torch.from_numpy(final_audio).float()

        metadata: Dict[str, Any] = {
            "source_id": source_id,
            "source_type": type(source).__name__,
            "original_sample_rate": original_sr,
            "target_sample_rate": target_sr,
            "original_channels": original_channels,
            "normalized": self.config.normalize_audio,
            "target_peak": self.config.target_peak if self.config.normalize_audio else None,
        }

        return AudioPreprocessingResult(
            audio_tensor=audio_tensor,
            audio_numpy=final_audio,
            sample_rate=target_sr,
            original_sample_rate=original_sr,
            duration_sec=processed_duration_sec,
            original_duration_sec=original_duration_sec,
            num_channels=original_channels,
            num_samples=processed_samples,
            rms_energy=final_metrics.rms_energy,
            peak_amplitude=final_metrics.peak_amplitude,
            metrics=final_metrics,
            metadata=metadata,
            is_valid=True,
        )

