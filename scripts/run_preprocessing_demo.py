"""Standalone execution script for the SentinelAI Audio Preprocessing module.

Runs preprocessing on an input WAV file or generates a synthetic test signal
to verify the audio pipeline end-to-end.
"""

from pathlib import Path
import sys

# Ensure repository root is in Python path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import soundfile as sf

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.preprocessor import AudioPreprocessor


def main() -> None:
    print("=" * 70)
    print(" SentinelAI Voice Verification - Audio Preprocessing Pipeline Demo")
    print("=" * 70)

    # Output directory for demonstration artifacts
    output_dir = Path("outputs/preprocessing_demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate a multi-channel, non-16kHz synthetic test signal (44100 Hz stereo)
    # NOTE: Mathematical test fixture for verifying algorithmic conversions only.
    synthetic_test_wav = output_dir / "synthetic_input_44100hz_stereo.wav"
    sample_rate = 44100
    duration_sec = 2.5
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)

    # Left channel: 440 Hz tone, Right channel: 880 Hz harmonic
    ch_left = 0.45 * np.sin(2.0 * np.pi * 440.0 * t)
    ch_right = 0.35 * np.sin(2.0 * np.pi * 880.0 * t)
    stereo_signal = np.column_stack([ch_left, ch_right]).astype(np.float32)

    print(f"1. Generating synthetic test signal : {synthetic_test_wav.name}")
    print(f"   - Channels     : 2 (Stereo)")
    print(f"   - Sample Rate  : {sample_rate} Hz")
    print(f"   - Duration     : {duration_sec} s")
    sf.write(str(synthetic_test_wav), stereo_signal, sample_rate, subtype="PCM_16")

    # Initialize AudioPreprocessor with standard ECAPA-TDNN settings
    config = AudioPreprocessingConfig(
        target_sample_rate=16000,
        min_duration_sec=0.5,
        max_duration_sec=30.0,
        normalize_audio=True,
        target_peak=0.95,
    )
    preprocessor = AudioPreprocessor(config=config)

    print("\n2. Executing AudioPreprocessor...")
    result = preprocessor.process(synthetic_test_wav, source_id="demo-test-01")

    # Save the processed 16kHz mono audio
    processed_wav = output_dir / "processed_output_16000hz_mono.wav"
    saved_path = result.save_wav(processed_wav)

    print("\n3. Preprocessing Successful! Results:")
    print(f"   - Validated Status       : {result.is_valid}")
    print(f"   - Input Sample Rate      : {result.original_sample_rate} Hz -> Processed: {result.sample_rate} Hz")
    print(f"   - Input Channels         : {result.num_channels} -> Processed: 1 (Mono)")
    print(f"   - Duration               : {result.duration_sec:.3f} s ({result.num_samples} samples)")
    print(f"   - RMS Energy             : {result.rms_energy:.5f} ({result.metrics.rms_dbfs:.2f} dBFS)")
    print(f"   - Peak Amplitude         : {result.peak_amplitude:.5f} ({result.metrics.peak_dbfs:.2f} dBFS)")
    print(f"   - PyTorch Tensor Shape   : {list(result.audio_tensor.shape)} (dtype: {result.audio_tensor.dtype})")
    print(f"   - Saved Cleaned WAV      : {saved_path}")

    print("\n" + "=" * 70)
    print(" Pipeline verification complete. Ready for ECAPA-TDNN speaker embedding.")
    print("=" * 70)


if __name__ == "__main__":
    main()
