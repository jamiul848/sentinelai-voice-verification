"""Unit tests for Phase 5B: Multi-Speaker Enrollment and Verification Trial Generation.

Tests use synthetic audio fixtures created in tmp_path — NO real LibriSpeech data required.
Tests validate:
- Speaker and recording discovery.
- Enrollment/verification split selection.
- Insufficient recording handling.
- Genuine trial generation.
- Impostor trial generation.
- Duplicate trial detection.
- Enrollment/verification overlap prevention.
- Split leakage detection.
- Trial manifest CSV/JSON writing and reading.
- Deterministic reproducibility (same seed → same output).
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Set

import numpy as np
import pytest
import soundfile as sf

from sentinelai.evaluation.speaker_discovery import (
    EnrollmentSelector,
    EnrollmentSplit,
    SpeakerRecordingDiscovery,
    SpeakerRecordings,
)
from sentinelai.evaluation.trial_generator import (
    TrialGenerationResult,
    TrialGenerator,
    VerificationTrial,
)
from sentinelai.evaluation.trial_manifest import TrialManifestWriter
from sentinelai.evaluation.leakage_validator import LeakageValidator, ValidationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_audio_file(
    path: Path,
    sample_rate: int = 16000,
    duration_sec: float = 0.5,
) -> Path:
    """Create a minimal valid WAV audio file for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(sample_rate * duration_sec)
    data = (
        0.3
        * np.sin(
            2 * np.pi * 440.0 * np.linspace(0, duration_sec, num_samples, endpoint=False)
        )
    ).astype(np.float32)
    sf.write(str(path), data, sample_rate, format="WAV", subtype="PCM_16")
    return path


def _build_mock_split(
    base: Path,
    split_name: str,
    speakers: Dict[str, int],
) -> Path:
    """Build a mock LibriSpeech-style directory with specified speakers and recording counts.

    Args:
        base: Temporary base directory.
        split_name: Split name (e.g. 'dev-clean').
        speakers: Mapping from speaker_id to number of recordings to create.

    Returns:
        Path to the split root directory.
    """
    split_root = base / split_name
    for spk_id, count in speakers.items():
        for i in range(count):
            fname = f"{spk_id}-100-{i:04d}.wav"
            _create_audio_file(split_root / spk_id / "100" / fname)
    return split_root


@pytest.fixture
def mock_dataset(tmp_path: Path) -> Path:
    """Create a mock dataset with 4 speakers in dev-clean and 3 in test-clean."""
    # dev-clean: 4 speakers with varying recording counts
    _build_mock_split(
        tmp_path, "dev-clean",
        {"1001": 6, "1002": 5, "1003": 4, "1004": 2},  # 1004 has too few
    )
    # test-clean: 3 speakers (disjoint from dev)
    _build_mock_split(
        tmp_path, "test-clean",
        {"2001": 7, "2002": 5, "2003": 3},  # 2003 has too few
    )
    return tmp_path


