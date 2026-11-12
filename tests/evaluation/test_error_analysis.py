"""Unit tests for Error Analysis Engine (Phase 5D)."""

import json
from pathlib import Path
from typing import List
import numpy as np
import pytest

from sentinelai.evaluation.error_analysis import (
    ErrorAnalysisSummary,
    ErrorAnalyzer,
    SanitizedErrorRecord,
)
from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial


@pytest.fixture
def mock_dataset_with_errors() -> ScoredDataset:
    """Create scored dataset with known false rejections and false acceptances.

    Decision threshold: 0.60
    """
    trials = [
        # Correct genuine (TP)
        ScoredTrial("t1", "spk1", "spk1", "genuine", 1, 0.85, "test", "test-model"),
        # False Rejection 1 (boundary: score=0.58, dist=0.02)
        ScoredTrial("t2", "spk1", "spk1", "genuine", 1, 0.58, "test", "test-model"),
        # False Rejection 2 (distant: score=0.45, dist=0.15)
        ScoredTrial("t3", "spk2", "spk2", "genuine", 1, 0.45, "test", "test-model"),
        # Correct impostor (TN)
        ScoredTrial("t4", "spk1", "spk2", "impostor", 0, 0.30, "test", "test-model"),
        # False Acceptance 1 (boundary: score=0.62, dist=0.02)
        ScoredTrial("t5", "spk1", "spk3", "impostor", 0, 0.62, "test", "test-model"),
    ]
    scores = np.array([t.similarity_score for t in trials], dtype=np.float64)
    labels = np.array([t.ground_truth_label for t in trials], dtype=np.int64)
    return ScoredDataset("test-clean", trials, scores, labels)


class TestErrorAnalyzer:
    """Test suite for ErrorAnalyzer."""

    def test_classify_fr_and_fa(self, mock_dataset_with_errors: ScoredDataset) -> None:
        """Verify correct identification of false rejections and false acceptances."""
        analyzer = ErrorAnalyzer(boundary_margin=0.05)
        summary = analyzer.analyze(mock_dataset_with_errors, threshold=0.60)

        assert summary.total_trials == 5
        assert summary.total_errors == 3
        assert summary.false_rejections_count == 2
        assert summary.false_acceptances_count == 1

        # Check boundary count: t2 (dist 0.02) and t5 (dist 0.02) are boundary
        assert summary.boundary_errors_count == 2

    def test_top_speakers_ranking(self, mock_dataset_with_errors: ScoredDataset) -> None:
        """Verify identification of top rejected genuine speakers and accepted impostors."""
        analyzer = ErrorAnalyzer(boundary_margin=0.05)
        summary = analyzer.analyze(mock_dataset_with_errors, threshold=0.60)

        rejected_spks = {item["speaker_id"] for item in summary.top_rejected_speakers}
        assert "spk1" in rejected_spks
        assert "spk2" in rejected_spks

        accepted_impostors = {item["speaker_id"] for item in summary.top_accepted_impostors}
        assert "spk3" in accepted_impostors

    def test_sanitization_and_json_export(
        self, mock_dataset_with_errors: ScoredDataset, tmp_path: Path
    ) -> None:
        """Verify sanitized error records contain no raw embeddings."""
        analyzer = ErrorAnalyzer()
        summary = analyzer.analyze(mock_dataset_with_errors, threshold=0.60)

        json_path = tmp_path / "errors.json"
        summary.save_json(json_path)
        assert json_path.exists()

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_errors"] == 3
        # Check first error record
        err0 = data["sanitized_errors"][0]
        assert "similarity_score" in err0
        assert "distance_to_threshold" in err0
        assert "embedding" not in err0
        assert "audio_bytes" not in err0

