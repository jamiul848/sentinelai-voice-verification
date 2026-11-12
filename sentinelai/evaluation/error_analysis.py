"""Error Analysis Engine for Speaker Verification.

Performs qualitative and quantitative diagnostic inspection of verification failures:
- False Acceptance (FA / Type I) and False Rejection (FR / Type II) classification.
- Boundary proximity analysis (|score - threshold| <= 0.05).
- Identification of most frequently rejected genuine speakers ("goats") and impostor accepted speakers ("wolves").
- Sanitized reporting with zero raw audio or biometric embedding exposure.
"""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial

logger = logging.getLogger(__name__)


@dataclass
class SanitizedErrorRecord:
    """Sanitized diagnostic record of an individual verification error.

    Contains trial metadata and decision proximity without exposing biometric embeddings.
    """

    trial_id: str
    error_type: str  # 'false_rejection' or 'false_acceptance'
    claimed_speaker_id: str
    actual_speaker_id: str
    similarity_score: float
    decision_threshold: float
    distance_to_threshold: float
    is_boundary_case: bool  # True if |score - threshold| <= 0.05

    def to_dict(self) -> Dict[str, Any]:
        """Convert error record to JSON-serializable dictionary."""
        return {
            "trial_id": self.trial_id,
            "error_type": self.error_type,
            "claimed_speaker_id": self.claimed_speaker_id,
            "actual_speaker_id": self.actual_speaker_id,
            "similarity_score": round(self.similarity_score, 6),
            "decision_threshold": round(self.decision_threshold, 6),
            "distance_to_threshold": round(self.distance_to_threshold, 6),
            "is_boundary_case": self.is_boundary_case,
        }


@dataclass
class ErrorAnalysisSummary:
    """Comprehensive diagnostic summary of verification errors on an evaluation partition."""

    dataset_name: str
    decision_threshold: float
    total_trials: int
    total_errors: int
    error_rate_percent: float
    false_rejections_count: int
    false_acceptances_count: int
    boundary_errors_count: int
    boundary_errors_percentage: float
    top_rejected_speakers: List[Dict[str, Any]]
    top_accepted_impostors: List[Dict[str, Any]]
    score_proximity_stats: Dict[str, float]
    sanitized_errors: List[SanitizedErrorRecord] = field(default_factory=list)

    def to_dict(self, include_all_errors: bool = True) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        data = {
            "dataset_name": self.dataset_name,
            "decision_threshold": round(self.decision_threshold, 6),
            "total_trials": self.total_trials,
            "total_errors": self.total_errors,
            "error_rate_percent": round(self.error_rate_percent, 2),
            "false_rejections_count": self.false_rejections_count,
            "false_acceptances_count": self.false_acceptances_count,
            "boundary_errors_count": self.boundary_errors_count,
            "boundary_errors_percentage": round(self.boundary_errors_percentage, 2),
            "top_rejected_speakers": self.top_rejected_speakers,
            "top_accepted_impostors": self.top_accepted_impostors,
            "score_proximity_stats": {k: round(v, 4) for k, v in self.score_proximity_stats.items()},
        }
        if include_all_errors:
            data["sanitized_errors"] = [e.to_dict() for e in self.sanitized_errors]
        return data

    def save_json(self, output_path: Path, include_all_errors: bool = True) -> Path:
        """Save error analysis report to a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(include_all_errors=include_all_errors), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved error analysis summary to {output_path}")
        return output_path


class ErrorAnalyzer:
    """Performs qualitative failure mode analysis on scored verification trials."""

    BOUNDARY_MARGIN: float = 0.05

    def __init__(self, boundary_margin: float = BOUNDARY_MARGIN) -> None:
        """Initialize error analyzer.

        Args:
            boundary_margin: Distance from threshold defining a boundary case.
        """
        self.boundary_margin = boundary_margin

    def analyze(
        self,
        dataset: ScoredDataset,
        threshold: float,
    ) -> ErrorAnalysisSummary:
        """Analyze verification errors in a scored dataset at a specific decision threshold.

        Decision Rule:
            MATCH when similarity_score >= threshold
            NO_MATCH when similarity_score < threshold

        Errors:
            False Rejection (FR): label == 1 and score < threshold
            False Acceptance (FA): label == 0 and score >= threshold

        Args:
            dataset: ScoredDataset containing evaluated trials.
            threshold: Decision threshold.

        Returns:
            ErrorAnalysisSummary instance.
        """
        sanitized_errors: List[SanitizedErrorRecord] = []
        fr_speaker_counts: Counter = Counter()
        fa_impostor_counts: Counter = Counter()
        distances: List[float] = []

        boundary_count = 0

        for trial in dataset.trials:
            score = trial.similarity_score
            label = trial.ground_truth_label
            pred = 1 if score >= threshold else 0

            if pred != label:
                dist = abs(score - threshold)
                is_boundary = dist <= self.boundary_margin
                if is_boundary:
                    boundary_count += 1
                distances.append(dist)

                if label == 1:
                    # Genuine rejected
                    err_type = "false_rejection"
                    fr_speaker_counts[trial.actual_speaker_id] += 1
                else:
                    # Impostor accepted
                    err_type = "false_acceptance"
                    fa_impostor_counts[trial.actual_speaker_id] += 1

                record = SanitizedErrorRecord(
                    trial_id=trial.trial_id,
                    error_type=err_type,
                    claimed_speaker_id=trial.claimed_speaker_id,
                    actual_speaker_id=trial.actual_speaker_id,
                    similarity_score=score,
                    decision_threshold=threshold,
                    distance_to_threshold=dist,
                    is_boundary_case=is_boundary,
                )
                sanitized_errors.append(record)

        total_errs = len(sanitized_errors)
        total_trials = dataset.total_count
        err_pct = (total_errs / total_trials * 100.0) if total_trials > 0 else 0.0
        boundary_pct = (boundary_count / total_errs * 100.0) if total_errs > 0 else 0.0

        top_fr = [
            {"speaker_id": spk, "false_rejection_count": count}
            for spk, count in fr_speaker_counts.most_common(10)
        ]
        top_fa = [
            {"speaker_id": spk, "false_acceptance_count": count}
            for spk, count in fa_impostor_counts.most_common(10)
        ]

        prox_stats = {
            "mean_distance_to_threshold": float(np.mean(distances)) if distances else 0.0,
            "min_distance_to_threshold": float(np.min(distances)) if distances else 0.0,
            "max_distance_to_threshold": float(np.max(distances)) if distances else 0.0,
            "median_distance_to_threshold": float(np.median(distances)) if distances else 0.0,
        }

        n_fr = sum(1 for e in sanitized_errors if e.error_type == "false_rejection")
        n_fa = sum(1 for e in sanitized_errors if e.error_type == "false_acceptance")

        logger.info(
            f"[{dataset.split_name}] Error analysis at theta={threshold:.4f}: "
            f"{total_errs} errors ({n_fr} FR, {n_fa} FA), "
            f"{boundary_count} ({boundary_pct:.1f}%) within {self.boundary_margin} margin"
        )

        return ErrorAnalysisSummary(
            dataset_name=dataset.split_name,
            decision_threshold=threshold,
            total_trials=total_trials,
            total_errors=total_errs,
            error_rate_percent=err_pct,
            false_rejections_count=n_fr,
            false_acceptances_count=n_fa,
            boundary_errors_count=boundary_count,
            boundary_errors_percentage=boundary_pct,
            top_rejected_speakers=top_fr,
            top_accepted_impostors=top_fa,
            score_proximity_stats=prox_stats,
            sanitized_errors=sanitized_errors,
        )

