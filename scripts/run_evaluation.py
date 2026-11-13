#!/usr/bin/env python3
"""Run Speaker Verification Evaluation and Threshold Calibration (Phase 5C).

Executes:
1. Load development trials from outputs/evaluation/dev/trials.csv.
2. Extract or load cached embeddings for enrollment reference and probe audio.
3. Score development trials using cosine similarity.
4. Calibrate decision threshold at Equal Error Rate (EER) on dev-clean.
5. Save and freeze the calibrated threshold.
6. Load test trials from outputs/evaluation/test/trials.csv.
7. Score test trials using cosine similarity.
8. Evaluate test trials strictly using the frozen threshold.
9. Render ROC, DET, FAR/FRR, distribution, and confusion matrix figures.
10. Save reports to reports/evaluation/.

Usage:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --synthetic-demo
    python scripts/run_evaluation.py --reports-dir reports/evaluation
"""

import argparse
import logging
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from sentinelai.evaluation.evaluator import SpeakerVerificationEvaluator
from sentinelai.evaluation.threshold_calibrator import ThresholdCalibrator
from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial, TrialScorer


def setup_logging(verbose: bool = False) -> None:
    """Configure terminal logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SentinelAI Voice Verification Phase 5C Benchmark Evaluation & Threshold Calibration"
    )
    parser.add_argument(
        "--evaluation-dir",
        type=Path,
        default=Path("outputs/evaluation"),
        help="Directory containing dev/trials.csv and test/trials.csv",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("datasets/librispeech"),
        help="Root path to LibriSpeech dataset",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports/evaluation"),
        help="Directory to save evaluation reports, JSON files, and figures",
    )
    parser.add_argument(
        "--demo-mode",
        "--synthetic-demo",
        dest="synthetic_demo",
        action="store_true",
        help="Run in demonstration mode using synthetic scores (disabled by default; real ECAPA inference is required)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed debug logging",
    )
    return parser.parse_args()


def generate_synthetic_dataset(
    split_name: str,
    n_genuine: int,
    n_impostor: int,
    gen_mean: float = 0.76,
    gen_std: float = 0.08,
    imp_mean: float = 0.44,
    imp_std: float = 0.09,
    seed: int = 42,
) -> ScoredDataset:
    """Generate representative synthetic score distributions modeled on ECAPA-TDNN VoxCeleb characteristics.

    Used when running --synthetic-demo or when raw audio extraction is deferred.
    """
    rng = np.random.default_rng(seed)

    gen_scores = rng.normal(loc=gen_mean, scale=gen_std, size=n_genuine)
    imp_scores = rng.normal(loc=imp_mean, scale=imp_std, size=n_impostor)

    # Clamp scores strictly to [-1.0, 1.0]
    gen_scores = np.clip(gen_scores, -1.0, 1.0)
    imp_scores = np.clip(imp_scores, -1.0, 1.0)

    all_scores = np.concatenate([gen_scores, imp_scores])
    all_labels = np.concatenate([np.ones(n_genuine, dtype=np.int64), np.zeros(n_impostor, dtype=np.int64)])

    trials = []
    for i in range(len(all_scores)):
        is_gen = all_labels[i] == 1
        trials.append(
            ScoredTrial(
                trial_id=f"synth-{split_name}-{i:05d}",
                claimed_speaker_id=f"spk_{i % 30}",
                actual_speaker_id=f"spk_{i % 30}" if is_gen else f"spk_{(i + 1) % 30}",
                trial_type="genuine" if is_gen else "impostor",
                ground_truth_label=int(all_labels[i]),
                similarity_score=float(round(all_scores[i], 6)),
                split=split_name,
                model_identifier="speechbrain/spkrec-ecapa-voxceleb",
                score_source="synthetic_demonstration",
            )
        )

    return ScoredDataset(
        split_name=split_name,
        trials=trials,
        scores=all_scores,
        labels=all_labels,
        model_identifier="speechbrain/spkrec-ecapa-voxceleb",
    )


def load_or_score_split(
    split_name: str,
    trials_csv: Path,
    scores_csv: Path,
    scorer: TrialScorer,
    dataset_root: Path,
    use_synthetic: bool = False,
) -> ScoredDataset:
    """Load existing scores.csv, score real audio trials, or synthesize for demonstration."""
    logger = logging.getLogger(__name__)

    # Option 1: Explicit Synthetic Demo Mode
    if use_synthetic:
        logger.info(
            f"Using statistically calibrated demonstration score distribution for '{split_name}' "
            "(Requested via --demo-mode)..."
        )
        n_gen = 2583 if "dev" in split_name else 2264
        n_imp = 400 if "dev" in split_name else 360
        seed = 42 if "dev" in split_name else 1337
        ds = generate_synthetic_dataset(
            split_name=split_name,
            n_genuine=n_gen,
            n_impostor=n_imp,
            seed=seed,
        )
        scorer.write_scores_csv(ds, scores_csv)
        return ds

    # Option 2: Existing Real Score Manifest
    if scores_csv.exists():
        try:
            logger.info(f"Loading existing score manifest from {scores_csv}...")
            return scorer.load_scores_csv(scores_csv, split_name=split_name, allow_synthetic=False)
        except ValueError as err:
            logger.warning(f"Existing score manifest rejected: {err}. Re-scoring from real embeddings...")

    # Option 3: Real ECAPA Inference Scoring from trials.csv and cached embeddings
    logger.info(f"Scoring {split_name} from trial manifest {trials_csv} using real ECAPA embeddings...")
    import csv

    if not trials_csv.exists():
        raise FileNotFoundError(f"Trial manifest not found at {trials_csv}")

    rows = []
    with open(trials_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["ground_truth_label"] = int(r["ground_truth_label"])
            rows.append(r)

    profiles_dir = trials_csv.parent / "enrollment_profiles"
    embeddings_dir = trials_csv.parent / "embeddings"

    if not profiles_dir.exists() or not embeddings_dir.exists():
        raise FileNotFoundError(
            f"Real ECAPA embeddings not found in {embeddings_dir} or profiles in {profiles_dir}. "
            f"Run 'python scripts/generate_verification_trials.py' to extract embeddings from LibriSpeech "
            f"recordings first. Silent demonstration fallback is disabled."
        )

    ref_embeddings = {}
    probe_embeddings = {}

    logger.info(f"Loading real embeddings from {profiles_dir} and {embeddings_dir}...")
    for p in profiles_dir.glob("*_profile.npz"):
        spk_id = p.stem.replace("_profile", "")
        data = np.load(str(p))
        ref_embeddings[spk_id] = data["reference_embedding"]

    for p in embeddings_dir.glob("*.npz"):
        stem = p.stem
        data = np.load(str(p))
        probe_embeddings[stem] = data["embedding"]

    if len(ref_embeddings) == 0 or len(probe_embeddings) == 0:
        raise FileNotFoundError(
            f"Embedding directories exist but are empty (found {len(ref_embeddings)} profiles, "
            f"{len(probe_embeddings)} probe embeddings). Real extraction is required."
        )

    dataset = scorer.score_trials(rows, ref_embeddings, probe_embeddings, split_name)
    scorer.write_scores_csv(dataset, scores_csv)
    return dataset


def main() -> None:
    """Execute the Phase 5C evaluation demonstration."""
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 70)
    print(" SentinelAI Voice Verification — Phase 5C")
    print(" Threshold Calibration & Benchmark Performance Analysis")
    print("=" * 70)

    start_time = time.time()
    scorer = TrialScorer()

    # 1. Load / Score Development Trials
    dev_trials_csv = args.evaluation_dir / "dev" / "trials.csv"
    dev_scores_csv = args.evaluation_dir / "dev" / "scores.csv"

    dev_dataset = load_or_score_split(
        split_name="dev-clean",
        trials_csv=dev_trials_csv,
        scores_csv=dev_scores_csv,
        scorer=scorer,
        dataset_root=args.dataset_root,
        use_synthetic=args.synthetic_demo,
    )

    # 2. Load / Score Test Trials
    test_trials_csv = args.evaluation_dir / "test" / "trials.csv"
    test_scores_csv = args.evaluation_dir / "test" / "scores.csv"

    test_dataset = load_or_score_split(
        split_name="test-clean",
        trials_csv=test_trials_csv,
        scores_csv=test_scores_csv,
        scorer=scorer,
        dataset_root=args.dataset_root,
        use_synthetic=args.synthetic_demo,
    )

    # 3. Execute End-to-End Evaluation Pipeline
    evaluator = SpeakerVerificationEvaluator(reports_dir=args.reports_dir)
    pipeline_result = evaluator.evaluate(
        dev_dataset=dev_dataset,
        test_dataset=test_dataset,
    )

    elapsed = time.time() - start_time
    dev_sum = pipeline_result.dev_summary
    test_sum = pipeline_result.test_summary
    th_meta = pipeline_result.threshold_metadata

    # 4. Print Summary Terminal Output
    print("\n" + "=" * 70)
    print(" EVALUATION BENCHMARK RESULTS")
    print("=" * 70)
    print(f" Pretrained Model:       {th_meta.model_identifier}")
    print(f" Calibrated Threshold:   θ* = {th_meta.threshold_value:.4f}")
    print(f" Calibration Corpus:     {th_meta.calibration_dataset}")
    print(f" Calibration Timestamp:  {th_meta.calibration_timestamp}")
    print("-" * 70)
    print(" METRICS COMPARISON:")
    print(f" {'Metric':<28} | {'dev-clean (Calibrated)':<22} | {'test-clean (Frozen)':<20}")
    print("-" * 70)
    print(f" {'Total Evaluation Trials':<28} | {dev_sum.total_trials:<22,d} | {test_sum.total_trials:<20,d}")
    print(f" {'Genuine Trials':<28} | {dev_sum.genuine_trials:<22,d} | {test_sum.genuine_trials:<20,d}")
    print(f" {'Impostor Trials':<28} | {dev_sum.impostor_trials:<22,d} | {test_sum.impostor_trials:<20,d}")
    print(f" {'Equal Error Rate (EER)':<28} | {dev_sum.eer.eer_percent:<21.2f}% | {test_sum.eer.eer_percent:<19.2f}% (diag)")
    print(f" {'Operational FAR':<28} | {dev_sum.operating_metrics.far * 100:<21.2f}% | {test_sum.operating_metrics.far * 100:<19.2f}%")
    print(f" {'Operational FRR':<28} | {dev_sum.operating_metrics.frr * 100:<21.2f}% | {test_sum.operating_metrics.frr * 100:<19.2f}%")
    print(f" {'Classification Accuracy':<28} | {dev_sum.operating_metrics.accuracy * 100:<21.2f}% | {test_sum.operating_metrics.accuracy * 100:<19.2f}%")
    print(f" {'Precision':<28} | {dev_sum.operating_metrics.precision * 100:<21.2f}% | {test_sum.operating_metrics.precision * 100:<19.2f}%")
    print(f" {'Recall (1 - FRR)':<28} | {dev_sum.operating_metrics.recall * 100:<21.2f}% | {test_sum.operating_metrics.recall * 100:<19.2f}%")
    print(f" {'F1-Score':<28} | {dev_sum.operating_metrics.f1_score:<22.4f} | {test_sum.operating_metrics.f1_score:<20.4f}")
    print(f" {'ROC-AUC':<28} | {dev_sum.roc_auc:<22.4f} | {test_sum.roc_auc:<20.4f}")
    print("-" * 70)
    print(" GENERATED ARTIFACTS:")
    print(f" - Calibrated Threshold:   {pipeline_result.threshold_json_path}")
    print(f" - Development Metrics:    {pipeline_result.dev_metrics_json_path}")
    print(f" - Test Metrics:           {pipeline_result.test_metrics_json_path}")
    print(f" - Markdown Research Paper:{pipeline_result.report_markdown_path}")
    print(f" - Figures Directory:      {args.reports_dir / 'figures'}")
    print(f"\n Total Pipeline Wall Time: {elapsed:.2f}s")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

