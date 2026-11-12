"""Unit and Integration Tests for Phase 5C: Threshold Calibration and Performance Analysis.

Uses mocked score arrays and synthetic fixtures (no external downloads or model loading)
to verify:
- Cosine score generation and manifest serialization.
- Genuine and impostor trial scoring.
- FAR and FRR monotonic behavior across threshold sweeps.
- Equal Error Rate (EER) continuous interpolation.
- ROC-AUC trapezoidal integration.
- Operating threshold calibration on development data.
- Strict threshold freezing (test evaluation does not alter calibrated threshold).
- Classification metrics (Precision, Recall, F1, Accuracy, Confusion Matrix).
- Numerical validation: NaN, Inf, empty arrays, single-class trials.
- Missing embeddings or malformed input error handling.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pytest

from sentinelai.evaluation.metrics import (
    ClassificationMetrics,
    EERResult,
    FarFrrCurve,
    compute_classification_metrics,
    compute_det_coordinates,
    compute_eer,
    compute_far_frr_curve,
    compute_roc_auc,
)
from sentinelai.evaluation.threshold_calibrator import (
    CalibratedThresholdMetadata,
    ThresholdCalibrator,
)
from sentinelai.evaluation.trial_scorer import (
    ScoredDataset,
    ScoredTrial,
    TrialScorer,
)
from sentinelai.evaluation.visualizer import EvaluationVisualizer
from sentinelai.verification.threshold import VerificationThreshold


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_scores() -> Tuple[np.ndarray, np.ndarray]:
    """Generate known synthetic score distribution with controlled overlap.

    Genuine scores: mean=0.80, std=0.08
    Impostor scores: mean=0.40, std=0.08
    """
    rng = np.random.default_rng(42)
    n_gen = 500
    n_imp = 500
    gen_scores = rng.normal(loc=0.80, scale=0.08, size=n_gen)
    imp_scores = rng.normal(loc=0.40, scale=0.08, size=n_imp)

    gen_scores = np.clip(gen_scores, -1.0, 1.0)
    imp_scores = np.clip(imp_scores, -1.0, 1.0)

    scores = np.concatenate([gen_scores, imp_scores])
    labels = np.concatenate([np.ones(n_gen, dtype=np.int64), np.zeros(n_imp, dtype=np.int64)])
    return scores, labels


@pytest.fixture
def perfect_separation_scores() -> Tuple[np.ndarray, np.ndarray]:
    """Scores with zero overlap between genuine (0.7-0.9) and impostor (0.1-0.3)."""
    gen = np.array([0.70, 0.75, 0.80, 0.85, 0.90], dtype=np.float64)
    imp = np.array([0.10, 0.15, 0.20, 0.25, 0.30], dtype=np.float64)
    scores = np.concatenate([gen, imp])
    labels = np.concatenate([np.ones(len(gen), dtype=np.int64), np.zeros(len(imp), dtype=np.int64)])
    return scores, labels


# ---------------------------------------------------------------------------
# 1. FAR, FRR, and Monotonicity Tests
# ---------------------------------------------------------------------------


class TestFarFrrCurve:
    """Tests for FAR and FRR computation over threshold sweeps."""

    def test_far_and_frr_monotonicity(self, synthetic_scores: Tuple[np.ndarray, np.ndarray]) -> None:
        """Verify FAR decreases monotonically and FRR increases monotonically with threshold."""
        scores, labels = synthetic_scores
        curve = compute_far_frr_curve(scores, labels, num_thresholds=200)

        # FAR should be non-increasing as threshold increases
        far_diffs = np.diff(curve.far)
        assert np.all(far_diffs <= 1e-9), "FAR must decrease as threshold increases"

        # FRR should be non-decreasing as threshold increases
        frr_diffs = np.diff(curve.frr)
        assert np.all(frr_diffs >= -1e-9), "FRR must increase as threshold increases"

    def test_far_frr_boundary_conditions(self, synthetic_scores: Tuple[np.ndarray, np.ndarray]) -> None:
        """Verify extreme boundary conditions: low threshold => FAR~1, FRR~0; high => FAR~0, FRR~1."""
        scores, labels = synthetic_scores
        curve = compute_far_frr_curve(scores, labels, num_thresholds=100)

        # At the lowest threshold, almost all impostors accepted, no genuines rejected
        assert curve.far[0] >= 0.99
        assert curve.frr[0] <= 0.01

        # At the highest threshold, almost all genuines rejected, no impostors accepted
        assert curve.far[-1] <= 0.01
        assert curve.frr[-1] >= 0.99

    def test_empty_scores_raises_value_error(self) -> None:
        """Verify empty score array raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            compute_far_frr_curve(np.array([]), np.array([]))

    def test_shape_mismatch_raises_value_error(self) -> None:
        """Verify mismatched array lengths raise ValueError."""
        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_far_frr_curve(np.array([0.5, 0.6]), np.array([1]))

    def test_non_finite_scores_raises_value_error(self) -> None:
        """Verify NaN or Inf in scores raises ValueError."""
        with pytest.raises(ValueError, match="non-finite"):
            compute_far_frr_curve(np.array([0.5, np.nan]), np.array([1, 0]))

        with pytest.raises(ValueError, match="non-finite"):
            compute_far_frr_curve(np.array([0.5, np.inf]), np.array([1, 0]))

    def test_single_class_raises_value_error(self) -> None:
        """Verify arrays with only genuines or only impostors raise ValueError."""
        with pytest.raises(ValueError, match="both genuine"):
            compute_far_frr_curve(np.array([0.5, 0.6]), np.array([1, 1]))


