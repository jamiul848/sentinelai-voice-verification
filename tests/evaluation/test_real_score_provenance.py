"""Tests for real score provenance, synthetic score rejection, and embedding integration."""

import csv
from pathlib import Path
import numpy as np
import pytest

from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial, TrialScorer
from sentinelai.verification.scoring import compute_verification_score


class TestRealScoreProvenance:
    """Verifies that the evaluation scoring engine enforces real inference provenance."""

    def test_synthetic_score_manifest_rejected_by_default(self, tmp_path: Path) -> None:
        """Score manifests with synthetic trial IDs ('synth-...') are strictly rejected."""
        scorer = TrialScorer()
        synthetic_csv = tmp_path / "synthetic_scores.csv"

        with open(synthetic_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=scorer.SCORE_CSV_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "trial_id": "synth-test-clean-00000",
                "claimed_speaker_id": "spk_0",
                "actual_speaker_id": "spk_0",
                "trial_type": "genuine",
                "ground_truth_label": 1,
                "similarity_score": 0.771234,
                "split": "test-clean",
                "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
                "score_source": "synthetic_demonstration",
            })

        # Must raise ValueError when loading without allow_synthetic=True
        with pytest.raises(ValueError) as exc_info:
            scorer.load_scores_csv(synthetic_csv, allow_synthetic=False)

        assert "Stale synthetic score manifest detected" in str(exc_info.value)
        assert "synth-test-clean-00000" in str(exc_info.value)

    def test_synthetic_manifest_allowed_when_explicitly_requested(self, tmp_path: Path) -> None:
        """Synthetic demonstration scores are only loaded when allow_synthetic=True."""
        scorer = TrialScorer()
        synthetic_csv = tmp_path / "synthetic_scores.csv"

        with open(synthetic_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=scorer.SCORE_CSV_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "trial_id": "synth-test-clean-00001",
                "claimed_speaker_id": "spk_1",
                "actual_speaker_id": "spk_1",
                "trial_type": "genuine",
                "ground_truth_label": 1,
                "similarity_score": 0.785000,
                "split": "test-clean",
                "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
                "score_source": "synthetic_demonstration",
            })

        ds = scorer.load_scores_csv(synthetic_csv, allow_synthetic=True)
        assert len(ds.trials) == 1
        assert ds.trials[0].trial_id == "synth-test-clean-00001"
        assert ds.trials[0].score_source == "synthetic_demonstration"

    def test_real_score_manifest_loaded_successfully(self, tmp_path: Path) -> None:
        """Real score manifests with UUIDs and physical speaker IDs load cleanly."""
        scorer = TrialScorer()
        real_csv = tmp_path / "real_scores.csv"

        with open(real_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=scorer.SCORE_CSV_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "trial_id": "1f68fa33-fe32-4638-a3d7-0b55b9d47410",
                "claimed_speaker_id": "1284",
                "actual_speaker_id": "1284",
                "trial_type": "genuine",
                "ground_truth_label": 1,
                "similarity_score": 0.779300,
                "split": "test-clean",
                "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
                "score_source": "real_ecapa_inference",
            })

        ds = scorer.load_scores_csv(real_csv, allow_synthetic=False)
        assert len(ds.trials) == 1
        assert ds.trials[0].trial_id == "1f68fa33-fe32-4638-a3d7-0b55b9d47410"
        assert ds.trials[0].claimed_speaker_id == "1284"
        assert ds.trials[0].score_source == "real_ecapa_inference"

    def test_missing_embedding_detection(self) -> None:
        """Missing probe or reference embedding raises KeyError with exact identifier."""
        scorer = TrialScorer()
        trial_rows = [
            {
                "trial_id": "uuid-001",
                "claimed_speaker_id": "speaker_A",
                "actual_speaker_id": "speaker_A",
                "trial_type": "genuine",
                "ground_truth_label": 1,
                "verification_recording_id": "rec_001",
            }
        ]

        # Missing reference embedding
        with pytest.raises(KeyError) as exc_info:
            scorer.score_trials(
                trial_rows,
                reference_embeddings={},
                probe_embeddings={"rec_001": np.ones(192, dtype=np.float32)},
                split_name="test-clean",
            )
        assert "speaker_A" in str(exc_info.value)

        # Missing probe embedding
        with pytest.raises(KeyError) as exc_info:
            scorer.score_trials(
                trial_rows,
                reference_embeddings={"speaker_A": np.ones(192, dtype=np.float32)},
                probe_embeddings={},
                split_name="test-clean",
            )
        assert "rec_001" in str(exc_info.value)

    def test_trial_to_score_identity_and_cosine_fidelity(self) -> None:
        """Scored trials preserve trial UUID, speaker IDs, and compute exact cosine similarity."""
        scorer = TrialScorer()
        
        # Two orthogonal unit vectors (similarity = 0.0)
        v1 = np.zeros(192, dtype=np.float32)
        v1[0] = 1.0
        v2 = np.zeros(192, dtype=np.float32)
        v2[1] = 1.0

        trial_rows = [
            {
                "trial_id": "test-uuid-999",
                "claimed_speaker_id": "1284",
                "actual_speaker_id": "1320",
                "trial_type": "impostor",
                "ground_truth_label": 0,
                "verification_recording_id": "1320-probe",
            }
        ]

        ds = scorer.score_trials(
            trial_rows,
            reference_embeddings={"1284": v1},
            probe_embeddings={"1320-probe": v2},
            split_name="test-clean",
        )

        assert len(ds.trials) == 1
        t = ds.trials[0]
        assert t.trial_id == "test-uuid-999"
        assert t.claimed_speaker_id == "1284"
        assert t.actual_speaker_id == "1320"
        assert t.score_source == "real_ecapa_inference"
        assert pytest.approx(t.similarity_score, abs=1e-5) == 0.0

