"""Evaluation Metrics and Error Rate Calculations for Speaker Verification.

Provides mathematically rigorous, vectorized calculations for:
- False Acceptance Rate (FAR) and False Rejection Rate (FRR) across threshold sweeps.
- Equal Error Rate (EER) with continuous linear interpolation.
- Receiver Operating Characteristic (ROC) coordinates and Area Under Curve (ROC-AUC).
- Detection Error Trade-off (DET) normal deviate coordinates via SciPy.
- Classification metrics: Accuracy, Precision, Recall, F1-Score, and Confusion Matrix.
"""

from dataclasses import asdict, dataclass, field
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

logger = logging.getLogger(__name__)


@dataclass
class FarFrrCurve:
    """FAR and FRR error trade-off curve across a sweep of decision thresholds.

    Attributes:
        thresholds: 1D float array of evaluated decision thresholds in ascending order.
        far: 1D float array of False Acceptance Rates corresponding to each threshold.
        frr: 1D float array of False Rejection Rates corresponding to each threshold.
    """

    thresholds: np.ndarray
    far: np.ndarray
    frr: np.ndarray

    def to_dict(self) -> Dict[str, List[float]]:
        """Serialize curve coordinates to a dictionary of lists."""
        return {
            "thresholds": self.thresholds.tolist(),
            "far": self.far.tolist(),
            "frr": self.frr.tolist(),
        }


@dataclass
class EERResult:
    """Equal Error Rate calculation result and operating point.

    Attributes:
        eer: Equal Error Rate as a float in [0.0, 1.0].
        eer_percent: Equal Error Rate expressed as a percentage (0.0% to 100.0%).
        eer_threshold: The calibrated decision threshold where FAR equals FRR.
        far_at_eer: FAR evaluated at the exact EER threshold.
        frr_at_eer: FRR evaluated at the exact EER threshold.
        method: Description of interpolation method used.
    """

    eer: float
    eer_percent: float
    eer_threshold: float
    far_at_eer: float
    frr_at_eer: float
    method: str = "linear_interpolation"

    def to_dict(self) -> Dict[str, Any]:
        """Convert EER result to JSON-serializable dictionary."""
        return {
            "eer": round(self.eer, 6),
            "eer_percent": round(self.eer_percent, 4),
            "eer_threshold": round(self.eer_threshold, 6),
            "far_at_eer": round(self.far_at_eer, 6),
            "frr_at_eer": round(self.frr_at_eer, 6),
            "method": self.method,
        }


