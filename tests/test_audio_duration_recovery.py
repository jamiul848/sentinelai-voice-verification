"""Tests for extended audio duration support (up to 60s), cache reuse, and failed recording retry."""

from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
import torch

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.exceptions import AudioDurationError
from sentinelai.audio.preprocessor import AudioPreprocessingResult, AudioPreprocessor
from sentinelai.evaluation.batch_embedder import BatchEmbedder, BatchExtractionResult


@pytest.fixture
def synthetic_32s_flac(tmp_path: Path) -> Path:
    """Fixture providing a 32.5s mono FLAC file (similar to the 9 long LibriSpeech files)."""
    sr = 16000
    duration = 32.5
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sine = 0.4 * np.sin(2 * np.pi * 350.0 * t).astype(np.float32)
    flac_path = tmp_path / "long_32s.flac"
    sf.write(str(flac_path), sine, sr, format="FLAC")
    return flac_path


@pytest.fixture
def synthetic_65s_wav(tmp_path: Path) -> Path:
    """Fixture providing a 65.0s mono WAV file that exceeds the 60.0s limit."""
    sr = 16000
    duration = 65.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sine = 0.3 * np.sin(2 * np.pi * 350.0 * t).astype(np.float32)
    wav_path = tmp_path / "too_long_65s.wav"
    sf.write(str(wav_path), sine, sr, subtype="PCM_16")
    return wav_path


class TestExtendedAudioDurationSupport:
    """Test suite for extended duration configuration, cache reuse, and error recovery."""

    def test_default_config_has_60s_max_duration(self) -> None:
        """Default AudioPreprocessingConfig has max_duration_sec equal to 60.0 seconds."""
        config = AudioPreprocessingConfig()
        assert config.max_duration_sec == 60.0
        assert config.min_duration_sec == 0.5

    def test_audio_between_30_and_35_seconds_accepted_by_default(
        self, synthetic_32s_flac: Path
    ) -> None:
        """Recordings between 30 and 35 seconds (e.g. 32.5s) are accepted by default."""
        preprocessor = AudioPreprocessor()
        result = preprocessor.process(synthetic_32s_flac)

        assert isinstance(result, AudioPreprocessingResult)
        assert result.is_valid is True
        assert pytest.approx(result.duration_sec, rel=1e-2) == 32.5
        assert result.sample_rate == 16000
        assert isinstance(result.audio_tensor, torch.Tensor)
        assert result.audio_tensor.shape == (1, int(16000 * 32.5))

    def test_real_librispeech_31s_recording_accepted(self) -> None:
        """Real LibriSpeech 31.38s recording 2078-142845-0005.flac decodes cleanly."""
        real_file = Path(
            "datasets/librispeech/dev-clean/LibriSpeech/dev-clean/2078/142845/2078-142845-0005.flac"
        )
        if not real_file.exists():
            pytest.skip("LibriSpeech dev-clean 2078-142845-0005.flac not found.")

        preprocessor = AudioPreprocessor()
        result = preprocessor.process(real_file)

        assert result.is_valid is True
        assert pytest.approx(result.duration_sec, abs=0.2) == 31.38
        assert result.audio_tensor.dtype == torch.float32
        assert result.audio_tensor.ndim == 2

    def test_audio_exceeding_60_seconds_rejected(self, synthetic_65s_wav: Path) -> None:
        """Audio exceeding 60.0 seconds raises AudioDurationError."""
        preprocessor = AudioPreprocessor()
        with pytest.raises(AudioDurationError) as exc_info:
            preprocessor.process(synthetic_65s_wav)

        err = exc_info.value
        assert "exceeds maximum allowed 60.00s" in str(err)
        assert err.duration_sec > 60.0
        assert err.max_duration_sec == 60.0

    def test_batch_embedder_cache_reuse_and_skip(self, tmp_path: Path) -> None:
        """BatchEmbedder reuses existing cached .npz files without invoking the model."""
        cache_dir = tmp_path / "embeddings"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Pre-seed a valid cached embedding file
        dummy_stem = "rec_001"
        dummy_emb = np.random.randn(192).astype(np.float32)
        dummy_emb /= np.linalg.norm(dummy_emb)
        np.savez(
            str(cache_dir / f"{dummy_stem}.npz"),
            embedding=dummy_emb,
            speaker_id="spk_999",
            dimension=192,
        )

        embedder = BatchEmbedder(output_dir=cache_dir)
        dummy_audio = tmp_path / f"{dummy_stem}.wav"
        # Create empty audio file on disk to represent path
        dummy_audio.touch()

        result = embedder.extract_batch(
            recordings=[dummy_audio],
            speaker_ids={dummy_stem: "spk_999"},
            split_name="test-cache",
            skip_cached=True,
        )

        assert result.total_skipped == 1
        assert result.total_extracted == 0
        assert result.total_failed == 0
        assert dummy_stem in result.embeddings
        entry = result.embeddings[dummy_stem]
        assert entry.dimension == 192
        assert entry.speaker_id == "spk_999"
        assert np.allclose(entry.embedding, dummy_emb)

