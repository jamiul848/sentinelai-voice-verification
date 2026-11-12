"""Verification Trial Generation for Speaker Recognition Evaluation.

Generates genuine (same-speaker) and impostor (cross-speaker) verification trials
from enrollment/verification recording splits, with deterministic sampling
and unique trial identification.
"""

import logging
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sentinelai.evaluation.speaker_discovery import EnrollmentSplit

logger = logging.getLogger(__name__)


@dataclass
class VerificationTrial:
    """A single verification trial for speaker recognition evaluation.

    Attributes:
        trial_id: Unique identifier for this trial.
        claimed_speaker_id: Speaker ID that the trial claims to be.
        actual_speaker_id: True speaker ID of the verification recording.
        enrollment_recording_ids: List of recording stems used for enrollment.
        verification_recording_id: Recording stem used as the verification probe.
        verification_recording_path: Full path to the verification audio file.
        trial_type: 'genuine' (same-speaker) or 'impostor' (cross-speaker).
        ground_truth_label: 1 for genuine (match), 0 for impostor (non-match).
        split: Dataset split name (e.g. 'dev-clean').
        model_identifier: Model used for embedding extraction.
    """

    trial_id: str
    claimed_speaker_id: str
    actual_speaker_id: str
    enrollment_recording_ids: List[str]
    verification_recording_id: str
    verification_recording_path: str
    trial_type: str
    ground_truth_label: int
    split: str
    model_identifier: str


@dataclass
class TrialGenerationResult:
    """Result of trial generation for a dataset split.

    Attributes:
        split_name: Name of the split (e.g. 'dev-clean').
        trials: List of all generated VerificationTrial instances.
        genuine_count: Number of genuine (same-speaker) trials.
        impostor_count: Number of impostor (cross-speaker) trials.
        total_count: Total number of trials.
        genuine_impostor_ratio: Ratio of genuine to impostor trials.
        eligible_speakers: Number of speakers used for trial generation.
        seed: Random seed used for impostor selection.
        impostors_per_speaker: Number of impostor trials sampled per speaker.
        model_identifier: Model used for embedding extraction.
    """

    split_name: str
    trials: List[VerificationTrial] = field(default_factory=list)
    genuine_count: int = 0
    impostor_count: int = 0
    total_count: int = 0
    genuine_impostor_ratio: str = "0:0"
    eligible_speakers: int = 0
    seed: int = 42
    impostors_per_speaker: int = 0
    model_identifier: str = ""


