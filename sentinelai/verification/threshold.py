"""Verification Threshold Engine and Calibration Abstraction.

Implements configurable thresholding for speaker verification decisions with
version tracking, boundary validation, and scientific disclaimers.
"""

from typing import Any, Dict, Optional
from sentinelai.verification.exceptions import ThresholdValidationError


class VerificationThreshold:
    """Configurable decision threshold manager for speaker verification.

    SCIENTIFIC NOTE & RESEARCH BOUNDARY:
        Cosine similarity values range from -1.0 to +1.0. A development threshold
        (e.g., 0.65) is provided strictly for end-to-end software integration testing.
        It is NOT scientifically validated for production authentication or across
        untested human demographic cohorts. Production deployment requires empirical
        threshold calibration (e.g. Equal Error Rate or target FAR/FRR optimization)
        on a dedicated, unseen development dataset prior to deployment.
    """

    MIN_THRESHOLD: float = -1.0
    MAX_THRESHOLD: float = 1.0
    DEFAULT_DEV_THRESHOLD: float = 0.65
    DEFAULT_DEV_VERSION: str = "dev-uncalibrated-v1.0"

    def __init__(
        self,
        threshold_value: float = DEFAULT_DEV_THRESHOLD,
        version: str = DEFAULT_DEV_VERSION,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize and validate the verification threshold.

        Args:
            threshold_value: Scalar cutoff in [-1.0, 1.0]. A score >= threshold_value is a MATCH.
            version: Unique identifier for the threshold calibration model/version.
            description: Human-readable description of calibration source or intent.
            metadata: Additional metadata (e.g., target FAR/FRR, calibration dataset info).

        Raises:
            ThresholdValidationError: If threshold_value is outside [-1.0, 1.0] or non-finite.
        """
        self._validate_threshold(threshold_value)
        self.threshold_value = float(threshold_value)
        self.version = str(version).strip()
        if not self.version:
            raise ThresholdValidationError("Threshold version identifier cannot be empty.")
        self.description = description or "Development uncalibrated threshold for software pipeline validation."
        self.metadata = metadata or {}

    @classmethod
    def _validate_threshold(cls, value: float) -> None:
        """Ensure threshold is a finite float within [-1.0, 1.0]."""
        if not isinstance(value, (int, float)):
            raise ThresholdValidationError(
                f"Threshold value must be a numeric float, got {type(value).__name__}."
            )
        if isinstance(value, float) and (value != value or abs(value) == float("inf")):
            raise ThresholdValidationError("Threshold value must be a finite numerical number.")
        if value < cls.MIN_THRESHOLD or value > cls.MAX_THRESHOLD:
            raise ThresholdValidationError(
                f"Threshold value {value:.4f} is out of valid bounds "
                f"[{cls.MIN_THRESHOLD:.1f}, {cls.MAX_THRESHOLD:.1f}]."
            )

    def is_match(self, similarity_score: float) -> bool:
        """Evaluate whether a similarity score meets or exceeds the threshold.

        Args:
            similarity_score: Cosine similarity score in [-1.0, 1.0].

        Returns:
            True if similarity_score >= threshold_value, False otherwise.
        """
        return similarity_score >= self.threshold_value

    def to_dict(self) -> Dict[str, Any]:
        """Return a structured summary of the threshold configuration."""
        return {
            "threshold_value": self.threshold_value,
            "version": self.version,
            "description": self.description,
            "is_calibrated": not self.version.startswith("dev-"),
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"VerificationThreshold(value={self.threshold_value:.4f}, "
            f"version='{self.version}', calibrated={not self.version.startswith('dev-')})"
        )

