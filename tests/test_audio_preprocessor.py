"""Unit tests for the SentinelAI Audio Preprocessing Module.

NOTE ON TEST SIGNALS:
All test audio signals used in this module are purely synthetic mathematical fixtures
(e.g., sine tones, zero arrays, procedural white noise) generated dynamically for
algorithmic validation. No real speaker data or fabricated human speech is used.
"""

import io
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
import torch

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.exceptions import (
    AudioDurationError,
    AudioFileCorruptedError,
    EmptyAudioFileError,
    InvalidAudioValueError,
    SilentAudioError,
)
from sentinelai.audio.metrics import compute_audio_metrics
from sentinelai.audio.preprocessor import AudioPreprocessingResult, AudioPreprocessor
from sentinelai.audio.validator import validate_audio_numeric, validate_wav_header


class TestAudioPreprocessingPipeline:
    """Test suite covering the complete audio preprocessing pipeline."""

    def test_preprocess_standard_mono_wav(self, synthetic_mono_wav_16k: Path) -> None:
        """Requirement 1, 7, 9: Standard 16kHz mono WAV is processed with structured output."""
        preprocessor = AudioPreprocessor()
        result = preprocessor.process(synthetic_mono_wav_16k)

        assert isinstance(result, AudioPreprocessingResult)
        assert result.is_valid is True
        assert result.sample_rate == 16000
        assert result.original_sample_rate == 16000
        assert result.num_channels == 1
        assert pytest.approx(result.duration_sec, rel=1e-2) == 2.0
        assert pytest.approx(result.original_duration_sec, rel=1e-2) == 2.0

        # PyTorch Tensor properties for SpeechBrain ECAPA-TDNN ingestion
        assert isinstance(result.audio_tensor, torch.Tensor)
        assert result.audio_tensor.dtype == torch.float32
        assert result.audio_tensor.ndim == 2
        assert result.audio_tensor.shape == (1, result.num_samples)

        # NumPy array properties
        assert isinstance(result.audio_numpy, np.ndarray)
        assert result.audio_numpy.dtype == np.float32
        assert result.audio_numpy.ndim == 1
        assert len(result.audio_numpy) == result.num_samples

        # Metrics verification
        assert result.rms_energy > 0.0
        assert result.peak_amplitude > 0.0
        assert result.peak_amplitude <= 1.0
        assert result.metrics.is_silent is False

    def test_stereo_to_mono_conversion(self, synthetic_stereo_wav_44k: Path) -> None:
        """Requirement 2: Stereo 2-channel audio is downmixed to mono by averaging channels."""
        # Read the raw stereo file directly to compute expected mono downmix
        raw_stereo, sr = sf.read(str(synthetic_stereo_wav_44k), dtype="float32")
        expected_mono_mean = np.mean(raw_stereo, axis=1, dtype=np.float32)

        preprocessor = AudioPreprocessor(config=AudioPreprocessingConfig(normalize_audio=False))
        # Test direct convert_to_mono method
        direct_mono = AudioPreprocessor.convert_to_mono(raw_stereo)
        assert direct_mono.ndim == 1
        np.testing.assert_allclose(direct_mono, expected_mono_mean, atol=1e-6)

        # Test full pipeline stereo handling
        result = preprocessor.process(synthetic_stereo_wav_44k)
        assert result.num_channels == 2
        assert result.audio_numpy.ndim == 1
        assert result.audio_tensor.shape[0] == 1

    def test_resampling_from_various_sample_rates(
        self,
        synthetic_low_sr_wav_8k: Path,
        synthetic_high_sr_wav_48k: Path,
        synthetic_stereo_wav_44k: Path,
    ) -> None:
        """Requirement 3: Audio at 8kHz, 44.1kHz, and 48kHz is resampled to 16kHz."""
        preprocessor = AudioPreprocessor()

        # From 8000 Hz to 16000 Hz
        res_8k = preprocessor.process(synthetic_low_sr_wav_8k)
        assert res_8k.original_sample_rate == 8000
        assert res_8k.sample_rate == 16000
        assert pytest.approx(res_8k.duration_sec, rel=1e-2) == 1.0

        # From 48000 Hz to 16000 Hz
        res_48k = preprocessor.process(synthetic_high_sr_wav_48k)
        assert res_48k.original_sample_rate == 48000
        assert res_48k.sample_rate == 16000
        assert pytest.approx(res_48k.duration_sec, rel=1e-2) == 2.5

        # From 44100 Hz to 16000 Hz
        res_44k = preprocessor.process(synthetic_stereo_wav_44k)
        assert res_44k.original_sample_rate == 44100
        assert res_44k.sample_rate == 16000
        assert pytest.approx(res_44k.duration_sec, rel=1e-2) == 1.5

    def test_duration_validation_too_short(self, synthetic_too_short_wav: Path) -> None:
        """Requirement 4: Audio shorter than min_duration_sec is detected and rejected."""
        preprocessor = AudioPreprocessor(config=AudioPreprocessingConfig(min_duration_sec=0.5))
        with pytest.raises(AudioDurationError) as exc_info:
            preprocessor.process(synthetic_too_short_wav)

        err = exc_info.value
        assert "shorter than minimum allowed" in str(err)
        assert err.duration_sec < 0.5
        assert err.min_duration_sec == 0.5

    def test_duration_validation_too_long(self, synthetic_too_long_wav: Path) -> None:
        """Requirement 4: Audio longer than max_duration_sec is detected and rejected."""
        preprocessor = AudioPreprocessor(config=AudioPreprocessingConfig(max_duration_sec=30.0))
        with pytest.raises(AudioDurationError) as exc_info:
            preprocessor.process(synthetic_too_long_wav)

        err = exc_info.value
        assert "exceeds maximum allowed" in str(err)
        assert err.duration_sec > 30.0
        assert err.max_duration_sec == 30.0

    def test_detect_empty_file(self, empty_wav_file: Path) -> None:
        """Requirement 5: 0-byte file is detected and rejected with EmptyAudioFileError."""
        preprocessor = AudioPreprocessor()
        with pytest.raises(EmptyAudioFileError):
            preprocessor.process(empty_wav_file)

    def test_detect_empty_bytes(self) -> None:
        """Requirement 5: Empty byte array is rejected with EmptyAudioFileError."""
        preprocessor = AudioPreprocessor()
        with pytest.raises(EmptyAudioFileError):
            preprocessor.process(b"")

    def test_detect_corrupted_file(self, corrupted_wav_file: Path) -> None:
        """Requirement 5: Corrupted header is detected and rejected with AudioFileCorruptedError."""
        preprocessor = AudioPreprocessor()
        with pytest.raises(AudioFileCorruptedError):
            preprocessor.process(corrupted_wav_file)

    def test_detect_truncated_file(self, truncated_wav_file: Path) -> None:
        """Requirement 5: Truncated file (< 12 bytes) is rejected with AudioFileCorruptedError."""
        preprocessor = AudioPreprocessor()
        with pytest.raises(AudioFileCorruptedError):
            preprocessor.process(truncated_wav_file)

    def test_detect_nonexistent_file(self, tmp_path: Path) -> None:
        """Requirement 5: Non-existent file path raises FileNotFoundError."""
        preprocessor = AudioPreprocessor()
        missing_file = tmp_path / "does_not_exist.wav"
        with pytest.raises(FileNotFoundError):
            preprocessor.process(missing_file)

    def test_detect_nan_numerical_values(self) -> None:
        """Requirement 6: Audio containing NaN values is detected and rejected."""
        audio_with_nan = np.array([0.1, 0.2, np.nan, 0.4], dtype=np.float32)
        with pytest.raises(InvalidAudioValueError) as exc_info:
            validate_audio_numeric(audio_with_nan)
        assert "NaN detected" in str(exc_info.value)

    def test_detect_inf_numerical_values(self) -> None:
        """Requirement 6: Audio containing Inf values is detected and rejected."""
        audio_with_inf = np.array([0.1, 0.2, np.inf, 0.4], dtype=np.float32)
        with pytest.raises(InvalidAudioValueError) as exc_info:
            validate_audio_numeric(audio_with_inf)
        assert "Infinity detected" in str(exc_info.value)

    def test_detect_silent_audio(self, synthetic_silent_wav: Path) -> None:
        """Requirement 6, 7: All-zero silent audio is rejected when silence detection is enabled."""
        preprocessor = AudioPreprocessor(config=AudioPreprocessingConfig(detect_silence=True))
        with pytest.raises(SilentAudioError) as exc_info:
            preprocessor.process(synthetic_silent_wav)
        assert "completely silent" in str(exc_info.value)

    def test_allow_silence_when_configured(self, synthetic_silent_wav: Path) -> None:
        """Requirement 8: Silence check can be disabled via configuration."""
        preprocessor = AudioPreprocessor(
            config=AudioPreprocessingConfig(detect_silence=False, normalize_audio=False)
        )
        result = preprocessor.process(synthetic_silent_wav)
        assert result.is_valid is True
        assert result.rms_energy == 0.0
        assert result.metrics.is_silent is True

    def test_metrics_calculation(self) -> None:
        """Requirement 7: Verify analytical formulas for RMS, peak amplitude, and dBFS."""
        sr = 16000
        # A DC offset signal of constant 0.5 has RMS = 0.5, Peak = 0.5
        const_signal = np.full(16000, 0.5, dtype=np.float32)
        metrics = compute_audio_metrics(const_signal, sample_rate=sr)

        assert metrics.sample_rate == sr
        assert metrics.num_samples == 16000
        assert metrics.duration_sec == 1.0
        assert pytest.approx(metrics.rms_energy, rel=1e-4) == 0.5
        assert pytest.approx(metrics.peak_amplitude, rel=1e-4) == 0.5
        # 20 * log10(0.5) ~ -6.02 dBFS
        assert pytest.approx(metrics.rms_dbfs, abs=0.1) == -6.02
        assert pytest.approx(metrics.peak_dbfs, abs=0.1) == -6.02
        assert metrics.is_silent is False
        assert metrics.is_clipped is False

    def test_peak_normalization(self, synthetic_mono_wav_16k: Path) -> None:
        """Requirement 8: Peak normalization scales amplitude to configured target_peak."""
        target_peak = 0.90
        preprocessor = AudioPreprocessor(
            config=AudioPreprocessingConfig(normalize_audio=True, target_peak=target_peak)
        )
        result = preprocessor.process(synthetic_mono_wav_16k)
        assert pytest.approx(result.peak_amplitude, rel=1e-3) == target_peak
        assert float(np.max(np.abs(result.audio_numpy))) <= 1.0

    def test_configurable_settings_validation(self) -> None:
        """Requirement 8: Invalid configuration combinations are caught at initialization."""
        # min_duration >= max_duration must raise ValidationError
        with pytest.raises(Exception):
            AudioPreprocessingConfig(min_duration_sec=10.0, max_duration_sec=5.0)

        with pytest.raises(Exception):
            AudioPreprocessingConfig(target_sample_rate=-1)

    def test_accept_raw_bytes_and_bytesio(self, synthetic_mono_wav_16k: Path) -> None:
        """Requirement 1: Preprocessor accepts raw bytes and io.BytesIO streams."""
        preprocessor = AudioPreprocessor()
        raw_bytes = synthetic_mono_wav_16k.read_bytes()

        # Test from raw bytes
        result_bytes = preprocessor.process(raw_bytes, source_id="bytes-test")
        assert result_bytes.is_valid is True
        assert result_bytes.metadata["source_type"] == "bytes"

        # Test from BytesIO stream
        stream = io.BytesIO(raw_bytes)
        result_stream = preprocessor.process(stream, source_id="stream-test")
        assert result_stream.is_valid is True
        assert result_stream.metadata["source_type"] == "BytesIO"

    def test_save_preprocessed_wav(self, synthetic_mono_wav_16k: Path, tmp_path: Path) -> None:
        """Requirement 9: Save preprocessed audio to disk and verify decodability."""
        preprocessor = AudioPreprocessor()
        result = preprocessor.process(synthetic_mono_wav_16k)

        out_path = tmp_path / "processed_output.wav"
        saved_file = result.save_wav(out_path)

        assert saved_file.exists()
        assert saved_file.stat().st_size > 0

        # Verify saved file is 16kHz mono PCM
        loaded, sr = sf.read(str(saved_file))
        assert sr == 16000
        assert loaded.ndim == 1
        assert len(loaded) == result.num_samples

    def test_result_to_dict_and_summary(self, synthetic_mono_wav_16k: Path) -> None:
        """Requirement 9: Result serialization and human-readable summary."""
        preprocessor = AudioPreprocessor()
        result = preprocessor.process(synthetic_mono_wav_16k)

        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["is_valid"] is True
        assert d["sample_rate"] == 16000
        assert "rms_energy" in d
        assert "peak_amplitude" in d

        s = result.summary()
        assert "16000Hz" in s
        assert "duration=" in s

