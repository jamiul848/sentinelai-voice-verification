"""SentinelAI Voice Enrollment & Speaker Profile Management Demo.

Demonstrates the multi-utterance enrollment pipeline, reference embedding aggregation,
profile storage, status inspection, and profile revocation.
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

from sentinelai.audio.preprocessor import AudioPreprocessor
from sentinelai.enrollment.config import EnrollmentConfig
from sentinelai.enrollment.schemas import UserEnrollmentStatus
from sentinelai.enrollment.service import EnrollmentService
from sentinelai.enrollment.storage import LocalFileProfileStorage
from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.model import ECAPAModelLoader


def generate_synthetic_recording(path: Path, freq_hz: float, duration_sec: float = 2.0, sample_rate: int = 16000) -> Path:
    """Generate a deterministic synthetic tone for functional software execution testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    signal = (0.5 * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
    sf.write(str(path), signal, sample_rate, subtype="PCM_16")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SentinelAI Phase 3: Voice Enrollment & Profile Management Demonstration",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="demo_user_01",
        help="Unique user identifier for enrollment.",
    )
    parser.add_argument(
        "--recordings",
        nargs="+",
        help="Optional paths to at least 3 consented human voice WAV recordings.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device for inference (default: 'auto').",
    )
    args = parser.parse_args()

    print("=" * 76)
    print(" SentinelAI: Phase 3 - Voice Enrollment & Profile Management Demo")
    print("=" * 76)

    demo_dir = Path("outputs/enrollment_demo")
    demo_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize Pipeline Modules
    print("\n1. Initializing Preprocessing, Model, Storage, and Enrollment Services...")
    speaker_config = SpeakerConfig(device=args.device)
    model_loader = ECAPAModelLoader(config=speaker_config)
    preprocessor = AudioPreprocessor()
    extractor = SpeakerEmbeddingExtractor(config=speaker_config, loader=model_loader, preprocessor=preprocessor)

    storage_dir = demo_dir / "profiles"
    enrollment_config = EnrollmentConfig(
        min_recordings=3,
        max_recordings=10,
        storage_dir=storage_dir,
        require_explicit_consent=True,
        purge_biometrics_on_revocation=True,
    )
    storage = LocalFileProfileStorage(storage_dir=storage_dir)
    service = EnrollmentService(
        config=enrollment_config,
        storage=storage,
        preprocessor=preprocessor,
        extractor=extractor,
    )

    print(f"   - Model Source        : {speaker_config.model_source}")
    print(f"   - Active Device       : {speaker_config.resolved_device.upper()} (CUDA: {torch.cuda.is_available()})")
    print(f"   - Min/Max Recordings  : {enrollment_config.min_recordings} / {enrollment_config.max_recordings}")
    print(f"   - Profile Storage Dir : {storage_dir.resolve()}")

    # 2. Collect or Generate Voice Recordings
    audio_paths: list[Path] = []
    is_synthetic = False

    if args.recordings and len(args.recordings) >= 3:
        audio_paths = [Path(p) for p in args.recordings]
        print(f"\n2. Using {len(audio_paths)} user-provided consented voice recordings:")
        for p in audio_paths:
            print(f"   - {p}")
    else:
        is_synthetic = True
        print("\n2. No recordings provided. Generating 3 deterministic synthetic test signals:")
        # Mandatory warning per project specifications
        print("\n   ************************************************************************")
        print("   WARNING:")
        print("   Synthetic signals are not human speaker recordings and cannot establish")
        print("   speaker recognition performance.")
        print("   ************************************************************************\n")

        freqs = [380.0, 440.0, 500.0]
        for idx, freq in enumerate(freqs, start=1):
            p = demo_dir / f"synthetic_sample_{idx}_{int(freq)}hz.wav"
            generate_synthetic_recording(p, freq_hz=freq, duration_sec=2.0)
            audio_paths.append(p)
            print(f"   - Generated synthetic test utterance {idx}: {p.name} ({freq} Hz)")

    # 3. Check Initial Enrollment Status
    user_id = args.user_id
    initial_status = service.get_enrollment_status(user_id)
    print(f"\n3. Pre-Enrollment Status for User '{user_id}': {initial_status.status.value}")

    # 4. Enroll User with Explicit Consent
    print(f"\n4. Executing Voice Enrollment for User '{user_id}' with Consent=True...")
    enroll_result = service.enroll(
        user_id=user_id,
        audio_sources=audio_paths,
        consent=True,
        metadata={"client": "CLI_Demo", "hardware": "PC"},
    )
    profile_id = enroll_result.profile_id
    print(f"   -> Enrollment Successful!")
    print(f"      - Profile ID         : {profile_id}")
    print(f"      - Enrolled Samples   : {enroll_result.sample_count}")
    print(f"      - Embedding Dimension: {enroll_result.embedding_dimension}")
    print(f"      - Timestamp (UTC)    : {enroll_result.created_at}")

    # 5. Check Active Enrollment Status
    active_status = service.get_enrollment_status(user_id)
    print(f"\n5. Post-Enrollment Status for User '{user_id}': {active_status.status.value}")
    assert active_status.status == UserEnrollmentStatus.ACTIVE

    # 6. Retrieve Public Profile Metadata
    print(f"\n6. Retrieving Enrolled Profile Metadata (Public View):")
    public_prof = service.get_public_profile(profile_id)
    print(f"   - Status             : {public_prof.status.value}")
    print(f"   - Enrolled Samples   : {public_prof.enrollment_sample_count}")
    print(f"   - Dimension          : {public_prof.embedding_dimension}")
    print(f"   - Model Used         : {public_prof.model_name}")
    print(f"   - Consent Confirmed  : {public_prof.consent_status}")
    print("   - Biometric Security : Embedding vectors strictly excluded from public representation.")

    # 7. Check Storage Files on Disk
    meta_file = storage_dir / f"{profile_id}.meta.json"
    emb_file = storage_dir / f"{profile_id}.emb.npz"
    print(f"\n7. Storage Verification on Disk:")
    print(f"   - Metadata JSON exists    : {meta_file.exists()} ({meta_file.name})")
    print(f"   - Biometric NPZ exists    : {emb_file.exists()} ({emb_file.name})")

    # 8. Demonstrate Profile Revocation and Biometric Purging
    print(f"\n8. Demonstrating Profile Revocation & Biometric Purging:")
    rev_res = service.revoke_profile(profile_id, reason="User exercised right to revoke voiceprint.")
    print(f"   - Revocation Status       : {rev_res.status.value}")
    print(f"   - Revoked Timestamp       : {rev_res.revoked_at}")
    print(f"   - Biometric NPZ Purged    : {not emb_file.exists()} (Purged from disk: {emb_file.name})")
    print(f"   - Metadata Audit Retained : {meta_file.exists()} (Audit trail preserved)")

    post_rev_status = service.get_enrollment_status(user_id)
    print(f"   - Final User Status       : {post_rev_status.status.value}")

    print("\n" + "=" * 76)
    print(" Phase 3 Voice Enrollment Pipeline execution complete.")
    print("=" * 76 + "\n")

    # Clean up synthetic sample files if generated
    if is_synthetic:
        for p in audio_paths:
            if p.exists():
                p.unlink()


if __name__ == "__main__":
    main()

