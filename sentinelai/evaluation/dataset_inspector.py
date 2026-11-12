"""Dataset Inspector for Audio Corpora and Speaker Recognition Datasets.

Recursively scans audio directories, extracts speaker and chapter hierarchies,
validates acoustic signals using SoundFile, computes acoustic statistics,
and identifies speaker overlap across splits without loading audio arrays into memory.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
import math
from pathlib import Path
import re
import statistics
from typing import Any, Dict, List, Optional, Set, Tuple
import soundfile as sf

from sentinelai.evaluation.dataset_report import (
    AudioFileInfo,
    DatasetInspectionReport,
    SpeakerSummary,
    SplitInspectionReport,
    format_duration,
)

logger = logging.getLogger(__name__)


class DatasetInspector:
    """Inspector for multi-speaker speech datasets (LibriSpeech and similar audio corpora).

    Features:
        - Recursive directory traversal.
        - Hierarchical speaker and chapter identification.
        - High-throughput metadata extraction via SoundFile header decoding.
        - Zero audio array memory retention (avoids RAM exhaustion).
        - Multi-split speaker overlap / data leakage detection.
        - Corruption, truncation, and 0-byte file detection.
        - Optional SPEAKERS.TXT metadata parsing for demographic annotation.
    """

    DEFAULT_EXTENSIONS = [".flac", ".wav"]
    DEFAULT_SPLITS = ["dev-clean", "test-clean"]

    def __init__(
        self,
        dataset_root: Path,
        split_names: Optional[List[str]] = None,
        audio_extensions: Optional[List[str]] = None,
        max_workers: int = 8,
    ) -> None:
        """Initialize the DatasetInspector.

        Args:
            dataset_root: Base path to the dataset directory.
            split_names: List of split subdirectory names to inspect (e.g. ['dev-clean', 'test-clean']).
            audio_extensions: List of allowed file extensions (default: ['.flac', '.wav']).
            max_workers: Number of worker threads for parallel header inspection.
        """
        self.dataset_root = Path(dataset_root)
        self.split_names = split_names or list(self.DEFAULT_SPLITS)
        self.audio_extensions = [
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in (audio_extensions or self.DEFAULT_EXTENSIONS)
        ]
        self.max_workers = max(1, max_workers)
        self._speaker_meta_cache: Dict[str, Dict[str, str]] = {}
        self._load_speakers_metadata()

    def _load_speakers_metadata(self) -> None:
        """Attempt to locate and parse LibriSpeech SPEAKERS.TXT metadata if present."""
        candidate_paths = [
            self.dataset_root / "SPEAKERS.TXT",
            self.dataset_root / "dev-clean" / "LibriSpeech" / "SPEAKERS.TXT",
            self.dataset_root / "test-clean" / "LibriSpeech" / "SPEAKERS.TXT",
        ]
        for p in candidate_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith(";"):
                                continue
                            parts = [col.strip() for col in line.split("|")]
                            if len(parts) >= 5:
                                spk_id, sex, subset, minutes, name = parts[:5]
                                self._speaker_meta_cache[spk_id] = {
                                    "gender": sex,
                                    "subset": subset,
                                    "name": name,
                                }
                    logger.info(f"Loaded speaker metadata for {len(self._speaker_meta_cache)} speakers from {p}")
                    break
                except Exception as exc:
                    logger.warning(f"Could not parse SPEAKERS.TXT at {p}: {exc}")

    def resolve_split_path(self, split_name: str) -> Optional[Path]:
        """Resolve the active directory containing speaker subfolders for a split.

        Handles nested LibriSpeech extraction layouts:
            e.g. datasets/librispeech/dev-clean/LibriSpeech/dev-clean
            as well as flat layouts: datasets/librispeech/dev-clean.

        Args:
            split_name: Name of the split (e.g. 'dev-clean').

        Returns:
            Resolved Path object, or None if the directory does not exist.
        """
        direct_path = self.dataset_root / split_name
        if not direct_path.exists():
            return None

        # Check for nested LibriSpeech structure
        nested_path = direct_path / "LibriSpeech" / split_name
        if nested_path.exists() and nested_path.is_dir():
            return nested_path

        # Check alternative capitalization
        nested_lower = direct_path / "librispeech" / split_name
        if nested_lower.exists() and nested_lower.is_dir():
            return nested_lower

        return direct_path

    @staticmethod
    def extract_identifiers(file_path: Path, split_root: Path) -> Tuple[str, str, str]:
        """Extract speaker_id, chapter_id, and utterance_id from file path.

        In LibriSpeech standard hierarchy:
            <split_root>/<speaker_id>/<chapter_id>/<speaker_id>-<chapter_id>-<utterance_id>.<ext>

        Args:
            file_path: Path to the audio file.
            split_root: Root directory of the split.

        Returns:
            Tuple of (speaker_id, chapter_id, utterance_id).
        """
        # Try filename pattern match: <spk>-<chap>-<utt>.<ext>
        stem = file_path.stem
        match = re.match(r"^(\d+)-(\d+)-(\d+)$", stem)
        if match:
            return match.group(1), match.group(2), match.group(3)

        # Fallback to directory parts relative to split root
        try:
            rel = file_path.relative_to(split_root)
            parts = rel.parts
            if len(parts) >= 3:
                return parts[0], parts[1], stem
            elif len(parts) == 2:
                return parts[0], "unknown", stem
        except ValueError:
            pass

        # Final fallback
        parent_name = file_path.parent.name
        grandparent_name = file_path.parent.parent.name
        return grandparent_name, parent_name, stem

    def inspect_audio_file(self, file_path: Path, split_root: Path) -> AudioFileInfo:
        """Inspect a single audio file's metadata and validate its integrity.

        Uses SoundFile info header reading without reading audio sample arrays into RAM.

        Args:
            file_path: Path to the audio file.
            split_root: Base root of the split for relative path calculation.

        Returns:
            AudioFileInfo with acoustic metadata or failure annotations.
        """
        rel_path = str(file_path.relative_to(self.dataset_root) if file_path.is_relative_to(self.dataset_root) else file_path)
        spk_id, chap_id, utt_id = self.extract_identifiers(file_path, split_root)

        try:
            stat_info = file_path.stat()
            size_bytes = stat_info.st_size
        except OSError as exc:
            return AudioFileInfo(
                file_path=str(file_path),
                relative_path=rel_path,
                speaker_id=spk_id,
                chapter_id=chap_id,
                utterance_id=utt_id,
                sample_rate=0,
                channels=0,
                duration_sec=0.0,
                audio_format="UNKNOWN",
                subtype="UNKNOWN",
                size_bytes=0,
                is_valid=False,
                error_message=f"Filesystem access error: {exc}",
            )

        if size_bytes == 0:
            return AudioFileInfo(
                file_path=str(file_path),
                relative_path=rel_path,
                speaker_id=spk_id,
                chapter_id=chap_id,
                utterance_id=utt_id,
                sample_rate=0,
                channels=0,
                duration_sec=0.0,
                audio_format="EMPTY",
                subtype="EMPTY",
                size_bytes=0,
                is_valid=False,
                error_message="Audio file is empty (0 bytes).",
            )

        try:
            info = sf.info(str(file_path))
            duration = float(info.duration)

            if duration <= 0.0 or not math.isfinite(duration):
                return AudioFileInfo(
                    file_path=str(file_path),
                    relative_path=rel_path,
                    speaker_id=spk_id,
                    chapter_id=chap_id,
                    utterance_id=utt_id,
                    sample_rate=info.samplerate,
                    channels=info.channels,
                    duration_sec=duration,
                    audio_format=info.format,
                    subtype=info.subtype,
                    size_bytes=size_bytes,
                    is_valid=False,
                    error_message=f"Non-positive or non-finite audio duration: {duration}s",
                )

            return AudioFileInfo(
                file_path=str(file_path),
                relative_path=rel_path,
                speaker_id=spk_id,
                chapter_id=chap_id,
                utterance_id=utt_id,
                sample_rate=info.samplerate,
                channels=info.channels,
                duration_sec=duration,
                audio_format=info.format,
                subtype=info.subtype,
                size_bytes=size_bytes,
                is_valid=True,
                error_message=None,
            )

        except Exception as exc:
            return AudioFileInfo(
                file_path=str(file_path),
                relative_path=rel_path,
                speaker_id=spk_id,
                chapter_id=chap_id,
                utterance_id=utt_id,
                sample_rate=0,
                channels=0,
                duration_sec=0.0,
                audio_format="CORRUPTED",
                subtype="CORRUPTED",
                size_bytes=size_bytes,
                is_valid=False,
                error_message=f"SoundFile decoding error: {exc}",
            )

    def inspect_split(self, split_name: str) -> SplitInspectionReport:
        """Inspect all audio files in a single dataset split.

        Args:
            split_name: Name of the split (e.g. 'dev-clean').

        Returns:
            SplitInspectionReport summarizing the split.
        """
        split_path = self.resolve_split_path(split_name)
        if split_path is None or not split_path.exists():
            logger.warning(f"Split directory '{split_name}' not found under {self.dataset_root}")
            return SplitInspectionReport(
                split_name=split_name,
                root_path=str(self.dataset_root / split_name),
            )

        # Collect audio files matching specified extensions
        audio_files: List[Path] = []
        seen_paths: Set[Path] = set()
        for ext in self.audio_extensions:
            for p in split_path.rglob(f"*{ext}"):
                if p not in seen_paths:
                    seen_paths.add(p)
                    audio_files.append(p)

        audio_files = sorted(audio_files)

        if not audio_files:
            return SplitInspectionReport(
                split_name=split_name,
                root_path=str(split_path),
            )

        # Parallel inspection using ThreadPoolExecutor for high I/O throughput
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            inspected: List[AudioFileInfo] = list(
                executor.map(lambda f: self.inspect_audio_file(f, split_path), audio_files)
            )

        # Aggregate statistics
        speaker_chapters: Dict[str, Set[str]] = {}
        speaker_durations: Dict[str, List[float]] = {}
        all_durations: List[float] = []
        sample_rates: Dict[int, int] = {}
        channels: Dict[int, int] = {}
        subtypes: Dict[str, int] = {}
        formats: Dict[str, int] = {}
        total_size = 0
        corrupted: List[Dict[str, str]] = []
        empty: List[Dict[str, str]] = []

        for item in inspected:
            total_size += item.size_bytes

            if not item.is_valid:
                if item.size_bytes == 0:
                    empty.append({"path": item.relative_path, "error": item.error_message or "0 bytes"})
                else:
                    corrupted.append({"path": item.relative_path, "error": item.error_message or "Corrupted"})
                continue

            all_durations.append(item.duration_sec)

            # Speaker tracking
            spk = item.speaker_id
            if spk not in speaker_chapters:
                speaker_chapters[spk] = set()
                speaker_durations[spk] = []
            speaker_chapters[spk].add(item.chapter_id)
            speaker_durations[spk].append(item.duration_sec)

            # Distributions
            sample_rates[item.sample_rate] = sample_rates.get(item.sample_rate, 0) + 1
            channels[item.channels] = channels.get(item.channels, 0) + 1
            subtypes[item.subtype] = subtypes.get(item.subtype, 0) + 1
            formats[item.audio_format] = formats.get(item.audio_format, 0) + 1

        total_dur = sum(all_durations)
        min_dur = min(all_durations) if all_durations else 0.0
        max_dur = max(all_durations) if all_durations else 0.0
        mean_dur = statistics.mean(all_durations) if all_durations else 0.0
        std_dur = statistics.stdev(all_durations) if len(all_durations) > 1 else 0.0

        all_chapters: Set[str] = set()
        for chaps in speaker_chapters.values():
            all_chapters.update(chaps)

        # Build speaker summaries
        speakers_dict: Dict[str, SpeakerSummary] = {}
        for spk_id, durs in speaker_durations.items():
            meta = self._speaker_meta_cache.get(spk_id, {})
            spk_tot_dur = sum(durs)
            speakers_dict[spk_id] = SpeakerSummary(
                speaker_id=spk_id,
                gender=meta.get("gender"),
                name=meta.get("name"),
                chapter_count=len(speaker_chapters.get(spk_id, set())),
                utterance_count=len(durs),
                total_duration_sec=round(spk_tot_dur, 2),
                avg_duration_sec=round(spk_tot_dur / len(durs), 2) if durs else 0.0,
            )

        return SplitInspectionReport(
            split_name=split_name,
            root_path=str(split_path),
            total_speakers=len(speaker_chapters),
            total_chapters=len(all_chapters),
            total_utterances=len(all_durations),
            total_duration_sec=round(total_dur, 2),
            total_duration_formatted=format_duration(total_dur),
            min_duration_sec=round(min_dur, 2),
            max_duration_sec=round(max_dur, 2),
            mean_duration_sec=round(mean_dur, 2),
            std_duration_sec=round(std_dur, 2),
            sample_rate_distribution=sample_rates,
            channel_distribution=channels,
            subtype_distribution=subtypes,
            format_distribution=formats,
            total_size_bytes=total_size,
            total_size_mb=round(total_size / (1024 * 1024), 2),
            corrupted_files=corrupted,
            empty_files=empty,
            speakers=speakers_dict,
        )

    def inspect_dataset(self) -> DatasetInspectionReport:
        """Inspect all configured splits and compile a comprehensive dataset report.

        Returns:
            DatasetInspectionReport containing multi-split statistics and overlap checks.
        """
        splits_reports: Dict[str, SplitInspectionReport] = {}
        speaker_sets: Dict[str, Set[str]] = {}

        for split_name in self.split_names:
            report = self.inspect_split(split_name)
            splits_reports[split_name] = report
            speaker_sets[split_name] = set(report.speakers.keys())

        # Check speaker overlap between splits (e.g. dev-clean vs test-clean)
        overlapping_speakers: Set[str] = set()
        split_keys = list(speaker_sets.keys())
        for i in range(len(split_keys)):
            for j in range(i + 1, len(split_keys)):
                overlap = speaker_sets[split_keys[i]].intersection(speaker_sets[split_keys[j]])
                overlapping_speakers.update(overlap)

        all_unique_speakers: Set[str] = set()
        for s in speaker_sets.values():
            all_unique_speakers.update(s)

        total_utterances = sum(s.total_utterances for s in splits_reports.values())
        total_duration = sum(s.total_duration_sec for s in splits_reports.values())
        total_chapters = sum(s.total_chapters for s in splits_reports.values())
        total_corrupted = sum(len(s.corrupted_files) for s in splits_reports.values())
        total_empty = sum(len(s.empty_files) for s in splits_reports.values())

        has_overlap = len(overlapping_speakers) > 0

        # Suitability determination
        is_suitable = (total_utterances > 0) and (total_corrupted == 0) and not has_overlap

        limitations = [
            "Read Audiobook Speech Domain: Utterances originate from LibriVox audiobooks (clean read speech), lacking the prosodic variance, conversational turn-taking, and emotional shifts of real-world dialogue.",
            "High Acoustic Cleanliness: The recordings have near-studio Signal-to-Noise Ratio (SNR) with minimal background noise or reverberation, not testing acoustic robustness or cross-channel variability.",
            "ASR Origin: LibriSpeech was compiled primarily for speech-to-text benchmark evaluations; speaker verification trials (genuine and impostor pairs) must be synthetically coupled rather than collected as natural multi-session claimant trials.",
            "Phonetic & Lexical Disparity: Because each speaker reads different book chapters, differences in lexical content may introduce phonetic variance that influences ECAPA-TDNN feature trajectories.",
            "Absence of Synthetic / Replay Spoofs: The dataset contains exclusively bona fide recordings and provides zero presentation attack detection (PAD) samples for anti-spoofing evaluations.",
        ]

        suitability_summary = (
            "The dataset is fully suitable as a controlled, clean development testbed for Phase 5B (Enrollment & Genuine/Impostor Trial Generation) and Phase 5C (Equal Error Rate Calibration). "
            "The zero speaker overlap guarantees that the dev-clean and test-clean splits are strictly disjoint, preventing biometric evaluation leakage."
            if is_suitable
            else "The dataset has anomalies (corrupted files or speaker overlap) that require mitigation before proceeding with evaluation."
        )

        return DatasetInspectionReport(
            dataset_name="LibriSpeech (dev-clean & test-clean)",
            dataset_root=str(self.dataset_root),
            splits=splits_reports,
            total_speakers=len(all_unique_speakers),
            total_chapters=total_chapters,
            total_utterances=total_utterances,
            total_duration_sec=round(total_duration, 2),
            total_duration_formatted=format_duration(total_duration),
            speaker_overlap=sorted(list(overlapping_speakers)),
            has_speaker_overlap=has_overlap,
            total_corrupted_files=total_corrupted,
            total_empty_files=total_empty,
            is_suitable_for_evaluation=is_suitable,
            suitability_summary=suitability_summary,
            limitations=limitations,
        )