# ---------------------------------------------------------------------------
# 2. Equal Error Rate (EER) Tests
# ---------------------------------------------------------------------------


class TestEERComputation:
    """Tests for Equal Error Rate calculation and linear interpolation."""

    def test_perfect_separation_gives_zero_eer(
        self, perfect_separation_scores: Tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Verify that perfectly separated distributions yield EER = 0.0%."""
        scores, labels = perfect_separation_scores
        eer_res = compute_eer(scores, labels)

        assert eer_res.eer == 0.0
        assert eer_res.eer_percent == 0.0
        # Optimal threshold should be between max(imp)=0.30 and min(gen)=0.70
        assert 0.30 <= eer_res.eer_threshold <= 0.70

    def test_synthetic_eer_operating_point(
        self, synthetic_scores: Tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Verify EER calculation on realistic synthetic distributions."""
        scores, labels = synthetic_scores
        eer_res = compute_eer(scores, labels)

        # For N(0.8, 0.08) and N(0.4, 0.08), the midpoint is 0.60
        assert 0.55 <= eer_res.eer_threshold <= 0.65
        assert 0.0 <= eer_res.eer <= 0.05
        assert pytest.approx(eer_res.far_at_eer, abs=0.01) == eer_res.frr_at_eer

    def test_eer_result_serialization(self) -> None:
        """Verify EERResult converts to dict properly."""
        res = EERResult(
            eer=0.023456,
            eer_percent=2.35,
            eer_threshold=0.623456,
            far_at_eer=0.023456,
            frr_at_eer=0.023456,
        )
        d = res.to_dict()
        assert d["eer"] == 0.023456
        assert d["eer_percent"] == 2.35
        assert d["method"] == "linear_interpolation"


# ---------------------------------------------------------------------------
# 3. ROC-AUC Tests
# ---------------------------------------------------------------------------


class TestRocAucComputation:
    """Tests for ROC-AUC metric calculation."""

    def test_perfect_separation_gives_auc_one(
        self, perfect_separation_scores: Tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Verify perfect separation yields ROC-AUC = 1.0."""
        scores, labels = perfect_separation_scores
        auc = compute_roc_auc(scores, labels)
        assert auc == 1.0

    def test_synthetic_auc_value(
        self, synthetic_scores: Tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Verify ROC-AUC on overlapping distributions is well within [0.5, 1.0]."""
        scores, labels = synthetic_scores
        auc = compute_roc_auc(scores, labels)
        assert 0.95 <= auc <= 1.0


# ---------------------------------------------------------------------------
# 4. Classification Metrics Tests
# ---------------------------------------------------------------------------


class TestClassificationMetrics:
    """Tests for precision, recall, F1, accuracy, and confusion matrix."""

    def test_classification_metrics_at_threshold(
        self, synthetic_scores: Tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Verify classification metrics consistency at threshold 0.60."""
        scores, labels = synthetic_scores
        metrics = compute_classification_metrics(scores, labels, threshold=0.60)

        assert metrics.genuine_count == 500
        assert metrics.impostor_count == 500
        assert metrics.total_trials == 1000

        # Sum of confusion matrix elements must equal total trials
        assert (
            metrics.true_positives
            + metrics.false_negatives
            + metrics.false_positives
            + metrics.true_negatives
        ) == 1000

        # Accuracy formula check
        expected_acc = (metrics.true_positives + metrics.true_negatives) / 1000.0
        assert pytest.approx(metrics.accuracy) == expected_acc

        # Recall equals 1 - FRR
        assert pytest.approx(metrics.recall + metrics.frr) == 1.0

        # Specificity equals 1 - FAR
        assert pytest.approx(metrics.specificity + metrics.far) == 1.0

        # Confusion matrix shape
        cm = metrics.confusion_matrix()
        assert len(cm) == 2
        assert len(cm[0]) == 2


# ---------------------------------------------------------------------------
# 5. Threshold Calibration & Freezing Tests
# ---------------------------------------------------------------------------


class TestThresholdCalibrator:
    """Tests for calibrating and freezing operating thresholds."""

    def test_calibration_on_dev_scores(
        self, synthetic_scores: Tuple[np.ndarray, np.ndarray], tmp_path: Path
    ) -> None:
        """Verify calibration finds threshold and creates valid VerificationThreshold."""
        scores, labels = synthetic_scores
        calibrator = ThresholdCalibrator(
            calibration_dataset="dev-clean",
            model_identifier="test-model",
            version="test-v1.0",
        )

        frozen_th, meta = calibrator.calibrate(scores, labels)

        assert isinstance(frozen_th, VerificationThreshold)
        assert isinstance(meta, CalibratedThresholdMetadata)
        assert 0.50 <= frozen_th.threshold_value <= 0.70
        assert frozen_th.version == "test-v1.0"

        # Save and reload test
        json_path = tmp_path / "threshold.json"
        meta.save_json(json_path)
        assert json_path.exists()

        reloaded = ThresholdCalibrator.load_frozen_threshold(json_path)
        assert reloaded.threshold_value == frozen_th.threshold_value
        assert reloaded.version == frozen_th.version

    def test_frozen_threshold_is_immutable_for_test(
        self, synthetic_scores: Tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Verify that evaluating unseen test scores does NOT mutate the frozen threshold."""
        scores, labels = synthetic_scores
        calibrator = ThresholdCalibrator()
        frozen_th, _ = calibrator.calibrate(scores, labels)
        initial_val = frozen_th.threshold_value

        # Evaluate mock test scores with very different distribution
        test_scores = np.array([0.90, 0.95, 0.10, 0.05])
        test_labels = np.array([1, 1, 0, 0])

        test_metrics = compute_classification_metrics(
            test_scores, test_labels, threshold=frozen_th.threshold_value
        )

        # Threshold must not have changed
        assert frozen_th.threshold_value == initial_val
        assert test_metrics.threshold == initial_val


# ---------------------------------------------------------------------------
# 6. Trial Scorer & Manifest Tests
# ---------------------------------------------------------------------------


class TestTrialScorer:
    """Tests for trial scoring and score manifest generation."""

    def test_trial_scorer_computes_scores_and_writes_csv(self, tmp_path: Path) -> None:
        """Verify TrialScorer correctly pairs embeddings and produces valid score CSV."""
        # Setup mock embeddings
        ref_embs = {
            "spk1": np.array([1.0, 0.0, 0.0], dtype=np.float32),
            "spk2": np.array([0.0, 1.0, 0.0], dtype=np.float32),
        }
        probe_embs = {
            "probe_spk1": np.array([1.0, 0.0, 0.0], dtype=np.float32),  # identical to spk1 => score ~ 1.0
            "probe_spk2": np.array([0.0, 1.0, 0.0], dtype=np.float32),  # orthogonal to spk1 => score ~ 0.0
        }

        trial_rows = [
            {
                "trial_id": "trial_001",
                "claimed_speaker_id": "spk1",
                "actual_speaker_id": "spk1",
                "trial_type": "genuine",
                "ground_truth_label": 1,
                "verification_recording_id": "probe_spk1",
            },
            {
                "trial_id": "trial_002",
                "claimed_speaker_id": "spk1",
                "actual_speaker_id": "spk2",
                "trial_type": "impostor",
                "ground_truth_label": 0,
                "verification_recording_id": "probe_spk2",
            },
        ]

        scorer = TrialScorer()
        scored_ds = scorer.score_trials(trial_rows, ref_embs, probe_embs, split_name="test")

        assert scored_ds.total_count == 2
        assert scored_ds.genuine_count == 1
        assert scored_ds.impostor_count == 1
        assert pytest.approx(scored_ds.scores[0], abs=1e-4) == 1.0
        assert pytest.approx(scored_ds.scores[1], abs=1e-4) == 0.0

        # Test writing and reading scores CSV
        csv_path = tmp_path / "scores.csv"
        scorer.write_scores_csv(scored_ds, csv_path)
        assert csv_path.exists()

        reloaded_ds = scorer.load_scores_csv(csv_path)
        assert reloaded_ds.total_count == 2
        assert reloaded_ds.genuine_count == 1
        assert reloaded_ds.impostor_count == 1
        assert pytest.approx(reloaded_ds.scores[0], abs=1e-4) == 1.0

    def test_missing_reference_embedding_raises_error(self) -> None:
        """Verify KeyError is raised when a claimed speaker embedding is missing."""
        trial_rows = [
            {
                "trial_id": "t1",
                "claimed_speaker_id": "missing_spk",
                "actual_speaker_id": "missing_spk",
                "trial_type": "genuine",
                "ground_truth_label": 1,
                "verification_recording_id": "probe1",
            }
        ]
        scorer = TrialScorer()
        with pytest.raises(KeyError, match="missing_spk"):
            scorer.score_trials(trial_rows, reference_embeddings={}, probe_embeddings={}, split_name="test")

    def test_missing_probe_embedding_raises_error(self) -> None:
        """Verify KeyError is raised when a probe embedding is missing."""
        trial_rows = [
            {
                "trial_id": "t1",
                "claimed_speaker_id": "spk1",
                "actual_speaker_id": "spk1",
                "trial_type": "genuine",
                "ground_truth_label": 1,
                "verification_recording_id": "missing_probe",
            }
        ]
        scorer = TrialScorer()
        with pytest.raises(KeyError, match="missing_probe"):
            scorer.score_trials(
                trial_rows,
                reference_embeddings={"spk1": np.array([1.0, 0.0])},
                probe_embeddings={},
                split_name="test",
            )


# ---------------------------------------------------------------------------
# 7. Visualizer Tests
# ---------------------------------------------------------------------------


class TestVisualizer:
    """Tests for Matplotlib figure generation."""

    def test_visualizer_generates_all_png_files(
        self, synthetic_scores: Tuple[np.ndarray, np.ndarray], tmp_path: Path
    ) -> None:
        """Verify visualizer creates valid non-empty PNG files for all 5 requested charts."""
        scores, labels = synthetic_scores
        curve = compute_far_frr_curve(scores, labels, num_thresholds=100)
        eer_res = compute_eer(scores, labels)
        metrics = compute_classification_metrics(scores, labels, threshold=eer_res.eer_threshold)
        auc = compute_roc_auc(scores, labels)

        vis = EvaluationVisualizer(output_dir=tmp_path)
        fig_paths = vis.generate_all_figures(
            curve=curve,
            eer_res=eer_res,
            metrics=metrics,
            genuine_scores=scores[labels == 1],
            impostor_scores=scores[labels == 0],
            roc_auc=auc,
            split_name="synthetic-test",
            prefix="test_",
        )

        assert len(fig_paths) == 5
        for name, path in fig_paths.items():
            assert path.exists(), f"Figure {name} was not created"
            assert path.stat().st_size > 1000, f"Figure {name} is empty or corrupt"
