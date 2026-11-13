"""Confidence Interval Data Models and Calculators for Biometric Verification.

Provides structured containers and statistical functions to compute empirical
percentile-based confidence intervals (mean, standard error, median, 2.5th and 97.5th percentiles)
for biometric verification performance metrics.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MetricConfidenceInterval:
    """Empirical confidence interval summary for a single performance metric.

    Attributes:
        metric_name: Name of the evaluated metric (e.g. 'far', 'frr', 'eer', 'accuracy').
        point_estimate: Primary baseline measured value.
        mean: Sample mean across bootstrap replicates.
        median: Sample median (50th percentile) across bootstrap replicates.
        std_err: Standard error (standard deviation across bootstrap replicates).
        ci_lower: Lower bound of the two-sided 95% confidence interval (2.5th percentile).
        ci_upper: Upper bound of the two-sided 95% confidence interval (97.5th percentile).
        confidence_level: Nominal confidence level (default: 0.95 for 95% CI).
    """

    metric_name: str
    point_estimate: float
    mean: float
    median: float
    std_err: float
    ci_lower: float
    ci_upper: float
    confidence_level: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        """Serialize confidence interval summary to a dictionary with rounded values."""
        return {
            "metric_name": self.metric_name,
            "point_estimate": round(self.point_estimate, 6),
            "mean": round(self.mean, 6),
            "median": round(self.median, 6),
            "std_err": round(self.std_err, 6),
            "ci_lower": round(self.ci_lower, 6),
            "ci_upper": round(self.ci_upper, 6),
            "confidence_level": self.confidence_level,
            "formatted_ci_95": f"[{self.ci_lower * 100:.2f}%, {self.ci_upper * 100:.2f}%]"
            if "percent" in self.metric_name or self.point_estimate <= 1.0
            else f"[{self.ci_lower:.4f}, {self.ci_upper:.4f}]",
        }


@dataclass
class EvaluationConfidenceIntervals:
    """Aggregated container holding confidence intervals for all evaluated biometric metrics.

    Attributes:
        dataset_name: Identifier of the evaluated partition (e.g. 'test-clean').
        resampling_unit: The cluster unit used for resampling (e.g. 'speaker_cluster').
        iterations: Number of bootstrap replicates evaluated.
        valid_replicates: Count of replicates successfully calculated without degeneration.
        metrics: Dictionary mapping metric name to MetricConfidenceInterval instance.
        metadata: Diagnostic metadata regarding resampling protocol and assumptions.
    """

    dataset_name: str
    resampling_unit: str
    iterations: int
    valid_replicates: int
    metrics: Dict[str, MetricConfidenceInterval] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert container to JSON-serializable dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "resampling_unit": self.resampling_unit,
            "iterations": self.iterations,
            "valid_replicates": self.valid_replicates,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "metadata": self.metadata,
        }

    def save_json(self, output_path: Path) -> Path:
        """Save confidence intervals to a formatted JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved confidence intervals to {output_path}")
        return output_path


def compute_metric_confidence_interval(
    metric_name: str,
    point_estimate: float,
    replicates: Union[List[float], np.ndarray],
    confidence_level: float = 0.95,
) -> MetricConfidenceInterval:
    """Calculate empirical percentile confidence interval from bootstrap replicate samples.

    Formula:
        Lower bound: empirical percentile at (1 - confidence_level) / 2 = 2.5%
        Upper bound: empirical percentile at 1 - (1 - confidence_level) / 2 = 97.5%

    Args:
        metric_name: Name of the biometric metric.
        point_estimate: Primary baseline observed value.
        replicates: 1D array or list of scalar replicate values.
        confidence_level: Two-sided confidence level in (0, 1) (default: 0.95).

    Returns:
        MetricConfidenceInterval instance.

    Raises:
        ValueError: If replicates array is empty, non-finite, or confidence_level is invalid.
    """
    arr = np.asarray(replicates, dtype=np.float64).ravel()
    if arr.size == 0:
        raise ValueError(f"Replicates array for '{metric_name}' cannot be empty.")

    if not np.isfinite(arr).all():
        raise ValueError(f"Replicates array for '{metric_name}' contains non-finite values (NaN or Inf).")

    if not (0.0 < confidence_level < 1.0):
        raise ValueError(f"confidence_level must be in (0, 1), got {confidence_level}.")

    alpha = (1.0 - confidence_level) / 2.0
    lower_pct = alpha * 100.0
    upper_pct = (1.0 - alpha) * 100.0

    mean_val = float(np.mean(arr))
    median_val = float(np.median(arr))
    std_err = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0

    ci_lower = float(np.percentile(arr, lower_pct))
    ci_upper = float(np.percentile(arr, upper_pct))

    return MetricConfidenceInterval(
        metric_name=metric_name,
        point_estimate=float(point_estimate),
        mean=mean_val,
        median=median_val,
        std_err=std_err,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        confidence_level=confidence_level,
    )

