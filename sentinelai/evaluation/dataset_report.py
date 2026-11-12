"""Dataset Inspection Report Data Models and Formatters.

Provides structured models for audio metadata, per-split statistics, dataset-wide
summaries, JSON serialization, and Markdown report generation.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def format_duration(seconds: float) -> str:
    """Format duration in seconds into a human-readable HH:MM:SS string."""
    total_sec = max(0.0, float(seconds))
    hours = int(total_sec // 3600)
    minutes = int((total_sec % 3600) // 60)
    sec = total_sec % 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m {sec:05.2f}s"
    elif minutes > 0:
        return f"{minutes}m {sec:05.2f}s"
    else:
        return f"{sec:.2f}s"


@dataclass
class AudioFileInfo:
    """Detailed metadata for a single inspected audio file."""

    file_path: str
    relative_path: str
    speaker_id: str
    chapter_id: str
    utterance_id: str
    sample_rate: int
    channels: int
    duration_sec: float
    audio_format: str
    subtype: str
    size_bytes: int
    is_valid: bool = True
    error_message: Optional[str] = None


@dataclass
class SpeakerSummary:
    """Aggregated statistics for an individual speaker."""

    speaker_id: str
    gender: Optional[str] = None
    name: Optional[str] = None
    chapter_count: int = 0
    utterance_count: int = 0
    total_duration_sec: float = 0.0
    avg_duration_sec: float = 0.0


@dataclass
class SplitInspectionReport:
    """Comprehensive inspection report for a dataset split (e.g. dev-clean)."""

    split_name: str
    root_path: str
    total_speakers: int = 0
    total_chapters: int = 0
    total_utterances: int = 0
    total_duration_sec: float = 0.0
    total_duration_formatted: str = "0.00s"
    min_duration_sec: float = 0.0
    max_duration_sec: float = 0.0
    mean_duration_sec: float = 0.0
    std_duration_sec: float = 0.0
    sample_rate_distribution: Dict[int, int] = field(default_factory=dict)
    channel_distribution: Dict[int, int] = field(default_factory=dict)
    subtype_distribution: Dict[str, int] = field(default_factory=dict)
    format_distribution: Dict[str, int] = field(default_factory=dict)
    total_size_bytes: int = 0
    total_size_mb: float = 0.0
    corrupted_files: List[Dict[str, str]] = field(default_factory=list)
    empty_files: List[Dict[str, str]] = field(default_factory=list)
    speakers: Dict[str, SpeakerSummary] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to JSON-serializable dictionary."""
        data = asdict(self)
        return data


