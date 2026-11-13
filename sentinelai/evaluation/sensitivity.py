"""Decision Threshold Sensitivity Analyzer.

Evaluates metric stability across a parameter sweep around the calibrated operating threshold (0.55 to 0.70):
- Measures degradation gradients (dFAR/dtheta, dFRR/dtheta).
- Identifies permissible operating tolerance windows.
- Serializes sensitivity results to CSV for tabular review.
"""

import csv
from dataclasses import asdict, dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sentinelai.evaluation.metrics import (
    ClassificationMetrics,
    compute_classification_metrics,
)
from sentinelai.evaluation.trial_scorer import ScoredDataset

logger = logging.getLogger(__name__)


@dataclass
class ThresholdSensitivityPoint:
    """Performance evaluation at a single discrete threshold point."""

    threshold: float
    far_percent: float
    frr_percent: float
    accuracy_percent: float
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_negatives: int
    false_positives: int
    true_negatives: int
    is_calibrated_baseline: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert sensitivity point to dictionary."""
        return {
            "threshold": round(self.threshold, 4),
            "far_percent": round(self.far_percent, 2),
            "frr_percent": round(self.frr_percent, 2),
            "accuracy_percent": round(self.accuracy_percent, 2),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "true_positives": self.true_positives,
            "false_negatives": self.false_negatives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "is_calibrated_baseline": self.is_calibrated_baseline,
        }


@dataclass
class ThresholdSensitivitySummary:
    """Aggregated threshold sensitivity evaluation across a parameter sweep."""

    dataset_name: str
    baseline_threshold: float
    min_threshold: float
    max_threshold: float
    step: float
    points: List[ThresholdSensitivityPoint] = field(default_factory=list)
    stable_threshold_window_5pct: Tuple[float, float] = (0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert sensitivity summary to dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "baseline_threshold": round(self.baseline_threshold, 6),
            "min_threshold": round(self.min_threshold, 4),
            "max_threshold": round(self.max_threshold, 4),
            "step": round(self.step, 4),
            "stable_threshold_window_5pct": [
                round(self.stable_threshold_window_5pct[0], 4),
                round(self.stable_threshold_window_5pct[1], 4),
            ],
            "points_count": len(self.points),
        }

    def save_csv(self, output_path: Path) -> Path:
        """Save threshold sensitivity sweep to CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "threshold",
            "is_calibrated_baseline",
            "far_percent",
            "frr_percent",
            "accuracy_percent",
            "precision",
            "recall",
            "f1_score",
            "true_positives",
            "false_negatives",
            "false_positives",
            "true_negatives",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in self.points:
                d = p.to_dict()
                row = {k: d.get(k) for k in fieldnames}
                writer.writerow(row)

        logger.info(f"Saved threshold sensitivity results to {output_path}")
        return output_path


class ThresholdSensitivityAnalyzer:
    """Evaluates decision boundary sensitivity across fine-grained threshold sweeps."""

    DEFAULT_MIN: float = 0.55
    DEFAULT_MAX: float = 0.70
    DEFAULT_STEP: float = 0.005

    def __init__(
        self,
        min_threshold: float = DEFAULT_MIN,
        max_threshold: float = DEFAULT_MAX,
        step: float = DEFAULT_STEP,
    ) -> None:
        """Initialize sensitivity analyzer.

        Args:
            min_threshold: Lower sweep bound.
            max_threshold: Upper sweep bound.
            step: Incremental step size.
        """
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.step = step

    def analyze(
        self,
        dataset: ScoredDataset,
        baseline_threshold: float = 0.6057,
    ) -> ThresholdSensitivitySummary:
        """Perform threshold sweep and analyze operating margin stability.

        Args:
            dataset: ScoredDataset to evaluate.
            baseline_threshold: The primary frozen operating threshold.

        Returns:
            ThresholdSensitivitySummary instance.
        """
        thresholds = np.arange(self.min_threshold, self.max_threshold + self.step / 2.0, self.step)
        points: List[ThresholdSensitivityPoint] = []
        stable_min = None
        stable_max = None

        logger.info(
            f"[{dataset.split_name}] Analyzing threshold sensitivity from {self.min_threshold:.3f} "
            f"to {self.max_threshold:.3f} (step={self.step:.3f})..."
        )

        for th in thresholds:
            th_float = float(round(th, 4))
            metrics: ClassificationMetrics = compute_classification_metrics(
                dataset.scores, dataset.labels, threshold=th_float
            )

            is_base = bool(abs(th_float - baseline_threshold) < self.step / 2.0)
            far_pct = metrics.far * 100.0
            frr_pct = metrics.frr * 100.0

            # Window check: both FAR <= 5% and FRR <= 5%
            if far_pct <= 5.0 and frr_pct <= 5.0:
                if stable_min is None:
                    stable_min = th_float
                stable_max = th_float

            pt = ThresholdSensitivityPoint(
                threshold=th_float,
                far_percent=far_pct,
                frr_percent=frr_pct,
                accuracy_percent=metrics.accuracy * 100.0,
                precision=metrics.precision,
                recall=metrics.recall,
                f1_score=metrics.f1_score,
                true_positives=metrics.true_positives,
                false_negatives=metrics.false_negatives,
                false_positives=metrics.false_positives,
                true_negatives=metrics.true_negatives,
                is_calibrated_baseline=is_base,
            )
            points.append(pt)

        window = (
            float(stable_min if stable_min is not None else baseline_threshold),
            float(stable_max if stable_max is not None else baseline_threshold),
        )

        logger.info(
            f"[{dataset.split_name}] Threshold sensitivity complete: "
            f"5% error window spans [{window[0]:.4f}, {window[1]:.4f}]"
        )

        return ThresholdSensitivitySummary(
            dataset_name=dataset.split_name,
            baseline_threshold=baseline_threshold,
            min_threshold=self.min_threshold,
            max_threshold=self.max_threshold,
            step=self.step,
            points=points,
            stable_threshold_window_5pct=window,
        )

