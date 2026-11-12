"""Speaker and Recording Discovery for Evaluation Pipelines.

Scans LibriSpeech-style directory hierarchies to discover speaker identities,
their audio recordings, and split them into enrollment and verification subsets
using deterministic random selection.
"""

import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sentinelai.evaluation.dataset_inspector import DatasetInspector

logger = logging.getLogger(__name__)


@dataclass
class SpeakerRecordings:
    """Container for a single speaker's discovered audio recordings.

    Attributes:
        speaker_id: Unique identifier for the speaker (e.g. '1272').
        recordings: Sorted list of absolute paths to audio files.
        chapter_ids: Set of chapter identifiers the speaker contributed to.
    """

    speaker_id: str
    recordings: List[Path] = field(default_factory=list)
    chapter_ids: Set[str] = field(default_factory=set)

    @property
    def recording_count(self) -> int:
        return len(self.recordings)


@dataclass
class EnrollmentSplit:
    """Deterministic enrollment/verification partition for a single speaker.

    Attributes:
        speaker_id: Speaker identifier.
        enrollment_recordings: Recordings selected for reference profile generation.
        verification_recordings: Remaining recordings used as verification trials.
        is_eligible: Whether the speaker has sufficient recordings.
        ineligibility_reason: Explanation if the speaker is ineligible.
    """

    speaker_id: str
    enrollment_recordings: List[Path] = field(default_factory=list)
    verification_recordings: List[Path] = field(default_factory=list)
    is_eligible: bool = True
    ineligibility_reason: Optional[str] = None

    @property
    def enrollment_count(self) -> int:
        return len(self.enrollment_recordings)

    @property
    def verification_count(self) -> int:
        return len(self.verification_recordings)


@dataclass
class SplitDiscoveryResult:
    """Result of speaker/recording discovery for a single dataset split.

    Attributes:
        split_name: Name of the split (e.g. 'dev-clean').
        split_root: Resolved root path of the split directory.
        speakers: Mapping from speaker_id to SpeakerRecordings.
        enrollment_splits: Mapping from speaker_id to EnrollmentSplit.
        eligible_speakers: List of speaker IDs with sufficient recordings.
        ineligible_speakers: List of speaker IDs that were excluded.
        total_recordings: Total number of audio recordings discovered.
        total_enrollment_recordings: Total recordings assigned for enrollment.
        total_verification_recordings: Total recordings assigned for verification.
        seed: Random seed used for deterministic selection.
    """

    split_name: str
    split_root: str
    speakers: Dict[str, SpeakerRecordings] = field(default_factory=dict)
    enrollment_splits: Dict[str, EnrollmentSplit] = field(default_factory=dict)
    eligible_speakers: List[str] = field(default_factory=list)
    ineligible_speakers: List[str] = field(default_factory=list)
    total_recordings: int = 0
    total_enrollment_recordings: int = 0
    total_verification_recordings: int = 0
    seed: int = 42


class SpeakerRecordingDiscovery:
    """Discovers speakers and their audio recordings from LibriSpeech-style directories.

    Scans the directory hierarchy: <split_root>/<speaker_id>/<chapter_id>/<audio_file>
    and organizes recordings by speaker identity.
    """

    AUDIO_EXTENSIONS = {".flac", ".wav"}

    def __init__(
        self,
        dataset_root: Path,
        audio_extensions: Optional[Set[str]] = None,
    ) -> None:
        """Initialize the discovery engine.

        Args:
            dataset_root: Root path to the dataset (e.g. datasets/librispeech/).
            audio_extensions: Set of allowed file extensions (default: {'.flac', '.wav'}).
        """
        self.dataset_root = Path(dataset_root)
        self.audio_extensions = audio_extensions or self.AUDIO_EXTENSIONS
        self._inspector = DatasetInspector(dataset_root=self.dataset_root)

    def discover_split(self, split_name: str) -> Dict[str, SpeakerRecordings]:
        """Discover all speakers and recordings in a single dataset split.

        Args:
            split_name: Name of the split (e.g. 'dev-clean').

        Returns:
            Dictionary mapping speaker_id -> SpeakerRecordings.

        Raises:
            FileNotFoundError: If the split directory does not exist.
        """
        split_root = self._inspector.resolve_split_path(split_name)
        if split_root is None or not split_root.exists():
            raise FileNotFoundError(
                f"Split directory '{split_name}' not found under {self.dataset_root}"
            )

        speakers: Dict[str, SpeakerRecordings] = {}
        seen_paths: Set[Path] = set()

        for ext in sorted(self.audio_extensions):
            for audio_path in split_root.rglob(f"*{ext}"):
                resolved = audio_path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)

                spk_id, chap_id, _ = DatasetInspector.extract_identifiers(
                    audio_path, split_root
                )

                if spk_id not in speakers:
                    speakers[spk_id] = SpeakerRecordings(speaker_id=spk_id)

                speakers[spk_id].recordings.append(audio_path)
                speakers[spk_id].chapter_ids.add(chap_id)

        # Sort recordings within each speaker for deterministic ordering
        for spk in speakers.values():
            spk.recordings = sorted(spk.recordings, key=lambda p: p.name)

        logger.info(
            f"[{split_name}] Discovered {len(speakers)} speakers, "
            f"{sum(s.recording_count for s in speakers.values())} recordings"
        )
        return speakers


