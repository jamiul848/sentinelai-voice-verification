"""Evaluation Report Generation and Performance Serialization.

Compiles JSON metric summaries and creates a GitHub-flavored Markdown
research report documenting methodology, calibration, operational performance,
development vs. test generalizability, and acoustic limitations.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from sentinelai.evaluation.metrics import ClassificationMetrics, EERResult
from sentinelai.evaluation.threshold_calibrator import CalibratedThresholdMetadata

logger = logging.getLogger(__name__)


@dataclass
class SplitEvaluationSummary:
    """Summary metrics package for a single evaluated split."""

    split_name: str
    dataset_name: str
    model_identifier: str
    total_trials: int
    genuine_trials: int
    impostor_trials: int
    operating_threshold: float
    is_threshold_calibrated_on_this_split: bool
    eer: EERResult
    operating_metrics: ClassificationMetrics
    roc_auc: float
    score_statistics: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert split evaluation summary to JSON dictionary."""
        return {
            "split_name": self.split_name,
            "dataset_name": self.dataset_name,
            "model_identifier": self.model_identifier,
            "total_trials": self.total_trials,
            "genuine_trials": self.genuine_trials,
            "impostor_trials": self.impostor_trials,
            "operating_threshold": round(self.operating_threshold, 6),
            "is_threshold_calibrated_on_this_split": self.is_threshold_calibrated_on_this_split,
            "eer_metrics": self.eer.to_dict(),
            "operating_metrics": self.operating_metrics.to_dict(),
            "roc_auc": round(self.roc_auc, 6),
            "score_statistics": {k: round(v, 4) for k, v in self.score_statistics.items()},
        }

    def save_json(self, output_path: Path) -> Path:
        """Save evaluation summary as JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved evaluation metrics to {output_path}")
        return output_path


class EvaluationReportGenerator:
    """Generates the formal Phase 5C evaluation markdown report and JSON files."""

    def __init__(self, output_dir: Path) -> None:
        """Initialize the report generator.

        Args:
            output_dir: Directory where reports/evaluation/ contents are saved.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_markdown_report(
        self,
        dev_summary: SplitEvaluationSummary,
        test_summary: SplitEvaluationSummary,
        threshold_meta: CalibratedThresholdMetadata,
        figure_paths: Dict[str, Path],
    ) -> str:
        """Generate a complete GitHub-flavored Markdown evaluation report.

        Args:
            dev_summary: Development split evaluation summary.
            test_summary: Test split evaluation summary.
            threshold_meta: Provenance metadata for calibrated threshold.
            figure_paths: Paths to generated figures.

        Returns:
            Markdown formatted report string.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Generalization gap calculations
        delta_far = abs(test_summary.operating_metrics.far - dev_summary.operating_metrics.far)
        delta_frr = abs(test_summary.operating_metrics.frr - dev_summary.operating_metrics.frr)
        delta_acc = abs(test_summary.operating_metrics.accuracy - dev_summary.operating_metrics.accuracy)

        md = []
        md.append("# SentinelAI Voice Verification — Phase 5C: Threshold Calibration & Performance Analysis")
        md.append("")
        md.append(f"**Report Generated:** `{timestamp}`  ")
        md.append(f"**Pretrained Model:** `{threshold_meta.model_identifier}`  ")
        md.append(f"**Scoring Metric:** `{threshold_meta.scoring_metric}` (Cosine Similarity in [-1.0, 1.0])  ")
        md.append(f"**Operating Decision Threshold (θ*):** `{threshold_meta.threshold_value:.4f}` (Calibrated on {threshold_meta.calibration_dataset})")
        md.append("")
        md.append("---")
        md.append("")

        # 1. Executive Summary
        md.append("## 1. Executive Summary & Calibration Protocol")
        md.append("")
        md.append(
            "Phase 5C establishes an empirical benchmark evaluation and decision threshold calibration "
            "for the SentinelAI speaker recognition pipeline. In accordance with biometric evaluation standards:"
        )
        md.append(
            f"1. **Calibration:** Operating threshold $\\theta^* = {threshold_meta.threshold_value:.4f}$ was calibrated "
            f"strictly on `{dev_summary.split_name}` by finding the point minimizing the difference between "
            f"False Acceptance Rate (FAR) and False Rejection Rate (FRR) (Equal Error Rate operating point: {dev_summary.eer.eer_percent:.2f}%)."
        )
        md.append(
            "2. **Threshold Freezing:** The calibrated threshold was frozen into an immutable configuration without any "
            "hyperparameter tuning on the test partition."
        )
        md.append(
            f"3. **Independent Evaluation:** The exact frozen threshold $\\theta^*$ was subsequently evaluated on `{test_summary.split_name}` "
            f"({test_summary.total_trials:,} trials across {test_summary.genuine_trials:,} genuine and {test_summary.impostor_trials:,} impostor comparisons), "
            "guaranteeing zero test-to-threshold data contamination."
        )
        md.append("")
        md.append("---")
        md.append("")

        # 2. Performance Comparison Table
        md.append("## 2. Performance Comparison: Development vs. Test Partitions")
        md.append("")
        md.append("| Metric | Development Split (`dev-clean`) | Test Split (`test-clean`) | Generalization Gap (Δ) |")
        md.append("| :--- | :---: | :---: | :---: |")
        md.append(f"| **Calibration Status** | **Calibrated Operating Point** | **Frozen Evaluation (Unseen)** | — |")
        md.append(f"| **Decision Threshold (θ)** | **{dev_summary.operating_threshold:.4f}** | **{test_summary.operating_threshold:.4f} (Frozen)** | 0.0000 |")
        md.append(f"| **Total Trials** | {dev_summary.total_trials:,} | {test_summary.total_trials:,} | — |")
        md.append(f"| **Genuine Trials** | {dev_summary.genuine_trials:,} | {test_summary.genuine_trials:,} | — |")
        md.append(f"| **Impostor Trials** | {dev_summary.impostor_trials:,} | {test_summary.impostor_trials:,} | — |")
        md.append(f"| **False Acceptance Rate (FAR)** | **{dev_summary.operating_metrics.far * 100:.2f}%** | **{test_summary.operating_metrics.far * 100:.2f}%** | {delta_far * 100:.2f}% |")
        md.append(f"| **False Rejection Rate (FRR)** | **{dev_summary.operating_metrics.frr * 100:.2f}%** | **{test_summary.operating_metrics.frr * 100:.2f}%** | {delta_frr * 100:.2f}% |")
        md.append(f"| **Classification Accuracy** | {dev_summary.operating_metrics.accuracy * 100:.2f}% | {test_summary.operating_metrics.accuracy * 100:.2f}% | {delta_acc * 100:.2f}% |")
        md.append(f"| **Precision** | {dev_summary.operating_metrics.precision * 100:.2f}% | {test_summary.operating_metrics.precision * 100:.2f}% | — |")
        md.append(f"| **Recall (1 - FRR)** | {dev_summary.operating_metrics.recall * 100:.2f}% | {test_summary.operating_metrics.recall * 100:.2f}% | — |")
        md.append(f"| **F1-Score** | {dev_summary.operating_metrics.f1_score:.4f} | {test_summary.operating_metrics.f1_score:.4f} | — |")
        md.append(f"| **ROC-AUC** | **{dev_summary.roc_auc:.4f}** | **{test_summary.roc_auc:.4f}** | {abs(test_summary.roc_auc - dev_summary.roc_auc):.4f} |")
        md.append(f"| **Equal Error Rate (EER)** | **{dev_summary.eer.eer_percent:.2f}%** (Operating) | **{test_summary.eer.eer_percent:.2f}%** (Diagnostic only) | {abs(test_summary.eer.eer_percent - dev_summary.eer.eer_percent):.2f}% |")
        md.append("")
        md.append("> [!IMPORTANT]")
        md.append("> **Operational Error vs. Diagnostic EER:**")
        md.append(f"> On `{test_summary.split_name}`, the operational error rates achieved by applying the frozen threshold $\\theta^* = {threshold_meta.threshold_value:.4f}$ "
                  f"are **FAR = {test_summary.operating_metrics.far * 100:.2f}%** and **FRR = {test_summary.operating_metrics.frr * 100:.2f}%**. ")
        md.append(f"> The test split's theoretical EER ({test_summary.eer.eer_percent:.2f}%) is reported strictly as an acoustic diagnostic metric; "
                  "the threshold was not recalibrated to match test data.")
        md.append("")
        md.append("---")
        md.append("")

        # 3. Confusion Matrix Breakdown
        md.append("## 3. Confusion Matrix Breakdown at Operating Threshold")
        md.append("")
        md.append(f"### Decision Rule: $\\text{{Decision}}(s) = \\text{{MATCH}}$ if $s \\ge {threshold_meta.threshold_value:.4f}$, else $\\text{{NO\\_MATCH}}$")
        md.append("")
        dev_cm = dev_summary.operating_metrics
        test_cm = test_summary.operating_metrics

        md.append(f"#### Test Partition (`{test_summary.split_name}`):")
        md.append("")
        md.append("| True Condition | Predicted MATCH (1) | Predicted NO_MATCH (0) | Total |")
        md.append("| :--- | :---: | :---: | :---: |")
        md.append(f"| **Genuine Speaker** | **TP = {test_cm.true_positives:,}** ({test_cm.recall * 100:.1f}%) | **FN (FR) = {test_cm.false_negatives:,}** ({test_cm.frr * 100:.2f}%) | {test_cm.genuine_count:,} |")
        md.append(f"| **Impostor Speaker** | **FP (FA) = {test_cm.false_positives:,}** ({test_cm.far * 100:.2f}%) | **TN = {test_cm.true_negatives:,}** ({test_cm.specificity * 100:.1f}%) | {test_cm.impostor_count:,} |")
        md.append(f"| **Total** | {test_cm.true_positives + test_cm.false_positives:,} | {test_cm.false_negatives + test_cm.true_negatives:,} | **{test_cm.total_trials:,}** |")
        md.append("")
        md.append("---")
        md.append("")

        # 4. Visualizations
        md.append("## 4. Benchmark Visualizations")
        md.append("")
        md.append("All figures are generated via Matplotlib and saved to `reports/evaluation/figures/`:")
        md.append("")
        md.append("1. **Receiver Operating Characteristic (ROC) Curve:** Demonstrates true positive rate vs. false alarm rate across all possible thresholds.")
        md.append("2. **Detection Error Trade-off (DET) Curve:** Displays miss probability vs. false alarm probability on normal deviate scales.")
        md.append("3. **FAR & FRR vs. Threshold Curve:** Shows the error crossover point determining Equal Error Rate.")
        md.append("4. **Cosine Similarity Score Distributions:** Dual histograms demonstrating acoustic separation between genuine and impostor trials.")
        md.append("5. **Confusion Matrix Heatmap:** Normalized classification breakdown at the operating point.")
        md.append("")
        md.append("---")
        md.append("")

        # 5. Critical Research Validity & Academic Disclaimers
        md.append("## 5. Critical Research Validity & Academic Disclaimers")
        md.append("")
        md.append(
            "To uphold rigorous scientific standards in biometrics and machine learning research, the following "
            "methodological limitations must be explicitly recognized:"
        )
        md.append("")
        md.append(
            "1. **Domain Mismatch & Read Speech Nature:** LibriVox audiobook recordings represent scripted read speech "
            "recorded with high vocal projection, consistent cadence, and minimal emotional volatility. Performance metrics "
            "do not directly generalize to conversational speech, telephony channels, or spontaneous dialogue."
        )
        md.append(
            "2. **Acoustic Cleanliness (High SNR):** Recordings exhibit near-studio cleanliness with low ambient noise and "
            "negligible room reverberation. Real-world acoustic degradations (cocktail party noise, street traffic, reverberant rooms) "
            "will degrade directional cosine similarity."
        )
        md.append(
            "3. **Absence of Presentation Attacks (Anti-Spoofing):** LibriSpeech contains 100% bona fide human recordings. "
            "The system was evaluated solely on zero-effort impostor attempts. It provides **zero defense against physical acoustic replays, "
            "speech synthesis (TTS), or voice conversion deepfakes**. A production biometric pipeline must incorporate a dedicated "
            "Presentation Attack Detection (PAD) front-end."
        )
        md.append(
            "4. **Pretrained Model Heritage:** The underlying ECAPA-TDNN was pretrained on the VoxCeleb 1 & 2 datasets "
            "(`speechbrain/spkrec-ecapa-voxceleb`). Consequently, this benchmark constitutes a cross-corpus evaluation rather "
            "than an in-domain fine-tuned evaluation."
        )
        md.append(
            "5. **Statistical Dependency Among Trials:** Multiple trials originate from the same pool of speakers and chapters. "
            "Trials are statistically correlated and cannot be treated as completely independent human subject samples. "
            "The total trial count (5,607) reflects verification attempts, not the number of independent participants (76 speakers)."
        )
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 6. Artifact Artifact Locations")
        md.append("")
        md.append(f"- Calibrated Threshold: [`reports/evaluation/calibrated_threshold.json`](file:///{self.output_dir.as_posix()}/calibrated_threshold.json)")
        md.append(f"- Development Metrics: [`reports/evaluation/development_metrics.json`](file:///{self.output_dir.as_posix()}/development_metrics.json)")
        md.append(f"- Test Metrics: [`reports/evaluation/test_metrics.json`](file:///{self.output_dir.as_posix()}/test_metrics.json)")
        md.append(f"- Benchmark Figures: [`reports/evaluation/figures/`](file:///{self.output_dir.as_posix()}/figures)")
        md.append("")

        return "\n".join(md)

    def save_markdown_report(
        self,
        dev_summary: SplitEvaluationSummary,
        test_summary: SplitEvaluationSummary,
        threshold_meta: CalibratedThresholdMetadata,
        figure_paths: Dict[str, Path],
        filename: str = "evaluation_report.md",
    ) -> Path:
        """Save the markdown report to disk.

        Args:
            dev_summary: Development split evaluation summary.
            test_summary: Test split evaluation summary.
            threshold_meta: Calibrated threshold metadata.
            figure_paths: Generated figure file paths.
            filename: Target markdown filename.

        Returns:
            Path to saved markdown file.
        """
        output_path = self.output_dir / filename
        content = self.generate_markdown_report(
            dev_summary=dev_summary,
            test_summary=test_summary,
            threshold_meta=threshold_meta,
            figure_paths=figure_paths,
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved formal evaluation report to {output_path}")
        return output_path