@dataclass
class DatasetInspectionReport:
    """Overall dataset inspection report combining all splits."""

    dataset_name: str
    dataset_root: str
    inspection_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    splits: Dict[str, SplitInspectionReport] = field(default_factory=dict)
    total_speakers: int = 0
    total_chapters: int = 0
    total_utterances: int = 0
    total_duration_sec: float = 0.0
    total_duration_formatted: str = "0.00s"
    speaker_overlap: List[str] = field(default_factory=list)
    has_speaker_overlap: bool = False
    total_corrupted_files: int = 0
    total_empty_files: int = 0
    is_suitable_for_evaluation: bool = True
    suitability_summary: str = ""
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert full report to JSON-serializable dictionary."""
        return asdict(self)

    def save_json(self, output_path: Path) -> Path:
        """Save report to a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return output_path

    def generate_markdown(self) -> str:
        """Generate a clean, professional GitHub-flavored Markdown report."""
        md = []
        md.append(f"# SentinelAI Dataset Inspection & Validation Report: {self.dataset_name}")
        md.append("")
        md.append(f"**Inspection Timestamp (UTC):** `{self.inspection_timestamp}`  ")
        md.append(f"**Dataset Root Directory:** `{self.dataset_root}`  ")
        md.append(f"**Overall Status:** `{'VALIDATED & SUITABLE' if self.is_suitable_for_evaluation else 'ISSUES DETECTED'}`")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 1. Executive Summary")
        md.append("")
        md.append("| Metric | Overall Total |")
        md.append("| :--- | :--- |")
        md.append(f"| **Total Splits Inspected** | {len(self.splits)} ({', '.join(self.splits.keys())}) |")
        md.append(f"| **Unique Speakers** | **{self.total_speakers}** |")
        md.append(f"| **Total Chapters** | **{self.total_chapters}** |")
        md.append(f"| **Total Audio Utterances** | **{self.total_utterances:,}** |")
        md.append(f"| **Total Audio Duration** | **{self.total_duration_formatted}** ({self.total_duration_sec:.2f} s) |")
        md.append(f"| **Corrupted Audio Files** | **{self.total_corrupted_files}** |")
        md.append(f"| **Empty (0-byte) Files** | **{self.total_empty_files}** |")
        md.append(f"| **Dev/Test Speaker Overlap** | **{len(self.speaker_overlap)}** ({'None (Disjoint)' if not self.has_speaker_overlap else f'LEAKAGE DETECTED: {len(self.speaker_overlap)} speakers'}) |")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 2. Split Comparison & Acoustic Properties")
        md.append("")
        md.append("| Metric | " + " | ".join(f"`{k}`" for k in self.splits.keys()) + " |")
        md.append("| :--- | " + " | ".join(":---:" for _ in self.splits.keys()) + " |")
        md.append("| **Speakers** | " + " | ".join(f"{s.total_speakers}" for s in self.splits.values()) + " |")
        md.append("| **Chapters** | " + " | ".join(f"{s.total_chapters}" for s in self.splits.values()) + " |")
        md.append("| **Utterances** | " + " | ".join(f"{s.total_utterances:,}" for s in self.splits.values()) + " |")
        md.append("| **Total Duration** | " + " | ".join(f"{s.total_duration_formatted}" for s in self.splits.values()) + " |")
        md.append("| **Mean Duration** | " + " | ".join(f"{s.mean_duration_sec:.2f} s (±{s.std_duration_sec:.2f})" for s in self.splits.values()) + " |")
        md.append("| **Min / Max Duration** | " + " | ".join(f"{s.min_duration_sec:.2f}s / {s.max_duration_sec:.2f}s" for s in self.splits.values()) + " |")
        md.append("| **Total Size** | " + " | ".join(f"{s.total_size_mb:.2f} MB" for s in self.splits.values()) + " |")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 3. Acoustic Signal Distributions")
        md.append("")
        for split_name, split in self.splits.items():
            md.append(f"### Split: `{split_name}`")
            md.append("")
            md.append(f"- **Sample Rates:** " + ", ".join(f"{sr} Hz ({cnt} files)" for sr, cnt in split.sample_rate_distribution.items()))
            md.append(f"- **Channels:** " + ", ".join(f"{'Mono' if ch == 1 else 'Stereo' if ch == 2 else f'{ch}-ch'} ({cnt} files)" for ch, cnt in split.channel_distribution.items()))
            md.append(f"- **Subtypes / Bit Depth:** " + ", ".join(f"{sub} ({cnt} files)" for sub, cnt in split.subtype_distribution.items()))
            md.append(f"- **Audio Formats:** " + ", ".join(f"{fmt} ({cnt} files)" for fmt, cnt in split.format_distribution.items()))
            md.append("")

        md.append("---")
        md.append("")
        md.append("## 4. Speaker Overlap & Data Leakage Assessment")
        md.append("")
        if not self.has_speaker_overlap:
            md.append("> [!NOTE]")
            md.append("> **Zero Speaker Overlap Confirmed:** There are 0 overlapping speakers between the development and test splits. ")
            md.append("> The speaker identity distributions are strictly disjoint, ensuring clean separation for genuine/impostor trial design without identity contamination.")
        else:
            md.append("> [!WARNING]")
            md.append(f"> **Speaker Overlap Detected:** {len(self.speaker_overlap)} speakers appear in multiple splits: `{self.speaker_overlap}`.")
            md.append("> This indicates data leakage if splits are used as independent development and evaluation sets.")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 5. File Integrity & Health Report")
        md.append("")
        if self.total_corrupted_files == 0 and self.total_empty_files == 0:
            md.append("> [!TIP]")
            md.append("> **100% Acoustic Integrity:** All inspected audio files passed header decoding, have valid positive non-zero durations, valid channels, and non-empty byte payloads. Zero corrupted files detected.")
        else:
            md.append(f"- **Corrupted Files ({self.total_corrupted_files}):**")
            for split_name, split in self.splits.items():
                for f in split.corrupted_files:
                    md.append(f"  - `[{split_name}]` `{f['path']}`: {f['error']}")
            md.append(f"- **Empty Files ({self.total_empty_files}):**")
            for split_name, split in self.splits.items():
                for f in split.empty_files:
                    md.append(f"  - `[{split_name}]` `{f['path']}`: 0 bytes")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 6. Evaluation Readiness & Benchmark Limitations")
        md.append("")
        md.append(f"**Suitability Determination:** `{'SUITABLE FOR PHASE 5 BENCHMARKING' if self.is_suitable_for_evaluation else 'NOT SUITABLE'}`  ")
        md.append(f"{self.suitability_summary}")
        md.append("")
        md.append("### Critical Scientific Limitations of LibriSpeech:")
        for idx, lim in enumerate(self.limitations, 1):
            md.append(f"{idx}. {lim}")
        md.append("")

        return "\n".join(md)

    def save_markdown(self, output_path: Path) -> Path:
        """Save report as a Markdown file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate_markdown()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

