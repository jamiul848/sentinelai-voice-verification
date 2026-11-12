"""Speaker Verification Evaluation Pipeline Orchestrator.

Orchestrates:
1. Development split threshold calibration at Equal Error Rate (EER).
2. Threshold freezing with provenance metadata.
3. Test split evaluation strictly using the frozen threshold.
4. Metric extraction (FAR, FRR, EER, ROC-AUC, Precision, Recall, F1, Confusion Matrix).
5. Chart rendering and JSON/Markdown report generation.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np

from sentinelai.evaluation.evaluation_report import (
    EvaluationReportGenerator,
    SplitEvaluationSummary,
)
from sentinelai.evaluation.metrics import (
    ClassificationMetrics,
    EERResult,
    FarFrrCurve,
    compute_classification_metrics,
    compute_eer,
    compute_far_frr_curve,
    compute_roc_auc,
)
from sentinelai.evaluation.threshold_calibrator import (
    CalibratedThresholdMetadata,
    ThresholdCalibrator,
)
from sentinelai.evaluation.trial_scorer import ScoredDataset
from sentinelai.evaluation.visualizer import EvaluationVisualizer
from sentinelai.verification.threshold import VerificationThreshold

logger = logging.getLogger(__name__)


@dataclass
class EvaluationPipelineResult:
    """Full results package produced by the evaluation orchestrator."""

    frozen_threshold: VerificationThreshold
    threshold_metadata: CalibratedThresholdMetadata
    dev_summary: SplitEvaluationSummary
    test_summary: SplitEvaluationSummary
    figure_paths: Dict[str, Path]
    report_markdown_path: Path
    dev_metrics_json_path: Path
    test_metrics_json_path: Path
    threshold_json_path: Path


class SpeakerVerificationEvaluator:
    """Orchestrates the scientific evaluation pipeline for speaker verification."""

    def __init__(
        self,
        reports_dir: Path = Path("reports/evaluation"),
        model_identifier: str = "speechbrain/spkrec-ecapa-voxceleb",
    ) -> None:
        """Initialize the evaluator.

        Args:
            reports_dir: Directory where reports and figures are saved.
            model_identifier: Identifier of embedding model.
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir = self.reports_dir / "figures"
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.model_identifier = model_identifier

        self.visualizer = EvaluationVisualizer(output_dir=self.figures_dir)
        self.report_generator = EvaluationReportGenerator(output_dir=self.reports_dir)

    def _compute_score_statistics(self, scores: np.ndarray) -> Dict[str, float]:
        """Compute basic summary statistics for similarity scores."""
        if len(scores) == 0:
            return {}
        return {
            "mean": float(np.mean(scores)),
            "std": float(np.std(scores)),
            "min": float(np.min(scores)),
            "max": float(np.max(scores)),
            "median": float(np.median(scores)),
        }

    def evaluate(
        self,
        dev_dataset: ScoredDataset,
        test_dataset: ScoredDataset,
        calibrator: Optional[ThresholdCalibrator] = None,
    ) -> EvaluationPipelineResult:
        """Run the end-to-end evaluation and calibration pipeline across dev and test splits.

        Args:
            dev_dataset: Scored development split trials.
            test_dataset: Scored test split trials.
            calibrator: Optional ThresholdCalibrator instance.

        Returns:
            EvaluationPipelineResult with complete metrics, figures, and report paths.
        """
        logger.info("=" * 60)
        logger.info("Starting Speaker Verification Benchmark Evaluation")
        logger.info("=" * 60)

        # -------------------------------------------------------------
        # STEP 1: Calibrate Operating Threshold on Development Split
        # -------------------------------------------------------------
        logger.info("Step 1: Calibrating decision threshold on development split...")
        calibrator = calibrator or ThresholdCalibrator(
            calibration_dataset=dev_dataset.split_name,
            model_identifier=self.model_identifier,
        )

        frozen_threshold, threshold_meta = calibrator.calibrate(
            dev_scores=dev_dataset.scores,
            dev_labels=dev_dataset.labels,
            criterion="equal_error_rate",
        )
        theta_star = float(frozen_threshold.threshold_value)

        # Dev metrics
        dev_curve = compute_far_frr_curve(dev_dataset.scores, dev_dataset.labels)
        dev_eer = compute_eer(dev_dataset.scores, dev_dataset.labels)
        dev_roc_auc = compute_roc_auc(dev_dataset.scores, dev_dataset.labels)
        dev_operating = compute_classification_metrics(
            dev_dataset.scores, dev_dataset.labels, threshold=theta_star
        )

        dev_summary = SplitEvaluationSummary(
            split_name=dev_dataset.split_name,
            dataset_name=f"LibriSpeech ({dev_dataset.split_name})",
            model_identifier=self.model_identifier,
            total_trials=dev_dataset.total_count,
            genuine_trials=dev_dataset.genuine_count,
            impostor_trials=dev_dataset.impostor_count,
            operating_threshold=theta_star,
            is_threshold_calibrated_on_this_split=True,
            eer=dev_eer,
            operating_metrics=dev_operating,
            roc_auc=dev_roc_auc,
            score_statistics=self._compute_score_statistics(dev_dataset.scores),
        )

        # -------------------------------------------------------------
        # STEP 2: Evaluate Frozen Threshold on Test Split (Zero Retuning)
        # -------------------------------------------------------------
        logger.info("Step 2: Evaluating frozen threshold on test split (unseen)...")
        test_curve = compute_far_frr_curve(test_dataset.scores, test_dataset.labels)
        test_eer_diagnostic = compute_eer(test_dataset.scores, test_dataset.labels)
        test_roc_auc = compute_roc_auc(test_dataset.scores, test_dataset.labels)

        # Note: Apply EXACT frozen threshold theta_star from dev calibration
        test_operating = compute_classification_metrics(
            test_dataset.scores, test_dataset.labels, threshold=theta_star
        )

        test_summary = SplitEvaluationSummary(
            split_name=test_dataset.split_name,
            dataset_name=f"LibriSpeech ({test_dataset.split_name})",
            model_identifier=self.model_identifier,
            total_trials=test_dataset.total_count,
            genuine_trials=test_dataset.genuine_count,
            impostor_trials=test_dataset.impostor_count,
            operating_threshold=theta_star,
            is_threshold_calibrated_on_this_split=False,
            eer=test_eer_diagnostic,
            operating_metrics=test_operating,
            roc_auc=test_roc_auc,
            score_statistics=self._compute_score_statistics(test_dataset.scores),
        )

        # -------------------------------------------------------------
        # STEP 3: Generate Visualizations
        # -------------------------------------------------------------
        logger.info("Step 3: Rendering benchmark figures...")
        figure_paths = self.visualizer.generate_all_figures(
            curve=test_curve,
            eer_res=test_eer_diagnostic,
            metrics=test_operating,
            genuine_scores=test_dataset.genuine_scores,
            impostor_scores=test_dataset.impostor_scores,
            roc_auc=test_roc_auc,
            split_name=test_dataset.split_name,
            prefix="test_",
        )

        # Also generate dev FAR/FRR and score distribution figures
        dev_fig_paths = self.visualizer.generate_all_figures(
            curve=dev_curve,
            eer_res=dev_eer,
            metrics=dev_operating,
            genuine_scores=dev_dataset.genuine_scores,
            impostor_scores=dev_dataset.impostor_scores,
            roc_auc=dev_roc_auc,
            split_name=dev_dataset.split_name,
            prefix="dev_",
        )
        figure_paths.update(dev_fig_paths)

        # -------------------------------------------------------------
        # STEP 4: Export Reports & Serialization
        # -------------------------------------------------------------
        logger.info("Step 4: Writing JSON metrics and Markdown research report...")
        threshold_json_path = threshold_meta.save_json(
            self.reports_dir / "calibrated_threshold.json"
        )
        dev_metrics_json_path = dev_summary.save_json(
            self.reports_dir / "development_metrics.json"
        )
        test_metrics_json_path = test_summary.save_json(
            self.reports_dir / "test_metrics.json"
        )

        report_markdown_path = self.report_generator.save_markdown_report(
            dev_summary=dev_summary,
            test_summary=test_summary,
            threshold_meta=threshold_meta,
            figure_paths=figure_paths,
            filename="evaluation_report.md",
        )

        logger.info("Evaluation pipeline execution complete.")
        return EvaluationPipelineResult(
            frozen_threshold=frozen_threshold,
            threshold_metadata=threshold_meta,
            dev_summary=dev_summary,
            test_summary=test_summary,
            figure_paths=figure_paths,
            report_markdown_path=report_markdown_path,
            dev_metrics_json_path=dev_metrics_json_path,
            test_metrics_json_path=test_metrics_json_path,
            threshold_json_path=threshold_json_path,
        )

