"""Visualization Engine for Statistical Validation and Robustness Analysis.

Generates 7 publication-quality figures using Matplotlib (Agg headless backend):
1. FAR & FRR with 95% Bootstrap Confidence Bands.
2. Bootstrap Metric Probability Distributions with CI percentiles.
3. EER Performance Across Multiple Enrollment Random Seeds.
4. Enrollment Recording Count (K=1, 2, 3) vs. Equal Error Rate.
5. Enrollment Recording Count (K=1, 2, 3) vs. Operational FAR and FRR.
6. Decision Threshold Sensitivity Curves (0.55 to 0.70) with Stability Window.
7. Speaker-Level Verification Error Breakdown (Top FR and FA Speakers).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Force headless Matplotlib backend prior to pyplot import
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

from sentinelai.evaluation.bootstrap import BootstrapResult
from sentinelai.evaluation.error_analysis import ErrorAnalysisSummary
from sentinelai.evaluation.robustness import (
    EnrollmentCountRunResult,
    RandomSeedRunResult,
)
from sentinelai.evaluation.sensitivity import ThresholdSensitivitySummary

logger = logging.getLogger(__name__)


class RobustnessVisualizer:
    """Generates Phase 5D statistical validation and robustness charts."""

    FIGURE_DPI = 300
    COLOR_GENUINE = "#2b5c8f"    # Deep Blue
    COLOR_IMPOSTOR = "#d95f02"   # Vermilion / Red-Orange
    COLOR_THRESHOLD = "#7570b3"  # Purple
    COLOR_ACCENT = "#1b9e77"     # Teal / Green
    COLOR_BASELINE = "#d95f02"   # Orange highlight for Seed 42

    def __init__(self, output_dir: Path) -> None:
        """Initialize the robustness visualizer.

        Args:
            output_dir: Directory where figures are saved (reports/evaluation/robustness/figures/).
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_far_frr_ci(
        self,
        bootstrap_result: BootstrapResult,
        output_filename: str = "fig1_far_frr_ci.png",
    ) -> Path:
        """Figure 1: Plot operational FAR and FRR with 95% Confidence Intervals."""
        output_path = self.output_dir / output_filename
        fig, ax = plt.subplots(figsize=(7, 5), dpi=self.FIGURE_DPI)

        metrics = ["FAR", "FRR", "EER", "Accuracy"]
        keys = ["far", "frr", "eer", "accuracy"]

        cis = bootstrap_result.confidence_intervals.metrics

        pts = [cis[k].point_estimate * 100.0 for k in keys]
        lows = [cis[k].ci_lower * 100.0 for k in keys]
        highs = [cis[k].ci_upper * 100.0 for k in keys]
        y_err = [
            [pts[i] - lows[i] for i in range(len(pts))],
            [highs[i] - pts[i] for i in range(len(pts))],
        ]

        x = np.arange(len(metrics))
        bars = ax.bar(x, pts, yerr=y_err, capsize=6, color=[self.COLOR_IMPOSTOR, self.COLOR_GENUINE, self.COLOR_THRESHOLD, self.COLOR_ACCENT], alpha=0.8, edgecolor="black", lw=1.2)

        for idx, rect in enumerate(bars):
            h = rect.get_height()
            ax.text(
                rect.get_x() + rect.get_width() / 2.0,
                highs[idx] + 1.5,
                f"{pts[idx]:.2f}%\n[{lows[idx]:.2f}%, {highs[idx]:.2f}%]",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
            )

        ax.set_xticks(x)
        ax.set_xticklabels(metrics, fontsize=11, fontweight="bold")
        ax.set_ylabel("Error / Performance Metric (%)", fontsize=11, fontweight="bold")
        ax.set_title(
            f"Speaker Verification Metrics with 95% Cluster Bootstrap CIs\n"
            f"(Frozen θ* = {bootstrap_result.frozen_threshold:.4f}, N = {bootstrap_result.iterations_valid:,} Replicates)",
            fontsize=11,
            fontweight="bold",
            pad=12,
        )
        ax.set_ylim([0, 115])
        ax.grid(True, linestyle=":", alpha=0.6, axis="y")

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved Fig 1 (FAR/FRR CI) to {output_path}")
        return output_path

    def plot_bootstrap_distributions(
        self,
        bootstrap_result: BootstrapResult,
        output_filename: str = "fig2_bootstrap_distributions.png",
    ) -> Path:
        """Figure 2: Plot multi-panel histograms of bootstrap metric distributions."""
        output_path = self.output_dir / output_filename
        fig, axes = plt.subplots(2, 2, figsize=(10, 8), dpi=self.FIGURE_DPI)

        panels = [
            ("far", "Operational FAR (%)", self.COLOR_IMPOSTOR, axes[0, 0]),
            ("frr", "Operational FRR (%)", self.COLOR_GENUINE, axes[0, 1]),
            ("eer", "Diagnostic EER (%)", self.COLOR_THRESHOLD, axes[1, 0]),
            ("roc_auc", "ROC-AUC Score", self.COLOR_ACCENT, axes[1, 1]),
        ]

        dists = bootstrap_result.distributions
        cis = bootstrap_result.confidence_intervals.metrics

        for key, label, color, ax in panels:
            raw_vals = np.asarray(dists.get(key, []), dtype=np.float64)
            vals = raw_vals * 100.0 if key != "roc_auc" else raw_vals
            ci = cis[key]

            ci_low = ci.ci_lower * 100.0 if key != "roc_auc" else ci.ci_lower
            ci_high = ci.ci_upper * 100.0 if key != "roc_auc" else ci.ci_upper
            pt = ci.point_estimate * 100.0 if key != "roc_auc" else ci.point_estimate

            ax.hist(vals, bins=35, density=True, alpha=0.5, color=color, edgecolor="black", lw=0.8)

            if len(vals) > 5 and np.std(vals) > 1e-9:
                kde = gaussian_kde(vals)
                x_grid = np.linspace(np.min(vals), np.max(vals), 200)
                ax.plot(x_grid, kde(x_grid), color=color, lw=2.2)

            ax.axvline(pt, color="black", linestyle="-", lw=2, label=f"Point Est: {pt:.3f}")
            ax.axvline(ci_low, color="red", linestyle="--", lw=1.5, label=f"95% CI: [{ci_low:.3f}, {ci_high:.3f}]")
            ax.axvline(ci_high, color="red", linestyle="--", lw=1.5)

            ax.set_xlabel(label, fontsize=10, fontweight="bold")
            ax.set_ylabel("Density", fontsize=10, fontweight="bold")
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.legend(loc="upper right", fontsize=8.5)

        fig.suptitle(
            f"Speaker-Cluster Bootstrap Sampling Distributions (B = {bootstrap_result.iterations_valid:,} Replicates)",
            fontsize=12,
            fontweight="bold",
            y=0.99,
        )
        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved Fig 2 (Bootstrap Distributions) to {output_path}")
        return output_path

    def plot_seed_eer_distribution(
        self,
        seed_results: List[RandomSeedRunResult],
        output_filename: str = "fig3_seed_eer_distribution.png",
    ) -> Path:
        """Figure 3: Plot EER and accuracy across random seeds."""
        output_path = self.output_dir / output_filename
        fig, ax = plt.subplots(figsize=(8, 5), dpi=self.FIGURE_DPI)

        seeds = [r.seed for r in seed_results]
        dev_eers = [r.dev_eer_percent for r in seed_results]
        test_eers = [r.test_eer_diagnostic_percent for r in seed_results]
        base_mask = [r.is_primary_baseline for r in seed_results]

        x = np.arange(len(seeds))
        width = 0.35

        rects1 = ax.bar(x - width / 2.0, dev_eers, width, label="Dev EER (%)", color=self.COLOR_GENUINE, alpha=0.85)
        rects2 = ax.bar(x + width / 2.0, test_eers, width, label="Test EER (%)", color=self.COLOR_ACCENT, alpha=0.85)

        # Highlight baseline seed 42
        for i, is_base in enumerate(base_mask):
            if is_base:
                rects1[i].set_edgecolor("black")
                rects1[i].set_linewidth(2.0)
                rects2[i].set_edgecolor("black")
                rects2[i].set_linewidth(2.0)

        # Add labels
        for rect in rects1:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.0, h + 0.1, f"{h:.2f}%", ha="center", va="bottom", fontsize=8.5)
        for rect in rects2:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.0, h + 0.1, f"{h:.2f}%", ha="center", va="bottom", fontsize=8.5)

        labels = [f"Seed {s}\n(Baseline)" if s == 42 else f"Seed {s}" for s in seeds]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10, fontweight="bold")
        ax.set_ylabel("Equal Error Rate (%)", fontsize=11, fontweight="bold")
        ax.set_title("Enrollment Selection Stability Across 5 Random Seeds", fontsize=12, fontweight="bold", pad=12)
        ax.set_ylim([0, max(max(dev_eers), max(test_eers)) + 1.2])
        ax.grid(True, linestyle=":", alpha=0.6, axis="y")
        ax.legend(loc="upper right")

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved Fig 3 (Seed EER Distribution) to {output_path}")
        return output_path

    def plot_enrollment_count_vs_eer(
        self,
        count_results: List[EnrollmentCountRunResult],
        output_filename: str = "fig4_enrollment_count_vs_eer.png",
    ) -> Path:
        """Figure 4: Plot enrollment recording count (K = 1, 2, 3) vs. EER."""
        output_path = self.output_dir / output_filename
        fig, ax = plt.subplots(figsize=(7, 5), dpi=self.FIGURE_DPI)

        counts = [r.enrollment_count for r in count_results]
        dev_eers = [r.dev_eer_percent for r in count_results]
        test_eers = [r.test_eer_diagnostic_percent for r in count_results]

        ax.plot(counts, dev_eers, marker="o", color=self.COLOR_GENUINE, lw=2.5, markersize=8, label="Development EER (%)")
        ax.plot(counts, test_eers, marker="s", color=self.COLOR_IMPOSTOR, lw=2.5, markersize=8, label="Test Diagnostic EER (%)")

        for c, d, t in zip(counts, dev_eers, test_eers):
            ax.text(c, d + 0.15, f"{d:.2f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color=self.COLOR_GENUINE)
            ax.text(c, t - 0.25, f"{t:.2f}%", ha="center", va="top", fontsize=9, fontweight="bold", color=self.COLOR_IMPOSTOR)

        ax.set_xticks(counts)
        ax.set_xticklabels([f"K = {c} Utterance{'s' if c > 1 else ''}" for c in counts], fontsize=10, fontweight="bold")
        ax.set_xlabel("Enrollment Utterance Count per Speaker", fontsize=11, fontweight="bold")
        ax.set_ylabel("Equal Error Rate (%)", fontsize=11, fontweight="bold")
        ax.set_title("Equal Error Rate vs. Enrollment Utterance Count", fontsize=12, fontweight="bold", pad=12)
        ax.set_ylim([0, max(max(dev_eers), max(test_eers)) + 1.2])
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper right")

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved Fig 4 (Enrollment Count vs EER) to {output_path}")
        return output_path

    def plot_enrollment_count_vs_far_frr(
        self,
        count_results: List[EnrollmentCountRunResult],
        output_filename: str = "fig5_enrollment_count_vs_far_frr.png",
    ) -> Path:
        """Figure 5: Plot enrollment recording count vs. operational FAR and FRR."""
        output_path = self.output_dir / output_filename
        fig, ax = plt.subplots(figsize=(7, 5), dpi=self.FIGURE_DPI)

        counts = [r.enrollment_count for r in count_results]
        fars = [r.test_far_percent for r in count_results]
        frrs = [r.test_frr_percent for r in count_results]

        ax.plot(counts, fars, marker="^", color=self.COLOR_IMPOSTOR, lw=2.5, markersize=8, label="Operational FAR (%)")
        ax.plot(counts, frrs, marker="v", color=self.COLOR_GENUINE, lw=2.5, markersize=8, label="Operational FRR (%)")

        for c, fa, fr in zip(counts, fars, frrs):
            ax.text(c, fa + 0.15, f"{fa:.2f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color=self.COLOR_IMPOSTOR)
            ax.text(c, fr - 0.25, f"{fr:.2f}%", ha="center", va="top", fontsize=9, fontweight="bold", color=self.COLOR_GENUINE)

        ax.set_xticks(counts)
        ax.set_xticklabels([f"K = {c}" for c in counts], fontsize=10, fontweight="bold")
        ax.set_xlabel("Enrollment Utterance Count per Speaker", fontsize=11, fontweight="bold")
        ax.set_ylabel("Error Rate (%)", fontsize=11, fontweight="bold")
        ax.set_title("Operational FAR & FRR vs. Enrollment Utterance Count", fontsize=12, fontweight="bold", pad=12)
        ax.set_ylim([0, max(max(fars), max(frrs)) + 1.2])
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper right")

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved Fig 5 (Enrollment Count vs FAR/FRR) to {output_path}")
        return output_path

    def plot_threshold_sensitivity(
        self,
        sensitivity_summary: ThresholdSensitivitySummary,
        output_filename: str = "fig6_threshold_sensitivity.png",
    ) -> Path:
        """Figure 6: Plot metric sensitivity across threshold sweep."""
        output_path = self.output_dir / output_filename
        fig, ax1 = plt.subplots(figsize=(8, 5.5), dpi=self.FIGURE_DPI)

        pts = sensitivity_summary.points
        thresholds = [p.threshold for p in pts]
        far_pct = [p.far_percent for p in pts]
        frr_pct = [p.frr_percent for p in pts]
        acc_pct = [p.accuracy_percent for p in pts]

        # Shaded 5% error stability window
        w_min, w_max = sensitivity_summary.stable_threshold_window_5pct
        ax1.axvspan(w_min, w_max, color="green", alpha=0.10, label=f"5% Error Tolerance [{w_min:.3f}, {w_max:.3f}]")

        # Baseline threshold marker
        base_th = sensitivity_summary.baseline_threshold
        ax1.axvline(base_th, color=self.COLOR_THRESHOLD, linestyle="--", lw=2, label=f"Calibrated θ* = {base_th:.4f}")

        # Plot FAR and FRR on primary y-axis
        l1 = ax1.plot(thresholds, far_pct, color=self.COLOR_IMPOSTOR, lw=2.2, label="FAR (%)")
        l2 = ax1.plot(thresholds, frr_pct, color=self.COLOR_GENUINE, lw=2.2, label="FRR (%)")
        ax1.set_xlabel("Decision Threshold (Cosine Similarity)", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Error Rate (%)", fontsize=11, fontweight="bold")
        ax1.set_ylim([-1, 35])
        ax1.grid(True, linestyle=":", alpha=0.6)

        # Accuracy on secondary y-axis
        ax2 = ax1.twinx()
        l3 = ax2.plot(thresholds, acc_pct, color=self.COLOR_ACCENT, lw=2.0, linestyle="-.", label="Accuracy (%)")
        ax2.set_ylabel("Accuracy (%)", fontsize=11, fontweight="bold", color=self.COLOR_ACCENT)
        ax2.set_ylim([70, 101])

        # Combined legend
        lines = l1 + l2 + l3
        labels = [l.get_label() for l in lines]
        ax1.legend(loc="upper left", framealpha=0.9)

        ax1.set_title(
            f"Decision Threshold Sensitivity & Stability Window ({sensitivity_summary.dataset_name})",
            fontsize=12,
            fontweight="bold",
            pad=12,
        )

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved Fig 6 (Threshold Sensitivity) to {output_path}")
        return output_path

    def plot_speaker_error_distribution(
        self,
        error_summary: ErrorAnalysisSummary,
        output_filename: str = "fig7_speaker_error_distribution.png",
    ) -> Path:
        """Figure 7: Horizontal bar chart of top rejected genuine speakers and accepted impostors."""
        output_path = self.output_dir / output_filename
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), dpi=self.FIGURE_DPI)

        # Subplot 1: Top False Rejections (Genuine speakers)
        top_fr = error_summary.top_rejected_speakers[:8]
        if top_fr:
            spk_fr = [item["speaker_id"] for item in reversed(top_fr)]
            cnt_fr = [item["false_rejection_count"] for item in reversed(top_fr)]
            ax1.barh(spk_fr, cnt_fr, color=self.COLOR_GENUINE, alpha=0.85, edgecolor="black")
            for i, v in enumerate(cnt_fr):
                ax1.text(v + 0.3, i, str(v), va="center", fontsize=9, fontweight="bold")
            ax1.set_xlim([0, max(cnt_fr) + 3])
        ax1.set_xlabel("False Rejection Count", fontsize=10, fontweight="bold")
        ax1.set_ylabel("Speaker ID", fontsize=10, fontweight="bold")
        ax1.set_title("Most Frequently Rejected Genuine Speakers", fontsize=10.5, fontweight="bold")
        ax1.grid(True, linestyle=":", alpha=0.6, axis="x")

        # Subplot 2: Top False Acceptances (Impostor speakers)
        top_fa = error_summary.top_accepted_impostors[:8]
        if top_fa:
            spk_fa = [item["speaker_id"] for item in reversed(top_fa)]
            cnt_fa = [item["false_acceptance_count"] for item in reversed(top_fa)]
            ax2.barh(spk_fa, cnt_fa, color=self.COLOR_IMPOSTOR, alpha=0.85, edgecolor="black")
            for i, v in enumerate(cnt_fa):
                ax2.text(v + 0.1, i, str(v), va="center", fontsize=9, fontweight="bold")
            ax2.set_xlim([0, max(cnt_fa) + 1.5])
        ax2.set_xlabel("False Acceptance Count", fontsize=10, fontweight="bold")
        ax2.set_title("Speakers Involved in False Acceptances", fontsize=10.5, fontweight="bold")
        ax2.grid(True, linestyle=":", alpha=0.6, axis="x")

        fig.suptitle(
            f"Speaker-Level Error Distribution (Total Errors = {error_summary.total_errors:,} at θ* = {error_summary.decision_threshold:.4f})",
            fontsize=12,
            fontweight="bold",
            y=0.99,
        )
        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.FIGURE_DPI)
        plt.close(fig)
        logger.info(f"Saved Fig 7 (Speaker Error Distribution) to {output_path}")
        return output_path

    def generate_all_robustness_figures(
        self,
        bootstrap_result: BootstrapResult,
        seed_results: List[RandomSeedRunResult],
        count_results: List[EnrollmentCountRunResult],
        sensitivity_summary: ThresholdSensitivitySummary,
        error_summary: ErrorAnalysisSummary,
    ) -> Dict[str, Path]:
        """Generate and save all 7 publication figures."""
        paths = {}
        paths["far_frr_ci"] = self.plot_far_frr_ci(bootstrap_result)
        paths["bootstrap_distributions"] = self.plot_bootstrap_distributions(bootstrap_result)
        paths["seed_eer_distribution"] = self.plot_seed_eer_distribution(seed_results)
        paths["enrollment_count_vs_eer"] = self.plot_enrollment_count_vs_eer(count_results)
        paths["enrollment_count_vs_far_frr"] = self.plot_enrollment_count_vs_far_frr(count_results)
        paths["threshold_sensitivity"] = self.plot_threshold_sensitivity(sensitivity_summary)
        paths["speaker_error_distribution"] = self.plot_speaker_error_distribution(error_summary)
        return paths

