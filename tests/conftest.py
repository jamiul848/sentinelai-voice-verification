"""Test fixtures and synthetic signal generators for audio preprocessing unit tests.

IMPORTANT NOTE:
All audio signals generated in this fixture suite are purely mathematical synthetic
signals (e.g., sine waves, deterministic tones, zero-arrays). None of these signals
represent or claim to represent human speech or real speaker data. They are designed
strictly for algorithmic unit testing of signal processing routines (resampling,
channel mixing, header parsing, duration validation, and numeric safety).
"""

import io
from pathlib import Path
from typing import Generator
import numpy as np
import pytest
import soundfile as sf


def create_synthetic_sine_tone(
    sample_rate: int = 16000,
    duration_sec: float = 2.0,
    freq_hz: float = 440.0,
    amplitude: float = 0.5,
    channels: int = 1,
) -> np.ndarray:
    """Generate a deterministic synthetic sine signal.

    NOTE: Purely synthetic mathematical test fixture. Not human speaker data.
    """
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0.0, duration_sec, num_samples, endpoint=False)
    if channels == 1:
        signal = (amplitude * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
        return signal
    else:
        # Multi-channel synthetic signal with slightly offset frequencies per channel
        channel_data = []
        for ch in range(channels):
            f = freq_hz * (1.0 + 0.5 * ch)
            channel_data.append(amplitude * np.sin(2.0 * np.pi * f * t))
        return np.column_stack(channel_data).astype(np.float32)


@pytest.fixture
def synthetic_mono_wav_16k(tmp_path: Path) -> Path:
    """Fixture providing a standard 16 kHz mono synthetic sine tone (2.0s)."""
    file_path = tmp_path / "synthetic_mono_16k.wav"
    data = create_synthetic_sine_tone(sample_rate=16000, duration_sec=2.0, freq_hz=440.0, channels=1)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_stereo_wav_44k(tmp_path: Path) -> Path:
    """Fixture providing a 44.1 kHz stereo synthetic tone (1.5s)."""
    file_path = tmp_path / "synthetic_stereo_44k.wav"
    data = create_synthetic_sine_tone(sample_rate=44100, duration_sec=1.5, freq_hz=440.0, channels=2)
    sf.write(str(file_path), data, 44100, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_low_sr_wav_8k(tmp_path: Path) -> Path:
    """Fixture providing an 8 kHz mono synthetic tone (1.0s)."""
    file_path = tmp_path / "synthetic_mono_8k.wav"
    data = create_synthetic_sine_tone(sample_rate=8000, duration_sec=1.0, freq_hz=300.0, channels=1)
    sf.write(str(file_path), data, 8000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_high_sr_wav_48k(tmp_path: Path) -> Path:
    """Fixture providing a 48 kHz mono synthetic tone (2.5s)."""
    file_path = tmp_path / "synthetic_mono_48k.wav"
    data = create_synthetic_sine_tone(sample_rate=48000, duration_sec=2.5, freq_hz=1000.0, channels=1)
    sf.write(str(file_path), data, 48000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_too_short_wav(tmp_path: Path) -> Path:
    """Fixture providing an excessively short synthetic signal (0.2s < min 0.5s)."""
    file_path = tmp_path / "synthetic_short.wav"
    data = create_synthetic_sine_tone(sample_rate=16000, duration_sec=0.2, freq_hz=440.0, channels=1)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_too_long_wav(tmp_path: Path) -> Path:
    """Fixture providing a synthetic signal exceeding max duration (35.0s > max 30.0s)."""
    file_path = tmp_path / "synthetic_long.wav"
    data = create_synthetic_sine_tone(sample_rate=16000, duration_sec=35.0, freq_hz=440.0, channels=1)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_silent_wav(tmp_path: Path) -> Path:
    """Fixture providing a completely silent signal (all zeros, 1.0s)."""
    file_path = tmp_path / "synthetic_silent.wav"
    data = np.zeros(16000, dtype=np.float32)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def empty_wav_file(tmp_path: Path) -> Path:
    """Fixture providing a 0-byte file."""
    file_path = tmp_path / "empty_file.wav"
    file_path.write_bytes(b"")
    return file_path


@pytest.fixture
def corrupted_wav_file(tmp_path: Path) -> Path:
    """Fixture providing random corrupted bytes pretending to be a WAV file."""
    file_path = tmp_path / "corrupted.wav"
    file_path.write_bytes(b"RIFF\x00\x00\x00\x00NOT_A_WAVE_HEADER_CORRUPTED_BYTES_1234567890")
    return file_path


@pytest.fixture
def truncated_wav_file(tmp_path: Path) -> Path:
    """Fixture providing a truncated file of only 4 bytes."""
    file_path = tmp_path / "truncated.wav"
    file_path.write_bytes(b"RIFF")
    return file_path