@dataclass
class ClassificationMetrics:
    """Standard classification and verification performance metrics at a specific operating threshold.

    Decision Rule:
        MATCH when similarity_score >= threshold
        NO_MATCH when similarity_score < threshold

    Attributes:
        threshold: The operating threshold evaluated.
        far: False Acceptance Rate (FA / total_impostors).
        frr: False Rejection Rate (FR / total_genuines).
        accuracy: Overall classification accuracy (TP + TN) / total.
        precision: Positive Predictive Value: TP / (TP + FP).
        recall: True Positive Rate (Sensitivity): TP / (TP + FN) = 1 - FRR.
        specificity: True Negative Rate: TN / (TN + FP) = 1 - FAR.
        f1_score: Harmonic mean of precision and recall.
        true_positives: Count of correctly verified genuine trials.
        false_negatives: Count of genuine trials rejected (FR).
        false_positives: Count of impostor trials falsely accepted (FA).
        true_negatives: Count of correctly rejected impostor trials.
        genuine_count: Total genuine trials.
        impostor_count: Total impostor trials.
        total_trials: Total trials evaluated.
    """

    threshold: float
    far: float
    frr: float
    accuracy: float
    precision: float
    recall: float
    specificity: float
    f1_score: float
    true_positives: int
    false_negatives: int
    false_positives: int
    true_negatives: int
    genuine_count: int
    impostor_count: int
    total_trials: int

    def confusion_matrix(self) -> List[List[int]]:
        """Return 2x2 confusion matrix [[TN, FP], [FN, TP]]."""
        return [
            [self.true_negatives, self.false_positives],
            [self.false_negatives, self.true_positives],
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a JSON-serializable dictionary."""
        return {
            "threshold": round(self.threshold, 6),
            "far": round(self.far, 6),
            "frr": round(self.frr, 6),
            "accuracy": round(self.accuracy, 6),
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "specificity": round(self.specificity, 6),
            "f1_score": round(self.f1_score, 6),
            "confusion_matrix": {
                "true_positives": self.true_positives,
                "false_negatives": self.false_negatives,
                "false_positives": self.false_positives,
                "true_negatives": self.true_negatives,
            },
            "trial_counts": {
                "genuine_trials": self.genuine_count,
                "impostor_trials": self.impostor_count,
                "total_trials": self.total_trials,
            },
        }


def _validate_score_arrays(
    scores: np.ndarray, labels: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Validate numerical integrity and shape alignment of score and label arrays.

    Args:
        scores: 1D array of scalar float similarity scores.
        labels: 1D array of binary ground-truth labels (1 for genuine, 0 for impostor).

    Returns:
        Tuple of (clean_scores_float64, clean_labels_int).

    Raises:
        ValueError: If arrays are empty, length mismatched, contain non-finite numbers,
                    or do not contain both genuine and impostor labels.
    """
    scores_arr = np.asarray(scores, dtype=np.float64).ravel()
    labels_arr = np.asarray(labels, dtype=np.int64).ravel()

    if scores_arr.size == 0 or labels_arr.size == 0:
        raise ValueError("Scores and labels arrays cannot be empty.")

    if scores_arr.shape[0] != labels_arr.shape[0]:
        raise ValueError(
            f"Shape mismatch: scores has {scores_arr.shape[0]} elements, "
            f"labels has {labels_arr.shape[0]} elements."
        )

    if not np.isfinite(scores_arr).all():
        raise ValueError("Scores array contains non-finite values (NaN or Inf).")

    unique_labels = set(np.unique(labels_arr))
    if not unique_labels.issubset({0, 1}):
        raise ValueError(
            f"Labels must contain only 0 (impostor) and 1 (genuine), found {unique_labels}."
        )

    if 0 not in unique_labels or 1 not in unique_labels:
        raise ValueError(
            "Evaluation requires both genuine (1) and impostor (0) trials. "
            f"Found only labels: {unique_labels}."
        )

    return scores_arr, labels_arr


def compute_far_frr_curve(
    scores: np.ndarray,
    labels: np.ndarray,
    num_thresholds: int = 2000,
) -> FarFrrCurve:
    """Compute FAR and FRR across a finely spaced grid of decision thresholds.

    Decision Rule:
        Score >= threshold => MATCH (1)
        Score <  threshold => NO_MATCH (0)

    Args:
        scores: 1D array of similarity scores.
        labels: 1D array of ground-truth binary labels (1=genuine, 0=impostor).
        num_thresholds: Number of evaluation points between min and max scores.

    Returns:
        FarFrrCurve containing thresholds, far, and frr arrays.
    """
    clean_scores, clean_labels = _validate_score_arrays(scores, labels)

    genuine_mask = clean_labels == 1
    impostor_mask = clean_labels == 0

    genuine_scores = clean_scores[genuine_mask]
    impostor_scores = clean_scores[impostor_mask]

    n_gen = float(len(genuine_scores))
    n_imp = float(len(impostor_scores))

    # Evaluate across a broad threshold sweep encompassing score range plus margins
    min_score = max(-1.0, float(np.min(clean_scores)) - 0.05)
    max_score = min(1.0, float(np.max(clean_scores)) + 0.05)

    thresholds = np.linspace(min_score, max_score, num_thresholds, dtype=np.float64)

    # Vectorized error rate computation:
    # Impostors falsely accepted: impostor_score >= threshold
    # Genuines falsely rejected: genuine_score < threshold
    # Utilizing broadcasting or searchsorted for high efficiency
    sorted_imp = np.sort(impostor_scores)
    sorted_gen = np.sort(genuine_scores)

    # For impostors: count where score >= t => len - searchsorted(sorted_imp, t, side='left')
    imp_accepted = len(sorted_imp) - np.searchsorted(sorted_imp, thresholds, side="left")
    far = imp_accepted / n_imp

    # For genuines: count where score < t => searchsorted(sorted_gen, t, side='left')
    gen_rejected = np.searchsorted(sorted_gen, thresholds, side="left")
    frr = gen_rejected / n_gen

    return FarFrrCurve(thresholds=thresholds, far=far, frr=frr)


def compute_eer(
    scores: np.ndarray,
    labels: np.ndarray,
    num_thresholds: int = 10000,
) -> EERResult:
    r"""Compute the Equal Error Rate (EER) and operating threshold via linear interpolation.

    Mathematical Method:
        1. Sweep thresholds $\theta \in [\min(s) - \epsilon, \max(s) + \epsilon]$.
        2. As threshold $\theta$ increases:
           - Impostor acceptances decrease: $\text{FAR}(\theta)$ is non-increasing.
           - Genuine rejections increase: $\text{FRR}(\theta)$ is non-decreasing.
        3. Identify bracket indices $i$ and $i+1$ where curves intersect:
           $\text{FAR}[i] \ge \text{FRR}[i]$ and $\text{FAR}[i+1] \le \text{FRR}[i+1]$.
        4. Apply linear interpolation between the bracket points:
           $$\alpha = \frac{\text{FAR}[i] - \text{FRR}[i]}{(\text{FAR}[i] - \text{FAR}[i+1]) + (\text{FRR}[i+1] - \text{FRR}[i])}$$
           $$\theta_{\text{EER}} = \theta[i] + \alpha (\theta[i+1] - \theta[i])$$
           $$\text{EER} = \text{FAR}[i] + \alpha (\text{FAR}[i+1] - \text{FAR}[i])$$

    Args:
        scores: 1D array of similarity scores in [-1.0, 1.0].
        labels: 1D array of binary ground-truth labels (1=genuine, 0=impostor).
        num_thresholds: Fine-grid resolution for bracket identification.

    Returns:
        EERResult with eer, eer_percent, eer_threshold, and error rates at operating point.
    """
    curve = compute_far_frr_curve(scores, labels, num_thresholds=num_thresholds)
    thresholds = curve.thresholds
    far = curve.far
    frr = curve.frr

    # Case: Perfect separation (zero overlap between genuine and impostor distributions)
    if np.max(scores[labels == 0]) < np.min(scores[labels == 1]):
        # Any threshold between max(impostor) and min(genuine) gives EER = 0.0
        sep_threshold = float(
            (np.max(scores[labels == 0]) + np.min(scores[labels == 1])) / 2.0
        )
        return EERResult(
            eer=0.0,
            eer_percent=0.0,
            eer_threshold=sep_threshold,
            far_at_eer=0.0,
            frr_at_eer=0.0,
            method="perfect_separation_midpoint",
        )

    # Locate crossing point: difference D = FAR - FRR goes from positive to negative
    diff = far - frr

    # Find the first index where FAR <= FRR (diff <= 0)
    indices = np.where(diff <= 0)[0]
    if len(indices) == 0:
        # Curve never crosses (degenerate distribution); take minimum absolute difference
        idx = int(np.argmin(np.abs(diff)))
        eer_val = float((far[idx] + frr[idx]) / 2.0)
        return EERResult(
            eer=eer_val,
            eer_percent=eer_val * 100.0,
            eer_threshold=float(thresholds[idx]),
            far_at_eer=float(far[idx]),
            frr_at_eer=float(frr[idx]),
            method="discrete_minimum_difference",
        )

    idx_high = int(indices[0])

    if idx_high == 0:
        # Crosses immediately at the lower bound
        eer_val = float((far[0] + frr[0]) / 2.0)
        return EERResult(
            eer=eer_val,
            eer_percent=eer_val * 100.0,
            eer_threshold=float(thresholds[0]),
            far_at_eer=float(far[0]),
            frr_at_eer=float(frr[0]),
            method="lower_boundary_crossing",
        )

    idx_low = idx_high - 1

    # Linear interpolation between idx_low and idx_high
    far_low, far_high = far[idx_low], far[idx_high]
    frr_low, frr_high = frr[idx_low], frr[idx_high]
    th_low, th_high = thresholds[idx_low], thresholds[idx_high]

    denominator = (far_low - far_high) + (frr_high - frr_low)
    if denominator > 0:
        alpha = (far_low - frr_low) / denominator
        alpha = float(np.clip(alpha, 0.0, 1.0))
        eer_threshold = th_low + alpha * (th_high - th_low)
        eer_val = far_low + alpha * (far_high - far_low)
    else:
        eer_threshold = (th_low + th_high) / 2.0
        eer_val = (far_low + frr_low) / 2.0

    eer_val = float(np.clip(eer_val, 0.0, 1.0))
    eer_percent = float(eer_val * 100.0)

    return EERResult(
        eer=eer_val,
        eer_percent=eer_percent,
        eer_threshold=float(eer_threshold),
        far_at_eer=eer_val,
        frr_at_eer=eer_val,
        method="linear_interpolation",
    )


def compute_roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Calculate Area Under the Receiver Operating Characteristic Curve (ROC-AUC).

    Args:
        scores: 1D array of similarity scores.
        labels: 1D array of binary ground-truth labels (1=genuine, 0=impostor).

    Returns:
        ROC-AUC float in range [0.0, 1.0].
    """
    clean_scores, clean_labels = _validate_score_arrays(scores, labels)
    try:
        auc = float(roc_auc_score(clean_labels, clean_scores))
        return round(auc, 6)
    except Exception as exc:
        logger.warning(f"roc_auc_score failed, computing via trapezoidal rule: {exc}")
        curve = compute_far_frr_curve(clean_scores, clean_labels, num_thresholds=5000)
        fpr = curve.far  # FAR = FPR
        tpr = 1.0 - curve.frr  # 1 - FRR = TPR
        # Sort by FPR ascending for numerical integration
        sort_idx = np.argsort(fpr)
        auc = float(np.trapezoid(tpr[sort_idx], fpr[sort_idx]))
        return round(float(np.clip(auc, 0.0, 1.0)), 6)


def compute_classification_metrics(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
) -> ClassificationMetrics:
    """Compute complete classification metrics at a given operating decision threshold.

    Decision Rule:
        Score >= threshold => MATCH (1)
        Score <  threshold => NO_MATCH (0)

    Args:
        scores: 1D array of similarity scores.
        labels: 1D array of binary ground-truth labels (1=genuine, 0=impostor).
        threshold: The operating threshold float.

    Returns:
        ClassificationMetrics instance with precision, recall, F1, FAR, FRR, and confusion matrix.
    """
    clean_scores, clean_labels = _validate_score_arrays(scores, labels)

    predictions = (clean_scores >= threshold).astype(np.int64)

    tp = int(np.sum((predictions == 1) & (clean_labels == 1)))
    fn = int(np.sum((predictions == 0) & (clean_labels == 1)))
    fp = int(np.sum((predictions == 1) & (clean_labels == 0)))
    tn = int(np.sum((predictions == 0) & (clean_labels == 0)))

    n_gen = tp + fn
    n_imp = tn + fp
    total = n_gen + n_imp

    far = float(fp / n_imp) if n_imp > 0 else 0.0
    frr = float(fn / n_gen) if n_gen > 0 else 0.0
    accuracy = float((tp + tn) / total) if total > 0 else 0.0
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / n_gen) if n_gen > 0 else 0.0  # Equivalent to 1 - FRR
    specificity = float(tn / n_imp) if n_imp > 0 else 0.0  # Equivalent to 1 - FAR

    if precision + recall > 0:
        f1 = float(2.0 * (precision * recall) / (precision + recall))
    else:
        f1 = 0.0

    return ClassificationMetrics(
        threshold=float(threshold),
        far=far,
        frr=frr,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        specificity=specificity,
        f1_score=f1,
        true_positives=tp,
        false_negatives=fn,
        false_positives=fp,
        true_negatives=tn,
        genuine_count=n_gen,
        impostor_count=n_imp,
        total_trials=total,
    )


def compute_det_coordinates(
    far: np.ndarray,
    frr: np.ndarray,
    eps: float = 1e-4,
) -> Tuple[np.ndarray, np.ndarray]:
    """Transform FAR and FRR into normal deviate coordinates for Detection Error Trade-off (DET) plots.

    Using probit link function: x = Norm_ppf(FAR), y = Norm_ppf(FRR).

    Args:
        far: 1D array of False Acceptance Rates.
        frr: 1D array of False Rejection Rates.
        eps: Bounds clipping to prevent infinite asymptotes at 0.0 and 1.0.

    Returns:
        Tuple of (deviate_far, deviate_frr).
    """
    clipped_far = np.clip(far, eps, 1.0 - eps)
    clipped_frr = np.clip(frr, eps, 1.0 - eps)

    dev_far = norm.ppf(clipped_far)
    dev_frr = norm.ppf(clipped_frr)

    return dev_far, dev_frr