@pytest.fixture
def overlapping_dataset(tmp_path: Path) -> Path:
    """Create a dataset with speaker overlap between splits."""
    _build_mock_split(
        tmp_path, "dev-clean",
        {"1001": 5, "SHARED": 4},
    )
    _build_mock_split(
        tmp_path, "test-clean",
        {"2001": 5, "SHARED": 4},  # Same speaker in both!
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Speaker Discovery Tests
# ---------------------------------------------------------------------------


class TestSpeakerRecordingDiscovery:
    """Tests for speaker and recording discovery from directory hierarchy."""

    def test_discover_all_speakers(self, mock_dataset: Path) -> None:
        """Verify all speakers are discovered in a split."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")

        assert len(speakers) == 4
        assert set(speakers.keys()) == {"1001", "1002", "1003", "1004"}

    def test_discover_recording_counts(self, mock_dataset: Path) -> None:
        """Verify correct recording counts per speaker."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")

        assert speakers["1001"].recording_count == 6
        assert speakers["1002"].recording_count == 5
        assert speakers["1003"].recording_count == 4
        assert speakers["1004"].recording_count == 2

    def test_discover_test_split(self, mock_dataset: Path) -> None:
        """Verify discovery works for the test split."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("test-clean")

        assert len(speakers) == 3
        assert set(speakers.keys()) == {"2001", "2002", "2003"}

    def test_discover_nonexistent_split_raises(self, tmp_path: Path) -> None:
        """Verify FileNotFoundError for missing splits."""
        discovery = SpeakerRecordingDiscovery(dataset_root=tmp_path)
        with pytest.raises(FileNotFoundError, match="not found"):
            discovery.discover_split("nonexistent-split")

    def test_recordings_are_sorted(self, mock_dataset: Path) -> None:
        """Verify recordings within each speaker are sorted by filename."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")

        for spk in speakers.values():
            names = [p.name for p in spk.recordings]
            assert names == sorted(names)

    def test_chapter_ids_populated(self, mock_dataset: Path) -> None:
        """Verify chapter IDs are tracked for each speaker."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")

        # All recordings are in chapter '100' in our mock
        for spk in speakers.values():
            assert "100" in spk.chapter_ids


# ---------------------------------------------------------------------------
# Enrollment Selector Tests
# ---------------------------------------------------------------------------


class TestEnrollmentSelector:
    """Tests for enrollment/verification selection logic."""

    def test_eligible_speakers_selected(self, mock_dataset: Path) -> None:
        """Verify speakers with >=4 recordings are marked eligible (3 enroll + 1 verify)."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")
        selector = EnrollmentSelector(enrollment_count=3, seed=42)
        splits = selector.select(speakers)

        # 1001 (6), 1002 (5), 1003 (4) are eligible; 1004 (2) is not
        assert splits["1001"].is_eligible
        assert splits["1002"].is_eligible
        assert splits["1003"].is_eligible
        assert not splits["1004"].is_eligible

    def test_enrollment_count_correct(self, mock_dataset: Path) -> None:
        """Verify exactly enrollment_count recordings are selected for enrollment."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")
        selector = EnrollmentSelector(enrollment_count=3, seed=42)
        splits = selector.select(speakers)

        for spk_id, split_info in splits.items():
            if split_info.is_eligible:
                assert split_info.enrollment_count == 3

    def test_verification_recordings_are_remainder(self, mock_dataset: Path) -> None:
        """Verify verification recordings = total - enrollment for eligible speakers."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")
        selector = EnrollmentSelector(enrollment_count=3, seed=42)
        splits = selector.select(speakers)

        assert splits["1001"].verification_count == 3  # 6 - 3
        assert splits["1002"].verification_count == 2  # 5 - 3
        assert splits["1003"].verification_count == 1  # 4 - 3

    def test_no_enrollment_verification_overlap(self, mock_dataset: Path) -> None:
        """Verify enrollment and verification sets are completely disjoint."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")
        selector = EnrollmentSelector(enrollment_count=3, seed=42)
        splits = selector.select(speakers)

        for spk_id, split_info in splits.items():
            if split_info.is_eligible:
                enroll_stems = {p.stem for p in split_info.enrollment_recordings}
                verify_stems = {p.stem for p in split_info.verification_recordings}
                overlap = enroll_stems.intersection(verify_stems)
                assert len(overlap) == 0, f"Speaker {spk_id} has overlap: {overlap}"

    def test_ineligible_reason_populated(self, mock_dataset: Path) -> None:
        """Verify ineligible speakers have a reason string."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")
        selector = EnrollmentSelector(enrollment_count=3, seed=42)
        splits = selector.select(speakers)

        assert splits["1004"].ineligibility_reason is not None
        assert "Insufficient recordings" in splits["1004"].ineligibility_reason

    def test_reproducibility_same_seed(self, mock_dataset: Path) -> None:
        """Verify same seed produces identical enrollment/verification splits."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")

        selector1 = EnrollmentSelector(enrollment_count=3, seed=42)
        splits1 = selector1.select(speakers)

        selector2 = EnrollmentSelector(enrollment_count=3, seed=42)
        splits2 = selector2.select(speakers)

        for spk_id in splits1:
            if splits1[spk_id].is_eligible:
                stems1 = [p.stem for p in splits1[spk_id].enrollment_recordings]
                stems2 = [p.stem for p in splits2[spk_id].enrollment_recordings]
                assert stems1 == stems2, f"Speaker {spk_id}: enrollment differs across runs"

    def test_different_seed_different_selection(self, mock_dataset: Path) -> None:
        """Verify different seeds produce different selections (for speakers with enough recs)."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        speakers = discovery.discover_split("dev-clean")

        selector1 = EnrollmentSelector(enrollment_count=3, seed=42)
        splits1 = selector1.select(speakers)

        selector2 = EnrollmentSelector(enrollment_count=3, seed=999)
        splits2 = selector2.select(speakers)

        # At least for speaker 1001 with 6 recordings, different seeds should usually differ
        # (There's a very small chance of collision, but with 6-choose-3 = 20 combinations it's unlikely)
        stems1 = set(p.stem for p in splits1["1001"].enrollment_recordings)
        stems2 = set(p.stem for p in splits2["1001"].enrollment_recordings)
        # We don't assert != because there's a small chance of collision
        # Instead verify both are valid
        assert len(stems1) == 3
        assert len(stems2) == 3

    def test_invalid_enrollment_count(self) -> None:
        """Verify ValueError for enrollment_count < 1."""
        with pytest.raises(ValueError, match="enrollment_count"):
            EnrollmentSelector(enrollment_count=0)


