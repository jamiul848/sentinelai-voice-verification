"""Unit tests for Confidence Interval calculations (Phase 5D)."""

import json
from pathlib import Path
import numpy as np
import pytest

from sentinelai.evaluation.confidence_intervals import (
    EvaluationConfidenceIntervals,
    MetricConfidenceInterval,
    compute_metric_confidence_interval,
)


class TestConfidenceIntervals:
    """Test suite for MetricConfidenceInterval and compute_metric_confidence_interval."""

    def test_compute_metric_ci_normal_distribution(self) -> None:
        """Verify empirical 95% CI on a known normal distribution."""
        rng = np.random.default_rng(42)
        samples = rng.normal(loc=0.50, scale=0.05, size=1000)

        ci = compute_metric_confidence_interval(
            metric_name="test_metric",
            point_estimate=0.50,
            replicates=samples,
            confidence_level=0.95,
        )

        assert ci.metric_name == "test_metric"
        assert ci.point_estimate == 0.50
        assert pytest.approx(ci.mean, abs=0.01) == 0.50
        assert pytest.approx(ci.median, abs=0.01) == 0.50
        # 95% of normal is within roughly mean +/- 1.96 * std = 0.50 +/- 0.098
        assert 0.38 <= ci.ci_lower <= 0.42
        assert 0.58 <= ci.ci_upper <= 0.62
        assert ci.ci_lower <= ci.median <= ci.ci_upper

    def test_ci_serialization_to_dict_and_json(self, tmp_path: Path) -> None:
        """Verify serialization and formatting of confidence intervals."""
        ci = MetricConfidenceInterval(
            metric_name="far",
            point_estimate=0.0194,
            mean=0.0195,
            median=0.0193,
            std_err=0.0035,
            ci_lower=0.0135,
            ci_upper=0.0270,
            confidence_level=0.95,
        )

        d = ci.to_dict()
        assert d["metric_name"] == "far"
        assert d["point_estimate"] == 0.0194
        assert "[1.35%, 2.70%]" in d["formatted_ci_95"]

        container = EvaluationConfidenceIntervals(
            dataset_name="test-clean",
            resampling_unit="speaker_cluster",
            iterations=1000,
            valid_replicates=1000,
            metrics={"far": ci},
            metadata={"note": "test"},
        )

        json_path = tmp_path / "ci.json"
        container.save_json(json_path)
        assert json_path.exists()

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["dataset_name"] == "test-clean"
        assert data["iterations"] == 1000
        assert "far" in data["metrics"]

    def test_empty_replicates_raises_error(self) -> None:
        """Verify ValueError when passing empty replicate array."""
        with pytest.raises(ValueError, match="cannot be empty"):
            compute_metric_confidence_interval("test", 0.5, [])

    def test_non_finite_replicates_raises_error(self) -> None:
        """Verify ValueError when passing NaN or Inf."""
        with pytest.raises(ValueError, match="non-finite"):
            compute_metric_confidence_interval("test", 0.5, [0.1, np.nan, 0.3])

        with pytest.raises(ValueError, match="non-finite"):
            compute_metric_confidence_interval("test", 0.5, [0.1, np.inf, 0.3])

    def test_invalid_confidence_level_raises_error(self) -> None:
        """Verify ValueError when confidence_level is outside (0, 1)."""
        with pytest.raises(ValueError, match="confidence_level"):
            compute_metric_confidence_interval("test", 0.5, [0.1, 0.2], confidence_level=1.5)

