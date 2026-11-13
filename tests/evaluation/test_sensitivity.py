"""Unit tests for Threshold Sensitivity Analyzer (Phase 5D)."""

from pathlib import Path
import numpy as np
import pytest

from sentinelai.evaluation.sensitivity import (
    ThresholdSensitivityAnalyzer,
    ThresholdSensitivityPoint,
    ThresholdSensitivitySummary,
)
from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial


@pytest.fixture
def mock_dataset() -> ScoredDataset:
    """Create scored dataset for sensitivity sweep testing."""
    rng = np.random.default_rng(42)
    gen = rng.normal(0.78, 0.08, size=300)
    imp = rng.normal(0.42, 0.08, size=150)
    scores = np.clip(np.concatenate([gen, imp]), -1.0, 1.0)
    labels = np.concatenate([np.ones(300, dtype=np.int64), np.zeros(150, dtype=np.int64)])
    return ScoredDataset("test-clean", [], scores, labels)


class TestThresholdSensitivityAnalyzer:
    """Test suite for ThresholdSensitivityAnalyzer."""

    def test_sweep_points_and_tradeoff(self, mock_dataset: ScoredDataset) -> None:
        """Verify sweep produces points with monotonic error trade-offs."""
        analyzer = ThresholdSensitivityAnalyzer(
            min_threshold=0.55, max_threshold=0.65, step=0.01
        )
        summary = analyzer.analyze(mock_dataset, baseline_threshold=0.60)

        assert len(summary.points) == 11
        thresholds = [p.threshold for p in summary.points]
        far_vals = [p.far_percent for p in summary.points]
        frr_vals = [p.frr_percent for p in summary.points]

        assert min(thresholds) == 0.55
        assert max(thresholds) == 0.65

        # FAR must decrease or stay flat as threshold increases
        assert all(far_vals[i] >= far_vals[i + 1] - 1e-6 for i in range(len(far_vals) - 1))
        # FRR must increase or stay flat as threshold increases
        assert all(frr_vals[i] <= frr_vals[i + 1] + 1e-6 for i in range(len(frr_vals) - 1))

    def test_baseline_threshold_flagged(self, mock_dataset: ScoredDataset) -> None:
        """Verify the point matching the baseline threshold has is_calibrated_baseline=True."""
        analyzer = ThresholdSensitivityAnalyzer(
            min_threshold=0.55, max_threshold=0.65, step=0.01
        )
        summary = analyzer.analyze(mock_dataset, baseline_threshold=0.60)

        baseline_pts = [p for p in summary.points if p.is_calibrated_baseline]
        assert len(baseline_pts) == 1
        assert pytest.approx(baseline_pts[0].threshold) == 0.60

    def test_stable_window_identified(self, mock_dataset: ScoredDataset) -> None:
        """Verify calculation of 5% error tolerance window."""
        analyzer = ThresholdSensitivityAnalyzer(
            min_threshold=0.50, max_threshold=0.70, step=0.01
        )
        summary = analyzer.analyze(mock_dataset, baseline_threshold=0.60)

        w_min, w_max = summary.stable_threshold_window_5pct
        assert w_min <= 0.60 <= w_max

    def test_csv_export(self, mock_dataset: ScoredDataset, tmp_path: Path) -> None:
        """Verify saving sensitivity sweep to CSV."""
        analyzer = ThresholdSensitivityAnalyzer(
            min_threshold=0.58, max_threshold=0.62, step=0.01
        )
        summary = analyzer.analyze(mock_dataset, baseline_threshold=0.60)

        csv_path = summary.save_csv(tmp_path / "sensitivity.csv")
        assert csv_path.exists()

        content = csv_path.read_text(encoding="utf-8")
        assert "threshold,is_calibrated_baseline,far_percent,frr_percent" in content
        assert "0.6,True" in content or "0.60,True" in content or "0.6000,True" in content

