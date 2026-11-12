"""Trial Manifest Writer for Speaker Verification Evaluation.

Serializes verification trials into CSV manifests and JSON summary reports
suitable for Phase 5C performance metric computation.
"""

import csv
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sentinelai.evaluation.trial_generator import TrialGenerationResult, VerificationTrial

logger = logging.getLogger(__name__)


class TrialManifestWriter:
    """Writes verification trial manifests as CSV and JSON summary files.

    CSV manifest columns:
        trial_id, claimed_speaker_id, actual_speaker_id, enrollment_recording_ids,
        verification_recording_id, trial_type, ground_truth_label, split, model_identifier

    JSON summary contains:
        - Trial count statistics (genuine, impostor, total, ratio).
        - Eligible speaker count.
        - Generation metadata (timestamp, seed, model).
    """

    CSV_COLUMNS = [
        "trial_id",
        "claimed_speaker_id",
        "actual_speaker_id",
        "enrollment_recording_ids",
        "verification_recording_id",
        "trial_type",
        "ground_truth_label",
        "split",
        "model_identifier",
    ]

    def __init__(self, output_dir: Path) -> None:
        """Initialize the manifest writer.

        Args:
            output_dir: Directory to write manifest files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_csv(
        self, trials: List[VerificationTrial], filename: str = "trials.csv"
    ) -> Path:
        """Write trials to a CSV manifest file.

        Args:
            trials: List of VerificationTrial instances.
            filename: Output filename (default: 'trials.csv').

        Returns:
            Path to the written CSV file.
        """
        csv_path = self.output_dir / filename

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()

            for trial in trials:
                row = {
                    "trial_id": trial.trial_id,
                    "claimed_speaker_id": trial.claimed_speaker_id,
                    "actual_speaker_id": trial.actual_speaker_id,
                    "enrollment_recording_ids": ";".join(
                        trial.enrollment_recording_ids
                    ),
                    "verification_recording_id": trial.verification_recording_id,
                    "trial_type": trial.trial_type,
                    "ground_truth_label": trial.ground_truth_label,
                    "split": trial.split,
                    "model_identifier": trial.model_identifier,
                }
                writer.writerow(row)

        logger.info(f"Wrote {len(trials)} trials to {csv_path}")
        return csv_path

    def write_summary(
        self,
        result: TrialGenerationResult,
        enrollment_stats: Optional[Dict[str, Any]] = None,
        filename: str = "summary.json",
    ) -> Path:
        """Write a JSON summary report for the trial generation.

        Args:
            result: TrialGenerationResult with statistics.
            enrollment_stats: Optional additional enrollment statistics.
            filename: Output filename (default: 'summary.json').

        Returns:
            Path to the written JSON file.
        """
        summary: Dict[str, Any] = {
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "split_name": result.split_name,
            "model_identifier": result.model_identifier,
            "seed": result.seed,
            "trial_statistics": {
                "genuine_trials": result.genuine_count,
                "impostor_trials": result.impostor_count,
                "total_trials": result.total_count,
                "genuine_impostor_ratio": result.genuine_impostor_ratio,
                "impostors_per_speaker": result.impostors_per_speaker,
            },
            "eligible_speakers": result.eligible_speakers,
        }

        if enrollment_stats:
            summary["enrollment_statistics"] = enrollment_stats

        json_path = self.output_dir / filename

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Wrote summary to {json_path}")
        return json_path

    def read_csv(self, filename: str = "trials.csv") -> List[Dict[str, Any]]:
        """Read a previously written CSV manifest back into memory.

        Args:
            filename: CSV filename to read.

        Returns:
            List of dictionaries, each representing one trial row.
        """
        csv_path = self.output_dir / filename
        rows: List[Dict[str, Any]] = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["ground_truth_label"] = int(row["ground_truth_label"])
                row["enrollment_recording_ids"] = row[
                    "enrollment_recording_ids"
                ].split(";")
                rows.append(row)

        return rows