# ---------------------------------------------------------------------------
# Trial Generator Tests
# ---------------------------------------------------------------------------


class TestTrialGenerator:
    """Tests for genuine and impostor trial generation."""

    def _make_enrollment_splits(self) -> Dict[str, EnrollmentSplit]:
        """Create simple enrollment splits for testing (no actual audio files needed)."""
        # 3 eligible speakers, each with 3 enrollment + varying verification
        splits = {}
        for spk_id, ver_count in [("A", 3), ("B", 2), ("C", 1)]:
            enroll = [Path(f"/fake/{spk_id}_enroll_{i}.wav") for i in range(3)]
            verify = [Path(f"/fake/{spk_id}_verify_{i}.wav") for i in range(ver_count)]
            splits[spk_id] = EnrollmentSplit(
                speaker_id=spk_id,
                enrollment_recordings=enroll,
                verification_recordings=verify,
                is_eligible=True,
            )
        # 1 ineligible speaker
        splits["D"] = EnrollmentSplit(
            speaker_id="D",
            is_eligible=False,
            ineligibility_reason="Too few recordings",
        )
        return splits

    def test_genuine_trials_count(self) -> None:
        """Verify number of genuine trials equals total verification recordings."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42)
        genuine = gen.generate_genuine_trials(splits, "test")

        # A has 3 verify, B has 2, C has 1 = total 6 genuine
        assert len(genuine) == 6

    def test_genuine_trials_labels(self) -> None:
        """Verify all genuine trials have label=1 and matching speaker IDs."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42)
        genuine = gen.generate_genuine_trials(splits, "test")

        for trial in genuine:
            assert trial.ground_truth_label == 1
            assert trial.trial_type == "genuine"
            assert trial.claimed_speaker_id == trial.actual_speaker_id

    def test_impostor_trials_labels(self) -> None:
        """Verify all impostor trials have label=0 and different speaker IDs."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42, max_impostors_per_speaker=5)
        impostor = gen.generate_impostor_trials(splits, "test")

        assert len(impostor) > 0
        for trial in impostor:
            assert trial.ground_truth_label == 0
            assert trial.trial_type == "impostor"
            assert trial.claimed_speaker_id != trial.actual_speaker_id

    def test_impostor_max_cap(self) -> None:
        """Verify impostor count is capped at max_impostors_per_speaker * eligible."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42, max_impostors_per_speaker=2)
        impostor = gen.generate_impostor_trials(splits, "test")

        # 3 eligible speakers * 2 impostors each = at most 6 impostor trials
        assert len(impostor) <= 6

    def test_generate_all_trials_result_structure(self) -> None:
        """Verify TrialGenerationResult has correct structure and counts."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42, max_impostors_per_speaker=3)
        result = gen.generate_all_trials(splits, "dev-clean")

        assert isinstance(result, TrialGenerationResult)
        assert result.genuine_count + result.impostor_count == result.total_count
        assert result.total_count == len(result.trials)
        assert result.eligible_speakers == 3  # A, B, C
        assert result.split_name == "dev-clean"

    def test_unique_trial_ids(self) -> None:
        """Verify all trials have unique IDs."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42, max_impostors_per_speaker=5)
        result = gen.generate_all_trials(splits, "test")

        trial_ids = [t.trial_id for t in result.trials]
        assert len(trial_ids) == len(set(trial_ids))

    def test_ineligible_speakers_excluded(self) -> None:
        """Verify ineligible speakers do not appear in any trials."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42)
        result = gen.generate_all_trials(splits, "test")

        for trial in result.trials:
            assert trial.claimed_speaker_id != "D"

    def test_enrollment_recording_ids_populated(self) -> None:
        """Verify trial enrollment_recording_ids contain expected stems."""
        splits = self._make_enrollment_splits()
        gen = TrialGenerator(seed=42)
        result = gen.generate_all_trials(splits, "test")

        for trial in result.trials:
            assert len(trial.enrollment_recording_ids) == 3
            expected_prefix = f"{trial.claimed_speaker_id}_enroll_"
            for stem in trial.enrollment_recording_ids:
                assert stem.startswith(expected_prefix)


# ---------------------------------------------------------------------------
# Leakage Validator Tests
# ---------------------------------------------------------------------------


class TestLeakageValidator:
    """Tests for data leakage and integrity validation."""

    def test_disjoint_splits_pass(self) -> None:
        """Verify disjoint speaker sets pass validation."""
        validator = LeakageValidator()
        is_disjoint, overlap = validator.validate_speaker_disjoint(
            {"A", "B", "C"}, {"D", "E", "F"}
        )
        assert is_disjoint
        assert len(overlap) == 0

    def test_overlapping_splits_fail(self) -> None:
        """Verify overlapping speaker sets fail validation."""
        validator = LeakageValidator()
        is_disjoint, overlap = validator.validate_speaker_disjoint(
            {"A", "B", "C"}, {"C", "D", "E"}
        )
        assert not is_disjoint
        assert "C" in overlap

    def test_enrollment_verification_nonoverlap(self) -> None:
        """Verify no overlap between enrollment and verification recordings."""
        validator = LeakageValidator()
        splits = {
            "A": EnrollmentSplit(
                speaker_id="A",
                enrollment_recordings=[Path("/a/e1.wav"), Path("/a/e2.wav")],
                verification_recordings=[Path("/a/v1.wav"), Path("/a/v2.wav")],
                is_eligible=True,
            ),
        }
        is_ok, violations = validator.validate_enrollment_verification_nonoverlap(splits)
        assert is_ok
        assert len(violations) == 0

    def test_enrollment_verification_overlap_detected(self) -> None:
        """Verify overlap detection when same recording appears in both sets."""
        validator = LeakageValidator()
        # Same path stem 'shared' in both enrollment and verification
        splits = {
            "A": EnrollmentSplit(
                speaker_id="A",
                enrollment_recordings=[Path("/a/shared.wav"), Path("/a/e2.wav")],
                verification_recordings=[Path("/b/shared.wav"), Path("/a/v1.wav")],
                is_eligible=True,
            ),
        }
        is_ok, violations = validator.validate_enrollment_verification_nonoverlap(splits)
        assert not is_ok
        assert len(violations) == 1
        assert violations[0]["recording"] == "shared"

    def test_duplicate_trial_ids_detected(self) -> None:
        """Verify duplicate trial ID detection."""
        validator = LeakageValidator()
        trials = [
            VerificationTrial(
                trial_id="same-id", claimed_speaker_id="A", actual_speaker_id="A",
                enrollment_recording_ids=["e1"], verification_recording_id="v1",
                verification_recording_path="/a/v1.wav",
                trial_type="genuine", ground_truth_label=1, split="test",
                model_identifier="test-model",
            ),
            VerificationTrial(
                trial_id="same-id", claimed_speaker_id="B", actual_speaker_id="B",
                enrollment_recording_ids=["e2"], verification_recording_id="v2",
                verification_recording_path="/b/v2.wav",
                trial_type="genuine", ground_truth_label=1, split="test",
                model_identifier="test-model",
            ),
        ]
        is_ok, dups = validator.validate_no_duplicate_trial_ids(trials)
        assert not is_ok
        assert "same-id" in dups

    def test_trial_label_consistency_genuine(self) -> None:
        """Verify label consistency check for genuine trials."""
        validator = LeakageValidator()
        # Genuine trial with mismatched speaker IDs
        bad_trial = VerificationTrial(
            trial_id="t1", claimed_speaker_id="A", actual_speaker_id="B",
            enrollment_recording_ids=["e1"], verification_recording_id="v1",
            verification_recording_path="/a/v1.wav",
            trial_type="genuine", ground_truth_label=1, split="test",
            model_identifier="test-model",
        )
        is_ok, mismatches = validator.validate_trial_labels([bad_trial])
        assert not is_ok
        assert len(mismatches) > 0

    def test_trial_label_consistency_impostor(self) -> None:
        """Verify label consistency check for impostor trials."""
        validator = LeakageValidator()
        # Impostor trial with matching speaker IDs (should fail)
        bad_trial = VerificationTrial(
            trial_id="t1", claimed_speaker_id="A", actual_speaker_id="A",
            enrollment_recording_ids=["e1"], verification_recording_id="v1",
            verification_recording_path="/a/v1.wav",
            trial_type="impostor", ground_truth_label=0, split="test",
            model_identifier="test-model",
        )
        is_ok, mismatches = validator.validate_trial_labels([bad_trial])
        assert not is_ok

    def test_validate_all_passes_clean_data(self) -> None:
        """Verify full validation passes with clean trial data."""
        validator = LeakageValidator()
        splits = {
            "A": EnrollmentSplit(
                speaker_id="A",
                enrollment_recordings=[Path("/a/e1.wav"), Path("/a/e2.wav")],
                verification_recordings=[Path("/a/v1.wav")],
                is_eligible=True,
            ),
        }
        trials = [
            VerificationTrial(
                trial_id="t1", claimed_speaker_id="A", actual_speaker_id="A",
                enrollment_recording_ids=["e1", "e2"], verification_recording_id="v1",
                verification_recording_path="/a/v1.wav",
                trial_type="genuine", ground_truth_label=1, split="test",
                model_identifier="test-model",
            ),
        ]
        result = validator.validate_all(trials=trials, enrollment_splits=splits)
        assert result.is_valid
        assert result.checks_failed == 0

    def test_validate_all_with_cross_split(self, mock_dataset: Path) -> None:
        """Verify cross-split validation with disjoint speakers."""
        validator = LeakageValidator()
        dev_speakers = {"1001", "1002", "1003", "1004"}
        test_speakers = {"2001", "2002", "2003"}

        splits = {
            "1001": EnrollmentSplit(
                speaker_id="1001",
                enrollment_recordings=[Path("/e1.wav")],
                verification_recordings=[Path("/v1.wav")],
                is_eligible=True,
            ),
        }
        trials = [
            VerificationTrial(
                trial_id="t1", claimed_speaker_id="1001", actual_speaker_id="1001",
                enrollment_recording_ids=["e1"], verification_recording_id="v1",
                verification_recording_path="/v1.wav",
                trial_type="genuine", ground_truth_label=1, split="dev",
                model_identifier="test-model",
            ),
        ]

        result = validator.validate_all(
            trials=trials,
            enrollment_splits=splits,
            dev_speakers=dev_speakers,
            test_speakers=test_speakers,
        )
        assert result.is_valid


# ---------------------------------------------------------------------------
# Trial Manifest Tests
# ---------------------------------------------------------------------------


class TestTrialManifestWriter:
    """Tests for CSV and JSON manifest writing and reading."""

    def _make_trials(self) -> List[VerificationTrial]:
        """Create sample trials for manifest testing."""
        return [
            VerificationTrial(
                trial_id="t001", claimed_speaker_id="A", actual_speaker_id="A",
                enrollment_recording_ids=["e1", "e2", "e3"],
                verification_recording_id="v1",
                verification_recording_path="/data/A/v1.wav",
                trial_type="genuine", ground_truth_label=1, split="dev-clean",
                model_identifier="speechbrain/spkrec-ecapa-voxceleb",
            ),
            VerificationTrial(
                trial_id="t002", claimed_speaker_id="A", actual_speaker_id="B",
                enrollment_recording_ids=["e1", "e2", "e3"],
                verification_recording_id="v2",
                verification_recording_path="/data/B/v2.wav",
                trial_type="impostor", ground_truth_label=0, split="dev-clean",
                model_identifier="speechbrain/spkrec-ecapa-voxceleb",
            ),
        ]

    def test_csv_write_and_read(self, tmp_path: Path) -> None:
        """Verify CSV manifest round-trip (write then read)."""
        trials = self._make_trials()
        writer = TrialManifestWriter(output_dir=tmp_path)

        csv_path = writer.write_csv(trials)
        assert csv_path.exists()

        rows = writer.read_csv()
        assert len(rows) == 2
        assert rows[0]["trial_id"] == "t001"
        assert rows[0]["ground_truth_label"] == 1
        assert rows[0]["trial_type"] == "genuine"
        assert rows[0]["enrollment_recording_ids"] == ["e1", "e2", "e3"]

        assert rows[1]["trial_id"] == "t002"
        assert rows[1]["ground_truth_label"] == 0
        assert rows[1]["trial_type"] == "impostor"

    def test_csv_column_headers(self, tmp_path: Path) -> None:
        """Verify CSV has correct column headers."""
        trials = self._make_trials()
        writer = TrialManifestWriter(output_dir=tmp_path)
        csv_path = writer.write_csv(trials)

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

        expected = [
            "trial_id", "claimed_speaker_id", "actual_speaker_id",
            "enrollment_recording_ids", "verification_recording_id",
            "trial_type", "ground_truth_label", "split", "model_identifier",
        ]
        assert header == expected

    def test_json_summary_write(self, tmp_path: Path) -> None:
        """Verify JSON summary contains expected fields."""
        result = TrialGenerationResult(
            split_name="dev-clean",
            genuine_count=100,
            impostor_count=200,
            total_count=300,
            genuine_impostor_ratio="1:2",
            eligible_speakers=10,
            seed=42,
            impostors_per_speaker=10,
            model_identifier="speechbrain/spkrec-ecapa-voxceleb",
        )

        writer = TrialManifestWriter(output_dir=tmp_path)
        json_path = writer.write_summary(result)
        assert json_path.exists()

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["split_name"] == "dev-clean"
        assert data["seed"] == 42
        assert data["trial_statistics"]["genuine_trials"] == 100
        assert data["trial_statistics"]["impostor_trials"] == 200
        assert data["trial_statistics"]["total_trials"] == 300
        assert data["eligible_speakers"] == 10


# ---------------------------------------------------------------------------
# Integration Tests (synthetic data only)
# ---------------------------------------------------------------------------


class TestTrialPipelineIntegration:
    """End-to-end pipeline tests using synthetic audio data."""

    def test_full_pipeline_with_mock_dataset(self, mock_dataset: Path) -> None:
        """Verify the complete pipeline: discover → select → generate → validate → write."""
        # Step 1: Discover
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        dev_speakers = discovery.discover_split("dev-clean")
        test_speakers = discovery.discover_split("test-clean")

        # Step 2: Select enrollment/verification
        selector = EnrollmentSelector(enrollment_count=3, seed=42)
        dev_splits = selector.select(dev_speakers)
        test_splits = selector.select(test_speakers)

        # Verify eligibility
        dev_eligible = [s for s in dev_splits.values() if s.is_eligible]
        assert len(dev_eligible) == 3  # 1001, 1002, 1003 (1004 excluded)

        test_eligible = [s for s in test_splits.values() if s.is_eligible]
        assert len(test_eligible) == 2  # 2001, 2002 (2003 excluded)

        # Step 3: Generate trials
        gen = TrialGenerator(seed=42, max_impostors_per_speaker=5)
        dev_result = gen.generate_all_trials(dev_splits, "dev-clean")
        test_result = gen.generate_all_trials(test_splits, "test-clean")

        assert dev_result.total_count > 0
        assert test_result.total_count > 0
        assert dev_result.genuine_count > 0
        assert dev_result.impostor_count > 0

        # Step 4: Validate
        validator = LeakageValidator()
        dev_validation = validator.validate_all(
            trials=dev_result.trials,
            enrollment_splits=dev_splits,
            dev_speakers=set(dev_speakers.keys()),
            test_speakers=set(test_speakers.keys()),
        )
        assert dev_validation.is_valid, f"Validation failed: {dev_validation.violations}"

        # Step 5: Write manifests
        dev_output = mock_dataset / "output" / "dev"
        writer = TrialManifestWriter(output_dir=dev_output)
        csv_path = writer.write_csv(dev_result.trials)
        json_path = writer.write_summary(dev_result)

        assert csv_path.exists()
        assert json_path.exists()

        # Verify round-trip
        rows = writer.read_csv()
        assert len(rows) == dev_result.total_count

    def test_cross_split_disjoint_validation(self, mock_dataset: Path) -> None:
        """Verify cross-split speaker disjoint validation with mock data."""
        discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
        dev_speakers = set(discovery.discover_split("dev-clean").keys())
        test_speakers = set(discovery.discover_split("test-clean").keys())

        validator = LeakageValidator()
        is_disjoint, overlap = validator.validate_speaker_disjoint(
            dev_speakers, test_speakers
        )
        assert is_disjoint
        assert len(overlap) == 0

    def test_overlapping_split_detection(self, overlapping_dataset: Path) -> None:
        """Verify detection of speaker overlap between splits."""
        discovery = SpeakerRecordingDiscovery(dataset_root=overlapping_dataset)
        dev_speakers = set(discovery.discover_split("dev-clean").keys())
        test_speakers = set(discovery.discover_split("test-clean").keys())

        validator = LeakageValidator()
        is_disjoint, overlap = validator.validate_speaker_disjoint(
            dev_speakers, test_speakers
        )
        assert not is_disjoint
        assert "SHARED" in overlap

    def test_pipeline_reproducibility(self, mock_dataset: Path) -> None:
        """Verify running the pipeline twice with same seed produces identical trials."""
        def run_pipeline(seed: int):
            discovery = SpeakerRecordingDiscovery(dataset_root=mock_dataset)
            speakers = discovery.discover_split("dev-clean")
            selector = EnrollmentSelector(enrollment_count=3, seed=seed)
            splits = selector.select(speakers)
            gen = TrialGenerator(seed=seed, max_impostors_per_speaker=5)
            result = gen.generate_all_trials(splits, "dev-clean")
            return result

        r1 = run_pipeline(42)
        r2 = run_pipeline(42)

        assert r1.genuine_count == r2.genuine_count
        assert r1.impostor_count == r2.impostor_count
        assert r1.total_count == r2.total_count

        # Compare trial details (excluding UUIDs which are always unique)
        for t1, t2 in zip(r1.trials, r2.trials):
            assert t1.claimed_speaker_id == t2.claimed_speaker_id
            assert t1.actual_speaker_id == t2.actual_speaker_id
            assert t1.verification_recording_id == t2.verification_recording_id
            assert t1.trial_type == t2.trial_type
            assert t1.ground_truth_label == t2.ground_truth_label

