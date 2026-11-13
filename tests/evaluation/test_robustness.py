"""Unit tests for Multi-Seed and Enrollment Count Robustness Experiments (Phase 5D)."""

from pathlib import Path
from typing import List
import numpy as np
import pytest

from sentinelai.evaluation.robustness import (
    EnrollmentCountRunResult,
    RandomSeedRunResult,
    RobustnessAnalyzer,
)
from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial


@pytest.fixture
def mock_datasets() -> tuple[ScoredDataset, ScoredDataset]:
    """Create paired development and test mock datasets."""
    rng = np.random.default_rng(42)

    # Dev split
    dev_gen = rng.normal(0.78, 0.08, size=200)
    dev_imp = rng.normal(0.42, 0.08, size=100)
    dev_scores = np.clip(np.concatenate([dev_gen, dev_imp]), -1.0, 1.0)
    dev_labels = np.concatenate([np.ones(200, dtype=np.int64), np.zeros(100, dtype=np.int64)])
    dev_ds = ScoredDataset(
        split_name="dev-clean",
        trials=[],
        scores=dev_scores,
        labels=dev_labels,
    )

    # Test split
    test_gen = rng.normal(0.79, 0.07, size=200)
    test_imp = rng.normal(0.40, 0.08, size=100)
    test_scores = np.clip(np.concatenate([test_gen, test_imp]), -1.0, 1.0)
    test_labels = np.concatenate([np.ones(200, dtype=np.int64), np.zeros(100, dtype=np.int64)])
    test_ds = ScoredDataset(
        split_name="test-clean",
        trials=[],
        scores=test_scores,
        labels=test_labels,
    )

    return dev_ds, test_ds


class TestRobustnessAnalyzer:
    """Test suite for RobustnessAnalyzer multi-seed and enrollment count experiments."""

    def test_multi_seed_anchors_baseline_seed_42(
        self, mock_datasets: tuple[ScoredDataset, ScoredDataset], tmp_path: Path
    ) -> None:
        """Verify Seed 42 is anchored and flagged as the primary baseline."""
        dev_ds, test_ds = mock_datasets
        analyzer = RobustnessAnalyzer(output_dir=tmp_path)

        results = analyzer.evaluate_multi_seed_experiments(
            dev_ds, test_ds, seeds=[42, 123]
        )

        assert len(results) == 2
        r42 = next(r for r in results if r.seed == 42)
        r123 = next(r for r in results if r.seed == 123)

        assert r42.is_primary_baseline is True
        assert r123.is_primary_baseline is False
        assert 0.50 <= r42.calibrated_threshold <= 0.70
        assert 0.0 <= r42.test_far <= 0.10

    def test_multi_seed_csv_export(
        self, mock_datasets: tuple[ScoredDataset, ScoredDataset], tmp_path: Path
    ) -> None:
        """Verify saving multi-seed results to CSV."""
        dev_ds, test_ds = mock_datasets
        analyzer = RobustnessAnalyzer(output_dir=tmp_path)
        results = analyzer.evaluate_multi_seed_experiments(dev_ds, test_ds, seeds=[42, 123, 456])

        csv_path = analyzer.save_random_seed_results_csv(results)
        assert csv_path.exists()

        content = csv_path.read_text(encoding="utf-8")
        assert "seed,is_primary_baseline" in content
        assert "42,True" in content

    def test_enrollment_count_nested_conditions(
        self, mock_datasets: tuple[ScoredDataset, ScoredDataset], tmp_path: Path
    ) -> None:
        """Verify evaluation of nested conditions K=1, 2, 3."""
        dev_ds, test_ds = mock_datasets
        analyzer = RobustnessAnalyzer(output_dir=tmp_path)

        results = analyzer.evaluate_enrollment_count_experiments(
            dev_ds, test_ds, counts=[1, 2, 3]
        )

        assert len(results) == 3
        k3 = next(r for r in results if r.enrollment_count == 3)
        assert k3.is_primary_baseline is True

        csv_path = analyzer.save_enrollment_count_results_csv(results)
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")
        assert "enrollment_count,is_primary_baseline" in content
        assert "3,True" in content

