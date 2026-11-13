"""Unit tests for FLAC container decoding, format validation, and preprocessing pipeline."""

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
from sentinelai.audio.preprocessor import AudioPreprocessingResult, AudioPreprocessor
from sentinelai.audio.validator import validate_audio_header


@pytest.fixture
def synthetic_mono_flac_16k(tmp_path: Path) -> Path:
    """Fixture providing a valid 16kHz mono FLAC file with a 440Hz sine wave."""
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sine = 0.5 * np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    flac_path = tmp_path / "test_sine_16k.flac"
    sf.write(str(flac_path), sine, sr, format="FLAC")
    return flac_path


@pytest.fixture
def synthetic_stereo_flac_44k(tmp_path: Path) -> Path:
    """Fixture providing a 44.1kHz stereo FLAC file."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    ch1 = 0.4 * np.sin(2 * np.pi * 300.0 * t).astype(np.float32)
    ch2 = 0.4 * np.sin(2 * np.pi * 600.0 * t).astype(np.float32)
    stereo = np.column_stack([ch1, ch2])
    flac_path = tmp_path / "test_stereo_44k.flac"
    sf.write(str(flac_path), stereo, sr, format="FLAC")
    return flac_path


@pytest.fixture
def corrupted_flac_file(tmp_path: Path) -> Path:
    """Fixture providing corrupted FLAC bytes."""
    flac_path = tmp_path / "corrupted.flac"
    flac_path.write_bytes(b"fLaC\x00\x00\x00\x22CORRUPTED_METADATA_STREAM_GARBAGE_1234567890")
    return flac_path


class TestFLACAudioPreprocessing:
    """Test suite for FLAC container decoding, validation, and pipeline integration."""

    def test_validate_audio_header_detects_flac(self, synthetic_mono_flac_16k: Path) -> None:
        """Header validation correctly identifies 'fLaC' stream marker as FLAC format."""
        detected = validate_audio_header(synthetic_mono_flac_16k)
        assert detected == "FLAC"

    def test_validate_audio_header_detects_wav(self, synthetic_mono_wav_16k: Path) -> None:
        """Header validation continues to identify standard WAV files as 'WAV'."""
        detected = validate_audio_header(synthetic_mono_wav_16k)
        assert detected == "WAV"

    def test_preprocess_standard_mono_flac(self, synthetic_mono_flac_16k: Path) -> None:
        """Standard 16kHz mono FLAC is processed into a valid PyTorch FloatTensor [1, N]."""
        preprocessor = AudioPreprocessor()
        result = preprocessor.process(synthetic_mono_flac_16k)

        assert isinstance(result, AudioPreprocessingResult)
        assert result.is_valid is True
        assert result.sample_rate == 16000
        assert result.original_sample_rate == 16000
        assert result.num_channels == 1
        assert pytest.approx(result.duration_sec, rel=1e-2) == 2.0

        # PyTorch Tensor properties for ECAPA-TDNN ingestion
        assert isinstance(result.audio_tensor, torch.Tensor)
        assert result.audio_tensor.dtype == torch.float32
        assert result.audio_tensor.ndim == 2
        assert result.audio_tensor.shape == (1, result.num_samples)

        # Signal properties
        assert result.rms_energy > 0.0
        assert result.peak_amplitude > 0.0
        assert result.peak_amplitude <= 1.0

    def test_stereo_flac_downmixing_and_resampling(self, synthetic_stereo_flac_44k: Path) -> None:
        """Stereo 44.1kHz FLAC is downmixed to mono and resampled to 16kHz."""
        preprocessor = AudioPreprocessor()
        result = preprocessor.process(synthetic_stereo_flac_44k)

        assert result.is_valid is True
        assert result.num_channels == 2
        assert result.sample_rate == 16000
        assert result.original_sample_rate == 44100
        assert result.audio_tensor.shape == (1, result.num_samples)
        assert result.audio_numpy.ndim == 1

    def test_corrupted_flac_rejected(self, corrupted_flac_file: Path) -> None:
        """Corrupted FLAC stream is rejected with AudioFileCorruptedError."""
        preprocessor = AudioPreprocessor()
        with pytest.raises(AudioFileCorruptedError):
            preprocessor.process(corrupted_flac_file)

    def test_real_librispeech_flac_decoding(self) -> None:
        """Actual LibriSpeech FLAC audio file from dataset directory is decoded cleanly."""
        sample_flac = Path("datasets/librispeech/test-clean/LibriSpeech/test-clean/908/31957/908-31957-0024.flac")
        if not sample_flac.exists():
            pytest.skip("LibriSpeech test-clean sample recording not found.")

        preprocessor = AudioPreprocessor()
        result = preprocessor.process(sample_flac)

        assert result.is_valid is True
        assert result.sample_rate == 16000
        assert result.audio_tensor.dtype == torch.float32
        assert result.audio_tensor.ndim == 2
        assert result.duration_sec > 1.0
        assert np.isfinite(result.audio_numpy).all()

    def test_flac_bytes_and_stream_input(self, synthetic_mono_flac_16k: Path) -> None:
        """FLAC audio is accepted as raw bytes and io.BytesIO stream."""
        raw_bytes = synthetic_mono_flac_16k.read_bytes()
        preprocessor = AudioPreprocessor()

        # From bytes
        res_bytes = preprocessor.process(raw_bytes, source_id="flac-bytes")
        assert res_bytes.is_valid is True
        assert res_bytes.metadata["source_type"] == "bytes"

        # From stream
        stream = io.BytesIO(raw_bytes)
        res_stream = preprocessor.process(stream, source_id="flac-stream")
        assert res_stream.is_valid is True
        assert res_stream.metadata["source_type"] == "BytesIO"