class EnrollmentSelector:
    """Selects enrollment and verification recordings for each speaker.

    Uses deterministic random selection with a fixed seed to ensure reproducibility.
    Speakers with fewer than (min_enrollment + 1) recordings are marked ineligible.
    """

    DEFAULT_ENROLLMENT_COUNT = 3
    DEFAULT_MIN_VERIFICATION = 1

    def __init__(
        self,
        enrollment_count: int = DEFAULT_ENROLLMENT_COUNT,
        min_verification: int = DEFAULT_MIN_VERIFICATION,
        seed: int = 42,
    ) -> None:
        """Initialize the enrollment selector.

        Args:
            enrollment_count: Number of recordings to select for enrollment per speaker.
            min_verification: Minimum verification recordings required for eligibility.
            seed: Random seed for reproducible selection.
        """
        if enrollment_count < 1:
            raise ValueError(f"enrollment_count must be >= 1, got {enrollment_count}")
        if min_verification < 1:
            raise ValueError(f"min_verification must be >= 1, got {min_verification}")

        self.enrollment_count = enrollment_count
        self.min_verification = min_verification
        self.seed = seed

    def select(
        self, speakers: Dict[str, SpeakerRecordings]
    ) -> Dict[str, EnrollmentSplit]:
        """Partition each speaker's recordings into enrollment and verification sets.

        Args:
            speakers: Mapping from speaker_id to SpeakerRecordings.

        Returns:
            Dictionary mapping speaker_id to EnrollmentSplit.
        """
        min_required = self.enrollment_count + self.min_verification
        results: Dict[str, EnrollmentSplit] = {}

        for spk_id in sorted(speakers.keys()):
            spk = speakers[spk_id]

            if spk.recording_count < min_required:
                results[spk_id] = EnrollmentSplit(
                    speaker_id=spk_id,
                    is_eligible=False,
                    ineligibility_reason=(
                        f"Insufficient recordings: {spk.recording_count} found, "
                        f"minimum {min_required} required "
                        f"({self.enrollment_count} enrollment + "
                        f"{self.min_verification} verification)"
                    ),
                )
                logger.debug(
                    f"Speaker {spk_id} ineligible: {spk.recording_count} < {min_required} recordings"
                )
                continue

            # Deterministic selection: seed is combined with speaker_id for per-speaker reproducibility
            rng = random.Random(self.seed + hash(spk_id))
            all_recordings = list(spk.recordings)  # already sorted
            enrollment_indices = sorted(
                rng.sample(range(len(all_recordings)), self.enrollment_count)
            )

            enrollment_set: Set[int] = set(enrollment_indices)
            enrollment_recs = [all_recordings[i] for i in enrollment_indices]
            verification_recs = [
                all_recordings[i]
                for i in range(len(all_recordings))
                if i not in enrollment_set
            ]

            results[spk_id] = EnrollmentSplit(
                speaker_id=spk_id,
                enrollment_recordings=enrollment_recs,
                verification_recordings=verification_recs,
                is_eligible=True,
            )

        eligible = [s for s in results.values() if s.is_eligible]
        ineligible = [s for s in results.values() if not s.is_eligible]
        logger.info(
            f"Enrollment selection complete: {len(eligible)} eligible, "
            f"{len(ineligible)} ineligible speakers"
        )

        return results

