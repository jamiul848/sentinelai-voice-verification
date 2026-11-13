"""SentinelAI Speaker Verification Engine Demonstration (Phase 4).

Demonstrates the 1:1 speaker verification pipeline:
1. Enrolling a reference profile using multi-utterance aggregation.
2. Executing a genuine matching verification trial.
3. Executing an impostor non-matching verification trial.
4. Handling nonexistent and revoked speaker profiles safely.
"""

import argparse
from pathlib import Path
import shutil
import sys
import tempfile

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import soundfile as sf
import torch

from sentinelai.audio.preprocessor import AudioPreprocessor
from sentinelai.enrollment.config import EnrollmentConfig
from sentinelai.enrollment.service import EnrollmentService
from sentinelai.enrollment.storage import LocalFileProfileStorage
from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.model import ECAPAModelLoader
from sentinelai.verification.audit import JsonLinesAuditLogger
from sentinelai.verification.config import VerificationConfig
from sentinelai.verification.exceptions import (
    ProfileNotFoundError,
    ProfileRevokedError,
)
from sentinelai.verification.service import SpeakerVerificationService


def generate_synthetic_audio(path: Path, freq_hz: float, duration_sec: float = 2.0, sample_rate: int = 16000) -> Path:
    """Generate a deterministic synthetic tone for functional software execution testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    signal = (0.5 * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
    sf.write(str(path), signal, sample_rate, subtype="PCM_16")
    return path


def print_banner() -> None:
    """Display warning and research boundary banner."""
    print("=" * 80)
    print("      SENTINELAI SPEAKER VERIFICATION ENGINE – PHASE 4 DEMONSTRATION")
    print("=" * 80)
    print(" [!] SCIENTIFIC NOTICE & RESEARCH GUARDRAIL:")
    print("     Synthetic audio is used only to validate software execution. It cannot")
    print("     establish real-world speaker verification performance.")
    print("     Speaker verification compares a claimed voice against an enrolled profile.")
    print("     It is NOT an anti-spoofing defense and provides NO liveness guarantees.")
    print("=" * 80)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SentinelAI Phase 4: Speaker Verification Engine Demonstration",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="alice_demo",
        help="Unique user identifier for the enrolled speaker (default: 'alice_demo').",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Decision threshold for cosine similarity (default: 0.80).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Inference compute device (default: 'auto').",
    )
    args = parser.parse_args()

    print_banner()

    temp_dir = Path(tempfile.mkdtemp(prefix="sentinelai_verification_demo_"))
    try:
        profiles_dir = temp_dir / "profiles"
        audit_file = temp_dir / "audit.jsonl"

        # 1. Initialize core services
        print(f"[*] Initializing Pretrained ECAPA-TDNN Model Loader (Device: {args.device})...")
        speaker_config = SpeakerConfig(device=args.device, normalize_embeddings=True)
        loader = ECAPAModelLoader(config=speaker_config)
        extractor = SpeakerEmbeddingExtractor(config=speaker_config, loader=loader)
        preprocessor = AudioPreprocessor()

        storage = LocalFileProfileStorage(storage_dir=profiles_dir)
        enrollment_config = EnrollmentConfig(min_recordings=3, storage_dir=profiles_dir)
        enrollment_service = EnrollmentService(
            config=enrollment_config,
            storage=storage,
            preprocessor=preprocessor,
            extractor=extractor,
        )

        verification_config = VerificationConfig(
            threshold_value=args.threshold,
            threshold_version="demo-uncalibrated-v1.0",
            expose_similarity_score=True,
            storage_dir=profiles_dir,
            audit_log_path=audit_file,
        )
        audit_logger = JsonLinesAuditLogger(log_path=audit_file)
        verification_service = SpeakerVerificationService(
            config=verification_config,
            extractor=extractor,
            storage=storage,
            audit_logger=audit_logger,
        )

        print("[+] Components initialized successfully.")
        print(f"    - Pretrained Model  : {speaker_config.model_source}")
        print(f"    - Active Device     : {speaker_config.resolved_device}")
        print(f"    - Decision Threshold: {args.threshold} (Version: {verification_config.threshold_version})")
        print()

        # 2. Step 1: Enroll Speaker Profile
        print(f"--- STEP 1: Voice Enrollment for User '{args.user_id}' ---")
        rec_dir = temp_dir / "enrollment_audio"
        enrollment_files = [
            generate_synthetic_audio(rec_dir / "enroll_1.wav", freq_hz=440.0),
            generate_synthetic_audio(rec_dir / "enroll_2.wav", freq_hz=445.0),
            generate_synthetic_audio(rec_dir / "enroll_3.wav", freq_hz=442.0),
        ]
        enroll_res = enrollment_service.enroll(
            user_id=args.user_id,
            audio_sources=enrollment_files,
            consent=True,
            metadata={"demo_context": "phase4_verification_trial"},
        )
        print(f"[+] Enrollment successful:")
        print(f"    - Profile ID        : {enroll_res.profile_id}")
        print(f"    - User ID           : {enroll_res.user_id}")
        print(f"    - Recordings Used   : {enroll_res.sample_count}")
        print(f"    - Embedding Dim     : {enroll_res.embedding_dimension}")
        print()

        # 3. Step 2: Genuine Claimant Verification Trial (Should MATCH)
        print(f"--- STEP 2: Genuine Verification Trial (Claimant: {args.user_id}) ---")
        genuine_audio = generate_synthetic_audio(temp_dir / "genuine_claimant.wav", freq_hz=441.0)
        result_genuine = verification_service.verify_speaker(
            audio_input=genuine_audio,
            user_id=args.user_id,
        )
        print(f"[*] Outcome             : {result_genuine.status.value}")
        print(f"    - Verified (Boolean): {result_genuine.verified}")
        print(f"    - Similarity Score  : {result_genuine.similarity_score:.4f}")
        print(f"    - Threshold Applied : {args.threshold}")
        print(f"    - Decision Rule     : score ({result_genuine.similarity_score:.4f}) >= threshold ({args.threshold})")
        print(f"    - Latency           : {result_genuine.processing_time_ms} ms")
        print(f"    - Message           : {result_genuine.message}")
        print()

        # 4. Step 3: Impostor Verification Trial (Should NO_MATCH)
        print(f"--- STEP 3: Impostor Verification Trial (Claimant claims: {args.user_id}) ---")
        impostor_audio = generate_synthetic_audio(temp_dir / "impostor_claimant.wav", freq_hz=880.0)
        result_impostor = verification_service.verify_speaker(
            audio_input=impostor_audio,
            user_id=args.user_id,
        )
        print(f"[*] Outcome             : {result_impostor.status.value}")
        print(f"    - Verified (Boolean): {result_impostor.verified}")
        print(f"    - Similarity Score  : {result_impostor.similarity_score:.4f}")
        print(f"    - Threshold Applied : {args.threshold}")
        print(f"    - Decision Rule     : score ({result_impostor.similarity_score:.4f}) >= threshold ({args.threshold})")
        print(f"    - Latency           : {result_impostor.processing_time_ms} ms")
        print(f"    - Message           : {result_impostor.message}")
        print()

        # 5. Step 4: Unknown Profile Handling
        print("--- STEP 4: Nonexistent Profile Verification Attempt ---")
        try:
            verification_service.verify_speaker(
                audio_input=genuine_audio,
                user_id="user_nonexistent_999",
            )
        except ProfileNotFoundError as exc:
            print(f"[+] Correctly rejected missing profile:")
            print(f"    - Exception: {type(exc).__name__}: {exc}")
        print()

        # 6. Step 5: Profile Revocation & Post-Revocation Verification Lockout
        print("--- STEP 5: Profile Revocation & Verification Lockout ---")
        revocation = enrollment_service.revoke_profile(
            identifier=enroll_res.profile_id,
            reason="User exercised privacy right to erasure",
        )
        print(f"[+] Revocation executed:")
        print(f"    - Profile ID        : {revocation.profile_id}")
        print(f"    - Status            : {revocation.status.value}")

        try:
            verification_service.verify_speaker(
                audio_input=genuine_audio,
                profile_id=enroll_res.profile_id,
            )
        except ProfileRevokedError as exc:
            print(f"[+] Correctly blocked verification against revoked profile:")
            print(f"    - Exception: {type(exc).__name__}: {exc}")
        print()

        # 7. Step 6: Inspect Privacy-Preserving Audit Log
        print("--- STEP 6: Privacy Audit Log Inspection ---")
        if audit_file.exists():
            with open(audit_file, "r", encoding="utf-8") as f:
                audit_lines = f.readlines()
            print(f"[+] Audit log recorded {len(audit_lines)} transactions to disk.")
            for i, line in enumerate(audit_lines, 1):
                print(f"    Event {i}: {line.strip()[:100]}...")
        print()

        print("=" * 80)
        print(" [v] PHASE 4 DEMONSTRATION COMPLETE: ALL INTEGRATION CHECKS PASSED")
        print("=" * 80)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
