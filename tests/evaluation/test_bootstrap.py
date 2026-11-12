"""Unit tests for Speaker-Level Cluster Bootstrap (Phase 5D)."""

from typing import List
import numpy as np
import pytest

from sentinelai.evaluation.bootstrap import (
    BootstrapResult,
    SpeakerClusterBootstrap,
)
from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial


@pytest.fixture
def mock_scored_dataset() -> ScoredDataset:
    """Create small multi-speaker scored dataset for fast unit testing."""
    trials: List[ScoredTrial] = []
    # 5 speakers: spk_A, spk_B, spk_C, spk_D, spk_E
    speakers = ["spk_A", "spk_B", "spk_C", "spk_D", "spk_E"]

    # Genuine trials: 4 per speaker with overlap around threshold 0.60
    for spk_idx, spk in enumerate(speakers):
        for i in range(4):
            trials.append(
                ScoredTrial(
                    trial_id=f"gen_{spk}_{i}",
                    claimed_speaker_id=spk,
                    actual_speaker_id=spk,
                    trial_type="genuine",
                    ground_truth_label=1,
                    similarity_score=float(0.55 + (spk_idx * 0.06) + (i * 0.02)),
                    split="test",
                    model_identifier="test-model",
                )
            )

    # Impostor trials: 2 per pair with overlap around threshold 0.60
    for i, s1 in enumerate(speakers):
        for j, s2 in enumerate(speakers):
            if s1 != s2:
                for k in range(2):
                    trials.append(
                        ScoredTrial(
                            trial_id=f"imp_{s1}_{s2}_{k}",
                            claimed_speaker_id=s1,
                            actual_speaker_id=s2,
                            trial_type="impostor",
                            ground_truth_label=0,
                            similarity_score=float(0.40 + (i * 0.04) + (k * 0.03)),
                            split="test",
                            model_identifier="test-model",
                        )
                    )

    scores = np.array([t.similarity_score for t in trials], dtype=np.float64)
    labels = np.array([t.ground_truth_label for t in trials], dtype=np.int64)

    return ScoredDataset(
        split_name="mock-test",
        trials=trials,
        scores=scores,
        labels=labels,
        model_identifier="test-model",
    )


class TestSpeakerClusterBootstrap:
    """Test suite for SpeakerClusterBootstrap."""

    def test_bootstrap_reproducibility_same_seed(self, mock_scored_dataset: ScoredDataset) -> None:
        """Verify identical seed produces identical confidence intervals and distributions."""
        boot1 = SpeakerClusterBootstrap(iterations=25, seed=42)
        res1 = boot1.run(mock_scored_dataset, frozen_threshold=0.60)

        boot2 = SpeakerClusterBootstrap(iterations=25, seed=42)
        res2 = boot2.run(mock_scored_dataset, frozen_threshold=0.60)

        assert res1.iterations_valid == res2.iterations_valid
        for metric in ["far", "frr", "eer", "accuracy", "roc_auc"]:
            ci1 = res1.confidence_intervals.metrics[metric]
            ci2 = res2.confidence_intervals.metrics[metric]
            assert pytest.approx(ci1.mean) == ci2.mean
            assert pytest.approx(ci1.ci_lower) == ci2.ci_lower
            assert pytest.approx(ci1.ci_upper) == ci2.ci_upper

    def test_different_seeds_produce_variation(self, mock_scored_dataset: ScoredDataset) -> None:
        """Verify different seeds produce non-identical replicate samples."""
        boot1 = SpeakerClusterBootstrap(iterations=25, seed=42)
        res1 = boot1.run(mock_scored_dataset, frozen_threshold=0.60)

        boot2 = SpeakerClusterBootstrap(iterations=25, seed=999)
        res2 = boot2.run(mock_scored_dataset, frozen_threshold=0.60)

        # Compare metrics with non-zero variance (e.g. roc_auc or eer)
        assert res1.distributions["roc_auc"] != res2.distributions["roc_auc"]

    def test_ci_bounds_validity(self, mock_scored_dataset: ScoredDataset) -> None:
        """Verify lower CI <= median <= upper CI across all metrics."""
        boot = SpeakerClusterBootstrap(iterations=30, seed=42)
        res = boot.run(mock_scored_dataset, frozen_threshold=0.60)

        assert res.iterations_valid > 0
        for m_name, ci in res.confidence_intervals.metrics.items():
            assert ci.ci_lower <= ci.median <= ci.ci_upper, (
                f"Metric {m_name} violates bound: lower={ci.ci_lower}, median={ci.median}, upper={ci.ci_upper}"
            )
            assert 0.0 <= ci.ci_lower <= 1.0
            assert 0.0 <= ci.ci_upper <= 1.0

    def test_insufficient_speakers_raises_value_error(self) -> None:
        """Verify ValueError when dataset contains fewer than 2 speakers."""
        single_spk_trials = [
            ScoredTrial(
                trial_id="t1",
                claimed_speaker_id="spk_A",
                actual_speaker_id="spk_A",
                trial_type="genuine",
                ground_truth_label=1,
                similarity_score=0.8,
                split="test",
                model_identifier="test",
            )
        ]
        ds = ScoredDataset(
            split_name="single-spk",
            trials=single_spk_trials,
            scores=np.array([0.8]),
            labels=np.array([1]),
        )

        boot = SpeakerClusterBootstrap(iterations=10)
        with pytest.raises(ValueError, match="at least 2 unique speakers"):
            boot.run(ds, frozen_threshold=0.6)

    def test_bootstrap_result_serialization(self, mock_scored_dataset: ScoredDataset, tmp_path) -> None:
        """Verify BootstrapResult serialization to JSON."""
        boot = SpeakerClusterBootstrap(iterations=15, seed=42)
        res = boot.run(mock_scored_dataset, frozen_threshold=0.60)

        json_path = tmp_path / "bootstrap.json"
        res.save_json(json_path)
        assert json_path.exists()

        d = res.to_dict()
        assert d["iterations_valid"] == 15
        assert d["frozen_threshold"] == 0.60
        assert "confidence_intervals" in d
