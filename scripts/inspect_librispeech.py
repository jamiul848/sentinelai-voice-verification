"""CLI Script for LibriSpeech Dataset Inspection and Validation (Phase 5A).

Usage:
    python scripts/inspect_librispeech.py
    python scripts/inspect_librispeech.py --dataset-dir datasets/librispeech --output-json reports/librispeech_report.json --output-md reports/librispeech_report.md
"""

import argparse
from pathlib import Path
import sys
import time

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sentinelai.evaluation.dataset_inspector import DatasetInspector
from sentinelai.evaluation.dataset_report import DatasetInspectionReport


def print_banner() -> None:
    """Print executive inspection banner."""
    print("=" * 80)
    print("       SENTINELAI DATASET INSPECTION & VALIDATION PIPELINE (PHASE 5A)")
    print("=" * 80)
    print(" Target Dataset: LibriSpeech (dev-clean & test-clean)")
    print(" Objective     : Verify file integrity, sample rates, duration, and speaker overlap")
    print(" Guardrail     : Does NOT calculate verification accuracy or claim benchmark status")
    print("=" * 80)
    print()


def print_summary(report: DatasetInspectionReport, elapsed_sec: float) -> None:
    """Print structured summary to console."""
    print("=" * 80)
    print("                      DATASET INSPECTION SUMMARY")
    print("=" * 80)
    print(f" Dataset Root Directory   : {report.dataset_root}")
    print(f" Inspection Duration      : {elapsed_sec:.2f} seconds")
    print(f" Inspected Splits         : {', '.join(report.splits.keys())}")
    print()
    print("[-] OVERALL AGGREGATED METRICS:")
    print(f"    - Total Unique Speakers   : {report.total_speakers}")
    print(f"    - Total Audio Chapters    : {report.total_chapters}")
    print(f"    - Total Audio Utterances  : {report.total_utterances:,}")
    print(f"    - Total Audio Duration    : {report.total_duration_formatted} ({report.total_duration_sec:.2f} s)")
    print(f"    - Corrupted Audio Files   : {report.total_corrupted_files}")
    print(f"    - Empty (0-byte) Files    : {report.total_empty_files}")
    print(f"    - Dev/Test Speaker Overlap: {len(report.speaker_overlap)} speakers ({'DISJOINT / ZERO LEAKAGE' if not report.has_speaker_overlap else 'LEAKAGE DETECTED'})")
    print()

    print("[-] PER-SPLIT BREAKDOWN:")
    for split_name, split in report.splits.items():
        print(f"    [{split_name.upper()}]")
        print(f"        • Directory Path      : {split.root_path}")
        print(f"        • Speakers            : {split.total_speakers}")
        print(f"        • Chapters            : {split.total_chapters}")
        print(f"        • Utterances          : {split.total_utterances:,}")
        print(f"        • Total Duration      : {split.total_duration_formatted} ({split.total_duration_sec:.2f} s)")
        print(f"        • Mean Duration       : {split.mean_duration_sec:.2f} s (±{split.std_duration_sec:.2f} s)")
        print(f"        • Min / Max Duration  : {split.min_duration_sec:.2f} s / {split.max_duration_sec:.2f} s")
        print(f"        • Sample Rate Dist    : " + ", ".join(f"{k} Hz: {v}" for k, v in split.sample_rate_distribution.items()))
        print(f"        • Channel Dist        : " + ", ".join(f"{'Mono' if k == 1 else 'Stereo' if k == 2 else k}: {v}" for k, v in split.channel_distribution.items()))
        print(f"        • Subtype Dist        : " + ", ".join(f"{k}: {v}" for k, v in split.subtype_distribution.items()))
        print(f"        • Audio Formats       : " + ", ".join(f"{k}: {v}" for k, v in split.format_distribution.items()))
        print(f"        • Storage Size        : {split.total_size_mb:.2f} MB ({split.total_size_bytes:,} bytes)")
        print(f"        • Corrupted / Empty   : {len(split.corrupted_files)} / {len(split.empty_files)}")
        print()

    print("[-] SUITABILITY FOR EVALUATION:")
    status_label = "SUITABLE FOR PHASE 5 BENCHMARKING" if report.is_suitable_for_evaluation else "ANOMALIES DETECTED"
    print(f"    Determination: [{status_label}]")
    print(f"    {report.suitability_summary}")
    print()

    print("[-] CRITICAL BENCHMARK LIMITATIONS:")
    for idx, limitation in enumerate(report.limitations, 1):
        print(f"    {idx}. {limitation}")
    print()
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SentinelAI LibriSpeech Dataset Inspector & Integrity Validator (Phase 5A)",
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="datasets/librispeech",
        help="Root path to the LibriSpeech dataset directory (default: 'datasets/librispeech').",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="reports/librispeech_inspection_report.json",
        help="Path where the structured JSON report will be saved (default: 'reports/librispeech_inspection_report.json').",
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default="reports/librispeech_inspection_report.md",
        help="Path where the formatted Markdown report will be saved (default: 'reports/librispeech_inspection_report.md').",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["dev-clean", "test-clean"],
        help="Dataset split names to inspect (default: ['dev-clean', 'test-clean']).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel worker threads for header inspection (default: 8).",
    )

    args = parser.parse_args()

    print_banner()

    dataset_path = Path(args.dataset_dir)
    if not dataset_path.exists():
        print(f"[!] ERROR: Dataset directory '{dataset_path}' does not exist.")
        print(f"    Please ensure LibriSpeech is downloaded and extracted to '{dataset_path}'.")
        sys.exit(1)

    print(f"[*] Initializing DatasetInspector for '{dataset_path}'...")
    print(f"    - Target Splits : {args.splits}")
    print(f"    - Worker Threads: {args.workers}")
    print()

    inspector = DatasetInspector(
        dataset_root=dataset_path,
        split_names=args.splits,
        max_workers=args.workers,
    )

    print("[*] Scanning and validating audio files in parallel...")
    t0 = time.perf_counter()
    report = inspector.inspect_dataset()
    elapsed = time.perf_counter() - t0

    # Save reports
    json_path = Path(args.output_json)
    md_path = Path(args.output_md)

    saved_json = report.save_json(json_path)
    saved_md = report.save_markdown(md_path)

    print(f"[+] Structured JSON report saved to: {saved_json}")
    print(f"[+] Formatted Markdown report saved to: {saved_md}")
    print()

    print_summary(report, elapsed)


if __name__ == "__main__":
    main()

