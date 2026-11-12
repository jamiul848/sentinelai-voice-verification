"""Visualization Engine for Speaker Verification Benchmark Results.

Generates publication-quality charts and plots using Matplotlib (Agg headless backend):
1. Receiver Operating Characteristic (ROC) Curve with AUC.
2. Detection Error Trade-off (DET) Curve on normal deviate scale.
3. FAR and FRR vs. Decision Threshold Curve with EER intersection.
4. Genuine vs. Impostor Cosine Similarity Score Distributions.
5. 2x2 Decision Confusion Matrix Heatmap at Operating Threshold.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Force headless Matplotlib backend prior to pyplot import
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde, norm

from sentinelai.evaluation.metrics import (
    ClassificationMetrics,
    EERResult,
    FarFrrCurve,
    compute_det_coordinates,
    compute_far_frr_curve,
    compute_roc_auc,
)

logger = logging.getLogger(__name__)


class EvaluationVisualizer:
    """Generates evaluation figures and charts saved to disk."""

    FIGURE_DPI = 300
    STYLE_COLOR_GENUINE = "#2b5c8f"    # Deep Blue
    STYLE_COLOR_IMPOSTOR = "#d95f02"   # Vermilion / Red-Orange
    STYLE_COLOR_THRESHOLD = "#7570b3"  # Purple
    STYLE_COLOR_ACCENT = "#1b9e77"     # Teal / Green

    def __init__(self, output_dir: Path) -> None:
        """Initialize the visualizer with output directory.

        Args:
            output_dir: Target directory for generated figures.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_roc_curve(
        self,
        far: np.ndarray,
        frr: np.ndarray,
        roc_auc: float,
        output_filename: str = "roc_curve.png",
        split_name: str = "Evaluation Split",
    ) -> Path:
        """Plot and save Receiver Operating Characteristic (ROC) curve.

        Args:
            far: False Acceptance Rates (False Positive Rate).
            frr: False Rejection Rates.
            roc_auc: Area Under the ROC Curve.
            output_filename: Target filename.
            split_name: Label for plot title/legend.

        Returns:
            Path to saved figure.
        """
        output_path = self.output_dir / output_filename
        tpr = 1.0 - frr
        fpr = far

        # Sort by FPR for clean plotting
        sort_idx = np.argsort(fpr)
        sorted_fpr = fpr[sort_idx]
        sorted_tpr = tpr[sort_idx]

        fig, ax = plt.subplots(figsize=(7, 6), dpi=self.FIGURE_DPI)
        ax.plot(
            sorted_fpr,
            sorted_tpr,
            color=self.STYLE_COLOR_GENUINE,
            lw=2.5,
            label=f"{split_name} (ROC-AUC = {roc_auc:.4f})",
        )
        ax.plot([0, 1], [0, 1], color="gray", lw=1.2, linestyle="--", label="Random Chance (AUC = 0.5000)")

        ax.set_xlim([-0.02, 1.02])
        ax.set_ylim([-0.02, 1.02])
        ax.set_xlabel("False Positive Rate (FAR / False Alarm)", fontsize=11, fontweight="bold")
        ax.set_ylabel("True Positive Rate (1 - FRR / Sensitivity)", fontsize=11, fontweight="bold")
        ax.set_title(f"Receiver Operating Characteristic (ROC) — {split_name}", fontsize=12, fontweight="bold", pad=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="lower right", framealpha=0.9)

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved ROC curve to {output_path}")
        return output_path

    def plot_det_curve(
        self,
        far: np.ndarray,
        frr: np.ndarray,
        eer_res: EERResult,
        output_filename: str = "det_curve.png",
        split_name: str = "Evaluation Split",
    ) -> Path:
        """Plot and save Detection Error Trade-off (DET) curve on normal deviate scale.

        Args:
            far: False Acceptance Rates.
            frr: False Rejection Rates.
            eer_res: EERResult instance containing EER point.
            output_filename: Target filename.
            split_name: Label for plot title/legend.

        Returns:
            Path to saved figure.
        """
        output_path = self.output_dir / output_filename

        dev_far, dev_frr = compute_det_coordinates(far, frr)

        fig, ax = plt.subplots(figsize=(7, 6), dpi=self.FIGURE_DPI)

        # Plot DET curve
        ax.plot(
            dev_far,
            dev_frr,
            color=self.STYLE_COLOR_GENUINE,
            lw=2.2,
            label=f"{split_name} DET Curve",
        )

        # Plot EER point
        eer_dev = float(norm.ppf(np.clip(eer_res.eer, 1e-4, 1.0 - 1e-4)))
        ax.scatter(
            [eer_dev],
            [eer_dev],
            color=self.STYLE_COLOR_IMPOSTOR,
            s=80,
            zorder=5,
            label=f"EER Point = {eer_res.eer_percent:.2f}% (θ = {eer_res.eer_threshold:.3f})",
        )

        # Reference tick marks on normal deviate scale corresponding to standard probabilities
        ticks = [0.001, 0.01, 0.05, 0.1, 0.2, 0.4, 0.6]
        tick_locs = norm.ppf(ticks)
        tick_labels = [f"{t * 100:.1f}%" for t in ticks]

        ax.set_xticks(tick_locs)
        ax.set_xticklabels(tick_labels, fontsize=9)
        ax.set_yticks(tick_locs)
        ax.set_yticklabels(tick_labels, fontsize=9)

        ax.set_xlim([norm.ppf(0.0008), norm.ppf(0.70)])
        ax.set_ylim([norm.ppf(0.0008), norm.ppf(0.70)])

        ax.set_xlabel("False Alarm Rate (FAR / P_fa)", fontsize=11, fontweight="bold")
        ax.set_ylabel("Miss Rate (FRR / P_miss)", fontsize=11, fontweight="bold")
        ax.set_title(f"Detection Error Trade-off (DET) Curve — {split_name}", fontsize=12, fontweight="bold", pad=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper right", framealpha=0.9)

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved DET curve to {output_path}")
        return output_path

    def plot_far_frr_curve(
        self,
        thresholds: np.ndarray,
        far: np.ndarray,
        frr: np.ndarray,
        eer_res: EERResult,
        output_filename: str = "far_frr_curve.png",
        split_name: str = "Evaluation Split",
    ) -> Path:
        """Plot and save FAR and FRR as functions of the decision threshold.

        Args:
            thresholds: 1D array of thresholds.
            far: False Acceptance Rates.
            frr: False Rejection Rates.
            eer_res: EERResult instance.
            output_filename: Target filename.
            split_name: Label for plot.

        Returns:
            Path to saved figure.
        """
        output_path = self.output_dir / output_filename

        fig, ax = plt.subplots(figsize=(8, 5.5), dpi=self.FIGURE_DPI)

        ax.plot(thresholds, far * 100.0, color=self.STYLE_COLOR_IMPOSTOR, lw=2.2, label="FAR (False Acceptance Rate)")
        ax.plot(thresholds, frr * 100.0, color=self.STYLE_COLOR_GENUINE, lw=2.2, label="FRR (False Rejection Rate)")

        # Vertical line at EER threshold
        ax.axvline(
            eer_res.eer_threshold,
            color=self.STYLE_COLOR_THRESHOLD,
            linestyle="--",
            lw=1.8,
            label=f"EER Threshold θ* = {eer_res.eer_threshold:.4f}",
        )

        # Highlight EER crossing point
        ax.scatter(
            [eer_res.eer_threshold],
            [eer_res.eer_percent],
            color="black",
            s=70,
            zorder=6,
            label=f"EER = {eer_res.eer_percent:.2f}%",
        )

        ax.set_xlim([float(np.min(thresholds)), float(np.max(thresholds))])
        ax.set_ylim([-2.0, 102.0])
        ax.set_xlabel("Decision Threshold (Cosine Similarity)", fontsize=11, fontweight="bold")
        ax.set_ylabel("Error Rate (%)", fontsize=11, fontweight="bold")
        ax.set_title(f"FAR & FRR vs. Decision Threshold — {split_name}", fontsize=12, fontweight="bold", pad=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="center right", framealpha=0.9)

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved FAR/FRR curve to {output_path}")
        return output_path

    def plot_score_distributions(
        self,
        genuine_scores: np.ndarray,
        impostor_scores: np.ndarray,
        threshold: float,
        output_filename: str = "score_distribution.png",
        split_name: str = "Evaluation Split",
    ) -> Path:
        """Plot histogram and density distributions for genuine vs. impostor scores.

        Args:
            genuine_scores: 1D array of genuine trial scores.
            impostor_scores: 1D array of impostor trial scores.
            threshold: Calibrated decision threshold.
            output_filename: Target filename.
            split_name: Label for plot.

        Returns:
            Path to saved figure.
        """
        output_path = self.output_dir / output_filename

        fig, ax = plt.subplots(figsize=(8, 5.5), dpi=self.FIGURE_DPI)

        bins = np.linspace(-0.2, 1.0, 60)

        # Impostor distribution
        ax.hist(
            impostor_scores,
            bins=bins,
            density=True,
            alpha=0.45,
            color=self.STYLE_COLOR_IMPOSTOR,
            label=f"Impostor Trials (N = {len(impostor_scores):,})",
            edgecolor="none",
        )

        # Genuine distribution
        ax.hist(
            genuine_scores,
            bins=bins,
            density=True,
            alpha=0.45,
            color=self.STYLE_COLOR_GENUINE,
            label=f"Genuine Trials (N = {len(genuine_scores):,})",
            edgecolor="none",
        )

        # Smooth KDE curves if enough points
        x_grid = np.linspace(-0.2, 1.0, 400)
        if len(impostor_scores) > 5:
            kde_imp = gaussian_kde(impostor_scores)
            ax.plot(x_grid, kde_imp(x_grid), color=self.STYLE_COLOR_IMPOSTOR, lw=2.2)

        if len(genuine_scores) > 5:
            kde_gen = gaussian_kde(genuine_scores)
            ax.plot(x_grid, kde_gen(x_grid), color=self.STYLE_COLOR_GENUINE, lw=2.2)

        # Decision threshold line
        ax.axvline(
            threshold,
            color=self.STYLE_COLOR_THRESHOLD,
            linestyle="--",
            lw=2.2,
            label=f"Calibrated Threshold θ* = {threshold:.4f}",
        )

        ax.set_xlabel("Cosine Similarity Score", fontsize=11, fontweight="bold")
        ax.set_ylabel("Probability Density", fontsize=11, fontweight="bold")
        ax.set_title(f"Acoustic Score Distributions — {split_name}", fontsize=12, fontweight="bold", pad=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper left", framealpha=0.9)

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved score distribution to {output_path}")
        return output_path

    def plot_confusion_matrix(
        self,
        metrics: ClassificationMetrics,
        output_filename: str = "confusion_matrix.png",
        split_name: str = "Evaluation Split",
    ) -> Path:
        """Plot and save confusion matrix heatmap at the operating threshold.

        Args:
            metrics: ClassificationMetrics instance.
            output_filename: Target filename.
            split_name: Label for plot.

        Returns:
            Path to saved figure.
        """
        output_path = self.output_dir / output_filename

        cm = np.array([
            [metrics.true_negatives, metrics.false_positives],
            [metrics.false_negatives, metrics.true_positives],
        ])

        total = float(np.sum(cm))
        cm_norm = (cm / total) * 100.0 if total > 0 else cm

        fig, ax = plt.subplots(figsize=(6, 5.2), dpi=self.FIGURE_DPI)

        im = ax.imshow(cm, cmap="Blues", interpolation="nearest")

        # Colorbar
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Trial Count", fontsize=10)

        # Labels
        classes = ["Impostor (0)", "Genuine (1)"]
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(classes, fontsize=10, fontweight="bold")
        ax.set_yticklabels(classes, fontsize=10, fontweight="bold")

        ax.set_xlabel("Predicted Identity Decision", fontsize=11, fontweight="bold", labelpad=8)
        ax.set_ylabel("True Identity Label", fontsize=11, fontweight="bold", labelpad=8)
        ax.set_title(
            f"Confusion Matrix (θ* = {metrics.threshold:.4f}) — {split_name}\n"
            f"FAR: {metrics.far * 100:.2f}% | FRR: {metrics.frr * 100:.2f}% | Acc: {metrics.accuracy * 100:.2f}%",
            fontsize=11,
            fontweight="bold",
            pad=12,
        )

        # Text annotations inside cells
        thresh = cm.max() / 2.0
        for i in range(2):
            for j in range(2):
                cnt = cm[i, j]
                pct = cm_norm[i, j]
                cell_label = (
                    "TN" if (i == 0 and j == 0) else
                    "FP (FA)" if (i == 0 and j == 1) else
                    "FN (FR)" if (i == 1 and j == 0) else
                    "TP"
                )
                txt_color = "white" if cnt > thresh else "black"
                ax.text(
                    j,
                    i,
                    f"{cell_label}\n{cnt:,}\n({pct:.1f}%)",
                    ha="center",
                    va="center",
                    color=txt_color,
                    fontsize=11,
                    fontweight="bold",
                )

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved confusion matrix to {output_path}")
        return output_path

    def generate_all_figures(
        self,
        curve: FarFrrCurve,
        eer_res: EERResult,
        metrics: ClassificationMetrics,
        genuine_scores: np.ndarray,
        impostor_scores: np.ndarray,
        roc_auc: float,
        split_name: str,
        prefix: str = "",
    ) -> Dict[str, Path]:
        """Generate the complete set of 5 benchmark figures.

        Args:
            curve: FarFrrCurve instance.
            eer_res: EERResult instance.
            metrics: ClassificationMetrics at the operating threshold.
            genuine_scores: 1D array of genuine similarity scores.
            impostor_scores: 1D array of impostor similarity scores.
            roc_auc: ROC-AUC score.
            split_name: Name of evaluated split.
            prefix: Optional filename prefix (e.g. 'dev_' or 'test_').

        Returns:
            Dictionary mapping figure name to saved Path.
        """
        paths = {}

        p_roc = self.plot_roc_curve(
            far=curve.far,
            frr=curve.frr,
            roc_auc=roc_auc,
            output_filename=f"{prefix}roc_curve.png",
            split_name=split_name,
        )
        paths["roc_curve"] = p_roc

        p_det = self.plot_det_curve(
            far=curve.far,
            frr=curve.frr,
            eer_res=eer_res,
            output_filename=f"{prefix}det_curve.png",
            split_name=split_name,
        )
        paths["det_curve"] = p_det

        p_far_frr = self.plot_far_frr_curve(
            thresholds=curve.thresholds,
            far=curve.far,
            frr=curve.frr,
            eer_res=eer_res,
            output_filename=f"{prefix}far_frr_curve.png",
            split_name=split_name,
        )
        paths["far_frr_curve"] = p_far_frr

        p_dist = self.plot_score_distributions(
            genuine_scores=genuine_scores,
            impostor_scores=impostor_scores,
            threshold=metrics.threshold,
            output_filename=f"{prefix}score_distribution.png",
            split_name=split_name,
        )
        paths["score_distribution"] = p_dist

        p_cm = self.plot_confusion_matrix(
            metrics=metrics,
            output_filename=f"{prefix}confusion_matrix.png",
            split_name=split_name,
        )
        paths["confusion_matrix"] = p_cm

        return paths

