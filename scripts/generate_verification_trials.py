#!/usr/bin/env python3
"""Generate Verification Trials for Speaker Recognition Evaluation.

This script orchestrates the full Phase 5B pipeline:
1. Discover speakers and recordings from LibriSpeech splits.
2. Select enrollment and verification recordings per speaker.
3. Extract ECAPA-TDNN embeddings for all recordings (with disk caching).
4. Aggregate enrollment embeddings into reference profiles.
5. Generate genuine and impostor verification trials.
6. Validate data integrity and leakage prevention.
7. Write CSV trial manifests and JSON summaries.

Usage:
    python scripts/generate_verification_trials.py
    python scripts/generate_verification_trials.py --dataset-root datasets/librispeech
    python scripts/generate_verification_trials.py --splits dev-clean
    python scripts/generate_verification_trials.py --skip-embedding-extraction

Output:
    outputs/evaluation/dev/trials.csv
    outputs/evaluation/dev/summary.json
    outputs/evaluation/test/trials.csv
    outputs/evaluation/test/summary.json
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

from sentinelai.evaluation.speaker_discovery import (
    EnrollmentSelector,
    SpeakerRecordingDiscovery,
)
from sentinelai.evaluation.trial_generator import TrialGenerator
from sentinelai.evaluation.trial_manifest import TrialManifestWriter
from sentinelai.evaluation.leakage_validator import LeakageValidator


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the trial generation script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate speaker verification trials from LibriSpeech dataset."
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("datasets/librispeech"),
        help="Root directory of the LibriSpeech dataset.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/evaluation"),
        help="Root directory for output files.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["dev-clean", "test-clean"],
        help="Dataset splits to process.",
    )
    parser.add_argument(
        "--enrollment-count",
        type=int,
        default=3,
        help="Number of recordings for enrollment per speaker.",
    )
    parser.add_argument(
        "--max-impostors",
        type=int,
        default=10,
        help="Maximum impostor trials per speaker.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--skip-embedding-extraction",
        action="store_true",
        help="Skip embedding extraction (generate trial structure only).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    return parser.parse_args()


def process_split(
    split_name: str,
    dataset_root: Path,
    output_root: Path,
    enrollment_count: int,
    max_impostors: int,
    seed: int,
    skip_embeddings: bool,
) -> dict:
    """Process a single dataset split through the full trial generation pipeline.

    Args:
        split_name: Name of the split (e.g. 'dev-clean').
        dataset_root: Root path to the dataset.
        output_root: Root path for outputs.
        enrollment_count: Number of enrollment recordings per speaker.
        max_impostors: Maximum impostor trials per speaker.
        seed: Random seed.
        skip_embeddings: If True, skip the embedding extraction step.

    Returns:
        Dictionary with split processing summary statistics.
    """
    logger = logging.getLogger(__name__)
    split_short = "dev" if "dev" in split_name else "test"
    split_output = output_root / split_short

    logger.info(f"\n{'='*60}")
    logger.info(f"Processing split: {split_name}")
    logger.info(f"{'='*60}")

    # Step 1: Discover speakers and recordings
    logger.info("Step 1: Discovering speakers and recordings...")
    discovery = SpeakerRecordingDiscovery(dataset_root=dataset_root)
    speakers = discovery.discover_split(split_name)

    total_recordings = sum(s.recording_count for s in speakers.values())
    logger.info(
        f"  Found {len(speakers)} speakers, {total_recordings} recordings"
    )

    # Step 2: Select enrollment/verification splits
    logger.info("Step 2: Selecting enrollment and verification recordings...")
    selector = EnrollmentSelector(
        enrollment_count=enrollment_count,
        seed=seed,
    )
    enrollment_splits = selector.select(speakers)

    eligible = [s for s in enrollment_splits.values() if s.is_eligible]
    ineligible = [s for s in enrollment_splits.values() if not s.is_eligible]
    total_enroll = sum(s.enrollment_count for s in eligible)
    total_verify = sum(s.verification_count for s in eligible)

    logger.info(f"  Eligible speakers: {len(eligible)}")
    logger.info(f"  Ineligible speakers: {len(ineligible)}")
    logger.info(f"  Enrollment recordings: {total_enroll}")
    logger.info(f"  Verification recordings: {total_verify}")

    if ineligible:
        for s in ineligible:
            logger.warning(f"  Ineligible: {s.speaker_id} — {s.ineligibility_reason}")

    # Step 3: Embedding extraction (optional)
    if not skip_embeddings:
        logger.info("Step 3: Extracting embeddings (this may take several minutes)...")
        try:
            from sentinelai.evaluation.batch_embedder import BatchEmbedder

            embed_dir = split_output / "embeddings"
            embedder = BatchEmbedder(
                output_dir=embed_dir,
                progress_interval=50,
            )

            # Collect all recordings and their speaker IDs
            all_recs = []
            spk_map = {}
            for spk_id, split_info in enrollment_splits.items():
                if split_info.is_eligible:
                    for rec in split_info.enrollment_recordings + split_info.verification_recordings:
                        all_recs.append(rec)
                        spk_map[rec.stem] = spk_id

            all_recs = sorted(set(all_recs), key=lambda p: p.name)
            result = embedder.extract_batch(
                recordings=all_recs,
                speaker_ids=spk_map,
                split_name=split_name,
            )

            logger.info(
                f"  Embeddings: {result.total_extracted} extracted, "
                f"{result.total_skipped} cached, "
                f"{result.total_failed} failed"
            )
            logger.info(
                f"  Dimension: {result.embedding_dimension}, "
                f"Time: {result.total_extraction_time_sec:.1f}s"
            )

            if result.total_failed > 0:
                for fail in result.failed_recordings:
                    logger.error(f"  Failed: {fail['path']} — {fail['error']}")

            # Step 3b: Aggregate enrollment embeddings into reference profiles
            logger.info("Step 3b: Aggregating enrollment embeddings into reference profiles...")
            from sentinelai.enrollment.aggregation import aggregate_embeddings

            profiles_dir = split_output / "enrollment_profiles"
            profiles_dir.mkdir(parents=True, exist_ok=True)

            for spk_id, split_info in enrollment_splits.items():
                if not split_info.is_eligible:
                    continue

                enroll_embeddings = []
                for rec in split_info.enrollment_recordings:
                    entry = result.embeddings.get(rec.stem)
                    if entry is not None:
                        enroll_embeddings.append(entry.embedding)

                if len(enroll_embeddings) == enrollment_count:
                    agg_result = aggregate_embeddings(enroll_embeddings)
                    np.savez(
                        str(profiles_dir / f"{spk_id}_profile.npz"),
                        reference_embedding=agg_result.reference_embedding,
                        dimension=np.array(agg_result.dimension),
                        sample_count=np.array(agg_result.sample_count),
                        mean_pairwise_similarity=np.array(agg_result.mean_pairwise_similarity),
                    )

            logger.info(f"  Saved reference profiles to {profiles_dir}")

        except Exception as exc:
            logger.error(f"  Embedding extraction failed: {exc}")
            logger.info("  Continuing with trial structure generation...")
    else:
        logger.info("Step 3: Skipping embedding extraction (--skip-embedding-extraction)")

    # Step 4: Generate trials
    logger.info("Step 4: Generating verification trials...")
    generator = TrialGenerator(
        seed=seed,
        max_impostors_per_speaker=max_impostors,
    )
    trial_result = generator.generate_all_trials(enrollment_splits, split_name)

    logger.info(f"  Genuine trials: {trial_result.genuine_count}")
    logger.info(f"  Impostor trials: {trial_result.impostor_count}")
    logger.info(f"  Total trials: {trial_result.total_count}")
    logger.info(f"  Genuine:Impostor ratio: {trial_result.genuine_impostor_ratio}")

    # Step 5: Validate
    logger.info("Step 5: Validating data integrity...")
    validator = LeakageValidator()
    eligible_spk_ids = {s.speaker_id for s in eligible}

    validation = validator.validate_all(
        trials=trial_result.trials,
        enrollment_splits=enrollment_splits,
    )

    if validation.is_valid:
        logger.info(f"  ✓ {validation.summary}")
    else:
        logger.error(f"  ✗ {validation.summary}")
        for v in validation.violations:
            logger.error(f"    Violation: [{v['check']}] {v['description']}")

    # Step 6: Write manifests
    logger.info("Step 6: Writing trial manifests...")
    writer = TrialManifestWriter(output_dir=split_output)

    csv_path = writer.write_csv(trial_result.trials)
    logger.info(f"  CSV manifest: {csv_path}")

    enrollment_stats = {
        "enrollment_count_per_speaker": enrollment_count,
        "eligible_speakers": len(eligible),
        "ineligible_speakers": len(ineligible),
        "total_enrollment_recordings": total_enroll,
        "total_verification_recordings": total_verify,
    }
    summary_path = writer.write_summary(trial_result, enrollment_stats=enrollment_stats)
    logger.info(f"  JSON summary: {summary_path}")

    return {
        "split_name": split_name,
        "speakers_discovered": len(speakers),
        "total_recordings": total_recordings,
        "eligible_speakers": len(eligible),
        "ineligible_speakers": len(ineligible),
        "enrollment_recordings": total_enroll,
        "verification_recordings": total_verify,
        "genuine_trials": trial_result.genuine_count,
        "impostor_trials": trial_result.impostor_count,
        "total_trials": trial_result.total_count,
        "genuine_impostor_ratio": trial_result.genuine_impostor_ratio,
        "validation_passed": validation.is_valid,
        "validation_summary": validation.summary,
    }


def main() -> None:
    """Main entry point for the trial generation pipeline."""
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("SentinelAI Voice Verification — Phase 5B")
    logger.info("Multi-Speaker Enrollment & Trial Generation")
    logger.info("=" * 60)
    logger.info(f"Dataset root: {args.dataset_root}")
    logger.info(f"Output root: {args.output_root}")
    logger.info(f"Splits: {args.splits}")
    logger.info(f"Enrollment count: {args.enrollment_count}")
    logger.info(f"Max impostors/speaker: {args.max_impostors}")
    logger.info(f"Seed: {args.seed}")
    logger.info(f"Skip embeddings: {args.skip_embedding_extraction}")

    overall_start = time.time()
    all_results = []

    # Cross-split speaker disjoint validation
    all_split_speakers = {}

    for split_name in args.splits:
        result = process_split(
            split_name=split_name,
            dataset_root=args.dataset_root,
            output_root=args.output_root,
            enrollment_count=args.enrollment_count,
            max_impostors=args.max_impostors,
            seed=args.seed,
            skip_embeddings=args.skip_embedding_extraction,
        )
        all_results.append(result)

        # Collect speakers for cross-split validation
        discovery = SpeakerRecordingDiscovery(dataset_root=args.dataset_root)
        speakers = discovery.discover_split(split_name)
        all_split_speakers[split_name] = set(speakers.keys())

    # Cross-split validation
    if len(all_split_speakers) > 1:
        logger.info("\n" + "=" * 60)
        logger.info("Cross-split Speaker Disjoint Validation")
        logger.info("=" * 60)
        validator = LeakageValidator()
        split_keys = list(all_split_speakers.keys())
        for i in range(len(split_keys)):
            for j in range(i + 1, len(split_keys)):
                is_disjoint, overlap = validator.validate_speaker_disjoint(
                    all_split_speakers[split_keys[i]],
                    all_split_speakers[split_keys[j]],
                )
                if is_disjoint:
                    logger.info(
                        f"  ✓ {split_keys[i]} vs {split_keys[j]}: "
                        f"Speaker-disjoint (0 overlap)"
                    )
                else:
                    logger.error(
                        f"  ✗ {split_keys[i]} vs {split_keys[j]}: "
                        f"{len(overlap)} overlapping speakers: {overlap}"
                    )

    total_time = time.time() - overall_start

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    for r in all_results:
        logger.info(f"\n  Split: {r['split_name']}")
        logger.info(f"    Speakers: {r['speakers_discovered']} ({r['eligible_speakers']} eligible)")
        logger.info(f"    Recordings: {r['total_recordings']}")
        logger.info(f"    Trials: {r['total_trials']} (genuine={r['genuine_trials']}, impostor={r['impostor_trials']})")
        logger.info(f"    Ratio: {r['genuine_impostor_ratio']}")
        logger.info(f"    Validation: {'✓ PASSED' if r['validation_passed'] else '✗ FAILED'}")

    logger.info(f"\n  Total pipeline time: {total_time:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

