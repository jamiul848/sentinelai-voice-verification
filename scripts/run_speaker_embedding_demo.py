"""SentinelAI Speaker Recognition - Standalone Pretrained ECAPA-TDNN Demo.

Demonstrates loading the pretrained ECAPA-TDNN model, extracting speaker embeddings,
and computing cosine similarity.
"""

import argparse
from pathlib import Path
import sys

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import soundfile as sf
import torch

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.model import ECAPAModelLoader
from sentinelai.speaker.similarity import compute_cosine_similarity


def generate_synthetic_tone(path: Path, freq_hz: float = 440.0, sample_rate: int = 16000, duration_sec: float = 2.0) -> Path:
    """Generate a deterministic synthetic sine tone test fixture.

    NOTE: Purely a mathematical test fixture for pipeline execution, NOT human speech.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    signal = (0.5 * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
    sf.write(str(path), signal, sample_rate, subtype="PCM_16")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SentinelAI Speaker Recognition & ECAPA-TDNN Demonstration",
    )
    parser.add_argument(
        "--audio1",
        type=str,
        help="Path to first audio WAV recording.",
    )
    parser.add_argument(
        "--audio2",
        type=str,
        help="Path to second audio WAV recording.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Compute device for inference (default: 'auto').",
    )
    args = parser.parse_args()

    print("=" * 72)
    print(" SentinelAI Voice Verification - Pretrained ECAPA-TDNN Demonstration")
    print("=" * 72)

    # 1. Configure speaker module
    config = SpeakerConfig(device=args.device)
    print(f"\n1. Initializing Model Configuration:")
    print(f"   - Model Source       : {config.model_source}")
    print(f"   - Requested Device   : {config.device}")
    print(f"   - Resolved Device    : {config.resolved_device.upper()} (CUDA Available: {torch.cuda.is_available()})")
    print(f"   - Cache Directory    : {config.savedir.resolve()}")
    print(f"   - Embedding L2 Norm  : {config.normalize_embeddings}")

    # 2. Initialize Model Loader and Extractor
    loader = ECAPAModelLoader(config=config)
    extractor = SpeakerEmbeddingExtractor(config=config, loader=loader)

    path1: Path
    path2: Path
    is_synthetic = False

    demo_dir = Path("outputs/speaker_demo")
    demo_dir.mkdir(parents=True, exist_ok=True)

    if args.audio1 and args.audio2:
        path1 = Path(args.audio1)
        path2 = Path(args.audio2)
        print(f"\n2. Using user-provided audio recordings:")
        print(f"   - Audio 1: {path1}")
        print(f"   - Audio 2: {path2}")
    else:
        is_synthetic = True
        path1 = demo_dir / "synthetic_test_signal_a_440hz.wav"
        path2 = demo_dir / "synthetic_test_signal_b_880hz.wav"
        print(f"\n2. No audio paths provided. Generating deterministic synthetic test signals:")
        print(f"   - Signal A (440 Hz sine tone, 2.0s) -> {path1.name}")
        print(f"   - Signal B (880 Hz sine tone, 2.0s) -> {path2.name}")
        print("   [Notice] Synthetic signals verify code execution, shapes, and normalization.")
        print("   They do not represent real human voice biometric data.")
        generate_synthetic_tone(path1, freq_hz=440.0)
        generate_synthetic_tone(path2, freq_hz=880.0)

    # 3. Extract Embeddings
    print("\n3. Extracting Speaker Embeddings with Pretrained ECAPA-TDNN...")
    result_a = extractor.extract(path1, source_id="input-a")
    print(f"   -> Extracted Embedding A:")
    print(f"      - Dimension        : {result_a.dimension} (dynamically verified)")
    print(f"      - Device Used      : {result_a.device}")
    print(f"      - L2 Norm          : {np.linalg.norm(result_a.embedding):.4f}")
    print(f"      - Duration         : {result_a.audio_duration_sec:.2f} s")
    print(f"      - Timestamp (UTC)  : {result_a.extraction_timestamp}")

    result_b = extractor.extract(path2, source_id="input-b")
    print(f"   -> Extracted Embedding B:")
    print(f"      - Dimension        : {result_b.dimension} (dynamically verified)")
    print(f"      - Device Used      : {result_b.device}")
    print(f"      - L2 Norm          : {np.linalg.norm(result_b.embedding):.4f}")
    print(f"      - Duration         : {result_b.audio_duration_sec:.2f} s")
    print(f"      - Timestamp (UTC)  : {result_b.extraction_timestamp}")

    # 4. Calculate Cosine Similarities
    print("\n4. Calculating Directional Cosine Similarity:")
    self_sim_a = compute_cosine_similarity(result_a, result_a)
    print(f"   - Self-Similarity (A vs A) : {self_sim_a:.6f} (Expected: 1.000000)")

    cross_sim = compute_cosine_similarity(result_a, result_b)
    print(f"   - Cross-Similarity (A vs B): {cross_sim:.6f}")

    print("\n" + "=" * 72)
    print(" Interpretation & Architectural Boundaries:")
    print(" - Cosine similarity measures geometric alignment in the 192-dim space.")
    print(" - Higher scores indicate greater acoustic voiceprint similarity.")
    print(" - Cosine similarity alone does NOT prove identity without threshold calibration,")
    print("   multi-utterance enrollment averaging, and anti-spoofing verification (Phase 3).")
    print("=" * 72 + "\n")

    # Clean up synthetic demo files if generated
    if is_synthetic:
        if path1.exists():
            path1.unlink()
        if path2.exists():
            path2.unlink()


if __name__ == "__main__":
    main()

