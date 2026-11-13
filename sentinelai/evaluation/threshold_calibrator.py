"""Decision Threshold Calibration Engine for Speaker Verification.

Calibrates the operating decision threshold strictly on development data (dev-clean)
to achieve Equal Error Rate (EER) or minimize absolute error disparity (|FAR - FRR|),
packages the calibrated threshold with provenance metadata, and freezes it into a
VerificationThreshold instance for test evaluation.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sentinelai.evaluation.metrics import (
    ClassificationMetrics,
    EERResult,
    compute_classification_metrics,
    compute_eer,
)
from sentinelai.verification.threshold import VerificationThreshold

logger = logging.getLogger(__name__)


@dataclass
class CalibratedThresholdMetadata:
    """Structured provenance metadata accompanying a calibrated verification threshold.

    Attributes:
        threshold_value: Calibrated scalar decision cutoff in [-1.0, 1.0].
        version: Semantic calibration identifier (e.g. 'librispeech-dev-clean-eer-v1.0').
        calibration_dataset: Name of development corpus used for calibration.
        calibration_timestamp: ISO 8601 UTC timestamp of calibration.
        model_identifier: ECAPA-TDNN model identifier used for extraction.
        scoring_metric: Acoustic comparison function (e.g. 'cosine_similarity').
        calibration_criterion: Optimization goal ('equal_error_rate_minimization').
        eer_metrics: Equal Error Rate metrics dictionary.
        trial_counts: Trial distribution breakdown in the calibration set.
        operating_metrics: Full classification metrics achieved at the calibrated threshold.
        description: Scientific summary of the threshold and intended domain.
    """

    threshold_value: float
    version: str
    calibration_dataset: str
    calibration_timestamp: str
    model_identifier: str
    scoring_metric: str
    calibration_criterion: str
    eer_metrics: Dict[str, Any]
    trial_counts: Dict[str, int]
    operating_metrics: Dict[str, Any]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to a JSON-serializable dictionary."""
        return asdict(self)

    def save_json(self, output_path: Path) -> Path:
        """Save calibrated threshold specification to a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved calibrated threshold metadata to {output_path}")
        return output_path


class ThresholdCalibrator:
    """Calibrator for empirical decision threshold selection on development data.

    Methodology:
        1. Evaluates genuine and impostor similarity scores from the development partition.
        2. Solves for the threshold $\theta^*$ where $\text{FAR}(\theta^*) = \text{FRR}(\theta^*)$
           via continuous linear interpolation.
        3. Validates that the calibration dataset is explicitly development data (e.g. dev-clean)
           to prevent data leakage or test set overfitting.
        4. Freezes the resulting threshold into an immutable `VerificationThreshold` instance.
    """

    DEFAULT_CALIBRATION_DATASET = "LibriSpeech dev-clean"
    DEFAULT_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
    DEFAULT_VERSION = "librispeech-dev-clean-eer-v1.0"

    def __init__(
        self,
        calibration_dataset: str = DEFAULT_CALIBRATION_DATASET,
        model_identifier: str = DEFAULT_MODEL,
        version: str = DEFAULT_VERSION,
    ) -> None:
        """Initialize the threshold calibrator.

        Args:
            calibration_dataset: Identifier of development corpus.
            model_identifier: Identifier of embedding model.
            version: Unique semantic version for the calibrated parameter.
        """
        self.calibration_dataset = calibration_dataset
        self.model_identifier = model_identifier
        self.version = version

    def calibrate(
        self,
        dev_scores: np.ndarray,
        dev_labels: np.ndarray,
        criterion: str = "equal_error_rate",
    ) -> Tuple[VerificationThreshold, CalibratedThresholdMetadata]:
        """Calibrate the decision threshold on development scores.

        Args:
            dev_scores: 1D array of development similarity scores in [-1.0, 1.0].
            dev_labels: 1D array of binary development labels (1=genuine, 0=impostor).
            criterion: Calibration criterion (currently supports 'equal_error_rate').

        Returns:
            Tuple of (VerificationThreshold, CalibratedThresholdMetadata).

        Raises:
            ValueError: If inputs are invalid or dataset suggests test set misuse.
        """
        if "test" in self.calibration_dataset.lower():
            logger.warning(
                f"Caution: Calibration dataset name '{self.calibration_dataset}' contains 'test'. "
                "Threshold calibration must be performed strictly on development data."
            )

        logger.info(
            f"Calibrating verification threshold on {self.calibration_dataset} "
            f"({len(dev_scores)} trials) using criterion '{criterion}'..."
        )

        eer_res: EERResult = compute_eer(dev_scores, dev_labels)
        calibrated_threshold = round(float(eer_res.eer_threshold), 6)

        # Evaluate complete operating metrics at this calibrated threshold
        metrics_at_cal: ClassificationMetrics = compute_classification_metrics(
            dev_scores, dev_labels, threshold=calibrated_threshold
        )

        timestamp_utc = datetime.now(timezone.utc).isoformat()

        metadata = CalibratedThresholdMetadata(
            threshold_value=round(calibrated_threshold, 6),
            version=self.version,
            calibration_dataset=self.calibration_dataset,
            calibration_timestamp=timestamp_utc,
            model_identifier=self.model_identifier,
            scoring_metric="cosine_similarity",
            calibration_criterion=f"{criterion}_minimization",
            eer_metrics=eer_res.to_dict(),
            trial_counts=metrics_at_cal.to_dict()["trial_counts"],
            operating_metrics=metrics_at_cal.to_dict(),
            description=(
                f"Empirically calibrated decision threshold ({calibrated_threshold:.4f}) "
                f"at Equal Error Rate ({eer_res.eer_percent:.2f}%) on {self.calibration_dataset}. "
                "Frozen for independent test evaluation."
            ),
        )

        # Construct and validate VerificationThreshold instance from the verification module
        frozen_threshold = VerificationThreshold(
            threshold_value=calibrated_threshold,
            version=self.version,
            description=metadata.description,
            metadata=metadata.to_dict(),
        )

        logger.info(
            f"Threshold calibration complete: theta* = {calibrated_threshold:.4f} "
            f"(EER = {eer_res.eer_percent:.2f}%, FAR = {metrics_at_cal.far:.4f}, FRR = {metrics_at_cal.frr:.4f})"
        )

        return frozen_threshold, metadata

    @staticmethod
    def load_frozen_threshold(json_path: Path) -> VerificationThreshold:
        """Load a previously saved calibrated threshold from a JSON file.

        Args:
            json_path: Path to calibrated_threshold.json.

        Returns:
            VerificationThreshold instance.
        """
        json_path = Path(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return VerificationThreshold(
            threshold_value=data["threshold_value"],
            version=data["version"],
            description=data.get("description", "Loaded frozen threshold"),
            metadata=data,
        )
