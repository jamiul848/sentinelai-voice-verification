"""Command-line interface for the SentinelAI Audio Preprocessing Module.

Supports processing WAV files from disk, running verification checks,
and executing a synthetic test signal demonstration.
"""

import argparse
import json
from pathlib import Path
import sys
import numpy as np
import soundfile as sf

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.exceptions import SentinelAudioError
from sentinelai.audio.preprocessor import AudioPreprocessor


def generate_synthetic_demo_wav(path: Path, sample_rate: int = 44100, duration_sec: float = 2.0) -> Path:
    """Generate a clean synthetic sine wave tone for pipeline demonstration.

    NOTE: This is a purely mathematical test fixture (sine wave signal), NOT human voice data.
    """
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # Generate 440 Hz standard concert pitch tone
    tone = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), tone, sample_rate, subtype="PCM_16")
    return path


def main() -> None:
    """CLI entry point for audio preprocessing."""
    parser = argparse.ArgumentParser(
        prog="sentinelai-audio-preprocessor",
        description="SentinelAI Voice Verification - Audio Preprocessing CLI",
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Path to the input WAV audio file to preprocess.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Optional destination path to save the preprocessed 16kHz mono WAV file.",
    )
    parser.add_argument(
        "--target-sr",
        type=int,
        default=16000,
        help="Target sample rate in Hz (default: 16000 for ECAPA-TDNN).",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.5,
        help="Minimum required duration in seconds (default: 0.5s).",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=60.0,
        help="Maximum allowed duration in seconds (default: 60.0s).",
    )
    parser.add_argument(
        "--demo-synthetic",
        action="store_true",
        help="Run a demonstration using a generated synthetic test tone (no dataset required).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )

    args = parser.parse_args()

    config = AudioPreprocessingConfig(
        target_sample_rate=args.target_sr,
        min_duration_sec=args.min_duration,
        max_duration_sec=args.max_duration,
    )
    preprocessor = AudioPreprocessor(config=config)

    input_path: Path
    if args.demo_synthetic:
        demo_file = Path("demo_synthetic_tone_44100hz.wav")
        print(f"[SentinelAI] Generating synthetic sine tone test file: {demo_file} (44100 Hz, stereo tone, 2.0s)...")
        # Create a stereo synthetic test signal (440Hz Left, 880Hz Right)
        sr = 44100
        dur = 2.0
        t = np.linspace(0.0, dur, int(sr * dur), endpoint=False)
        left = 0.4 * np.sin(2.0 * np.pi * 440.0 * t)
        right = 0.3 * np.sin(2.0 * np.pi * 880.0 * t)
        stereo = np.column_stack([left, right]).astype(np.float32)
        sf.write(str(demo_file), stereo, sr, subtype="PCM_16")
        input_path = demo_file
    elif args.input:
        input_path = Path(args.input)
    else:
        parser.print_help()
        sys.exit(1)

    try:
        result = preprocessor.process(input_path, source_id=str(input_path))
    except (SentinelAudioError, FileNotFoundError) as err:
        print(f"[SentinelAI ERROR] Preprocessing validation failed: {err}", file=sys.stderr)
        sys.exit(2)

    if args.output:
        saved_path = result.save_wav(args.output)
        print(f"[SentinelAI] Saved preprocessed audio to: {saved_path}")

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print("\n================ SentinelAI Audio Preprocessing Result ================")
        print(f" Status               : {'VALID' if result.is_valid else 'INVALID'}")
        print(f" Original Sample Rate : {result.original_sample_rate} Hz")
        print(f" Processed Sample Rate: {result.sample_rate} Hz (ECAPA-TDNN ready)")
        print(f" Original Channels    : {result.num_channels} -> Converted to Mono (1 channel)")
        print(f" Original Duration    : {result.original_duration_sec:.3f} s")
        print(f" Processed Duration   : {result.duration_sec:.3f} s")
        print(f" Processed Samples    : {result.num_samples}")
        print(f" RMS Energy           : {result.rms_energy:.5f} ({result.metrics.rms_dbfs:.1f} dBFS)")
        print(f" Peak Amplitude       : {result.peak_amplitude:.5f} ({result.metrics.peak_dbfs:.1f} dBFS)")
        print(f" PyTorch Tensor Shape : {list(result.audio_tensor.shape)} (dtype: {result.audio_tensor.dtype})")
        print("=======================================================================\n")

    # Clean up temporary demo file if generated
    if args.demo_synthetic and input_path.exists() and not args.output:
        input_path.unlink()


if __name__ == "__main__":
    main()