class TrialGenerator:
    """Generates genuine and impostor verification trials for speaker evaluation.

    Genuine trials: Verification recording belongs to the SAME speaker as the
    enrolled reference profile (ground_truth_label = 1).

    Impostor trials: Verification recording belongs to a DIFFERENT speaker than
    the enrolled reference profile (ground_truth_label = 0).

    The number of impostor trials per speaker is controlled to manage the
    genuine/impostor balance. By default, for each eligible speaker, up to
    `max_impostors_per_speaker` impostor recordings are randomly sampled from
    OTHER speakers' verification recordings.
    """

    def __init__(
        self,
        seed: int = 42,
        max_impostors_per_speaker: int = 10,
        model_identifier: str = "speechbrain/spkrec-ecapa-voxceleb",
    ) -> None:
        """Initialize the trial generator.

        Args:
            seed: Random seed for deterministic impostor selection.
            max_impostors_per_speaker: Maximum impostor trials to sample per speaker.
            model_identifier: Model identifier for trial metadata.
        """
        self.seed = seed
        self.max_impostors_per_speaker = max(1, max_impostors_per_speaker)
        self.model_identifier = model_identifier

    def generate_genuine_trials(
        self,
        enrollment_splits: Dict[str, EnrollmentSplit],
        split_name: str,
    ) -> List[VerificationTrial]:
        """Generate genuine (same-speaker) verification trials.

        For each eligible speaker, creates one trial per verification recording
        against the speaker's own enrollment profile.

        Args:
            enrollment_splits: Mapping from speaker_id to EnrollmentSplit.
            split_name: Dataset split name for trial metadata.

        Returns:
            List of genuine VerificationTrial instances.
        """
        genuine_trials: List[VerificationTrial] = []

        for spk_id in sorted(enrollment_splits.keys()):
            split_info = enrollment_splits[spk_id]
            if not split_info.is_eligible:
                continue

            enrollment_stems = [p.stem for p in split_info.enrollment_recordings]

            for ver_rec in split_info.verification_recordings:
                trial = VerificationTrial(
                    trial_id=str(uuid.uuid4()),
                    claimed_speaker_id=spk_id,
                    actual_speaker_id=spk_id,
                    enrollment_recording_ids=enrollment_stems,
                    verification_recording_id=ver_rec.stem,
                    verification_recording_path=str(ver_rec),
                    trial_type="genuine",
                    ground_truth_label=1,
                    split=split_name,
                    model_identifier=self.model_identifier,
                )
                genuine_trials.append(trial)

        logger.info(
            f"[{split_name}] Generated {len(genuine_trials)} genuine trials"
        )
        return genuine_trials

    def generate_impostor_trials(
        self,
        enrollment_splits: Dict[str, EnrollmentSplit],
        split_name: str,
    ) -> List[VerificationTrial]:
        """Generate impostor (cross-speaker) verification trials.

        For each eligible speaker, selects up to `max_impostors_per_speaker`
        verification recordings from OTHER eligible speakers.

        Args:
            enrollment_splits: Mapping from speaker_id to EnrollmentSplit.
            split_name: Dataset split name for trial metadata.

        Returns:
            List of impostor VerificationTrial instances.
        """
        rng = random.Random(self.seed)
        impostor_trials: List[VerificationTrial] = []

        # Collect eligible speakers
        eligible = {
            spk_id: split_info
            for spk_id, split_info in enrollment_splits.items()
            if split_info.is_eligible
        }

        eligible_ids = sorted(eligible.keys())

        for claimed_spk_id in eligible_ids:
            claimed_split = eligible[claimed_spk_id]
            enrollment_stems = [p.stem for p in claimed_split.enrollment_recordings]

            # Pool all verification recordings from OTHER speakers
            impostor_pool: List[Tuple[str, Path]] = []
            for other_spk_id in eligible_ids:
                if other_spk_id == claimed_spk_id:
                    continue
                for ver_rec in eligible[other_spk_id].verification_recordings:
                    impostor_pool.append((other_spk_id, ver_rec))

            if not impostor_pool:
                continue

            # Deterministic sampling
            sample_count = min(self.max_impostors_per_speaker, len(impostor_pool))
            selected = rng.sample(impostor_pool, sample_count)

            for actual_spk_id, ver_rec in selected:
                trial = VerificationTrial(
                    trial_id=str(uuid.uuid4()),
                    claimed_speaker_id=claimed_spk_id,
                    actual_speaker_id=actual_spk_id,
                    enrollment_recording_ids=enrollment_stems,
                    verification_recording_id=ver_rec.stem,
                    verification_recording_path=str(ver_rec),
                    trial_type="impostor",
                    ground_truth_label=0,
                    split=split_name,
                    model_identifier=self.model_identifier,
                )
                impostor_trials.append(trial)

        logger.info(
            f"[{split_name}] Generated {len(impostor_trials)} impostor trials"
        )
        return impostor_trials

    def generate_all_trials(
        self,
        enrollment_splits: Dict[str, EnrollmentSplit],
        split_name: str,
    ) -> TrialGenerationResult:
        """Generate both genuine and impostor trials for a split.

        Args:
            enrollment_splits: Mapping from speaker_id to EnrollmentSplit.
            split_name: Dataset split name.

        Returns:
            TrialGenerationResult with all trials and summary statistics.
        """
        genuine = self.generate_genuine_trials(enrollment_splits, split_name)
        impostor = self.generate_impostor_trials(enrollment_splits, split_name)

        all_trials = genuine + impostor
        genuine_count = len(genuine)
        impostor_count = len(impostor)
        total_count = len(all_trials)
        eligible_count = sum(
            1 for s in enrollment_splits.values() if s.is_eligible
        )

        # Compute ratio string
        if genuine_count > 0 and impostor_count > 0:
            from math import gcd
            g = gcd(genuine_count, impostor_count)
            ratio_str = f"{genuine_count // g}:{impostor_count // g}"
        elif genuine_count > 0:
            ratio_str = f"{genuine_count}:0"
        else:
            ratio_str = "0:0"

        result = TrialGenerationResult(
            split_name=split_name,
            trials=all_trials,
            genuine_count=genuine_count,
            impostor_count=impostor_count,
            total_count=total_count,
            genuine_impostor_ratio=ratio_str,
            eligible_speakers=eligible_count,
            seed=self.seed,
            impostors_per_speaker=self.max_impostors_per_speaker,
            model_identifier=self.model_identifier,
        )

        logger.info(
            f"[{split_name}] Trial generation complete: "
            f"{genuine_count} genuine + {impostor_count} impostor = {total_count} total, "
            f"ratio={ratio_str}"
        )

        return result

