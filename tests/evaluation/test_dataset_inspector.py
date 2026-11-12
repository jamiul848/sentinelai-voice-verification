"""Unit tests for the Dataset Inspector and Reporting module (Phase 5A)."""

import io
from pathlib import Path
import json
import numpy as np
import pytest
import soundfile as sf

from sentinelai.evaluation.dataset_inspector import DatasetInspector
from sentinelai.evaluation.dataset_report import format_duration


def create_tiny_audio_file(
    path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
    duration_sec: float = 0.5,
    file_format: str = "WAV",
    subtype: str = "PCM_16",
) -> Path:
    """Helper to generate a tiny valid audio file for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(sample_rate * duration_sec)
    if channels == 1:
        data = (0.5 * np.sin(2 * np.pi * 440.0 * np.linspace(0, duration_sec, num_samples, endpoint=False))).astype(np.float32)
    else:
        sig = (0.5 * np.sin(2 * np.pi * 440.0 * np.linspace(0, duration_sec, num_samples, endpoint=False))).astype(np.float32)
        data = np.column_stack([sig, sig])

    sf.write(str(path), data, sample_rate, format=file_format, subtype=subtype)
    return path


class TestDatasetInspector:
    """Unit test suite for DatasetInspector, metadata parsing, and report generation."""

    def test_format_duration_helper(self) -> None:
        """Verify format_duration correctly formats seconds into human-readable strings."""
        assert format_duration(5.5) == "5.50s"
        assert format_duration(125.0) == "2m 05.00s"
        assert format_duration(3665.5) == "1h 01m 05.50s"
        assert format_duration(-10.0) == "0.00s"

    def test_extract_identifiers_standard_librispeech(self, tmp_path: Path) -> None:
        """Verify standard LibriSpeech regex matching on filename."""
        split_root = tmp_path / "dev-clean"
        file_path = split_root / "1272" / "128104" / "1272-128104-0001.flac"

        spk, chap, utt = DatasetInspector.extract_identifiers(file_path, split_root)
        assert spk == "1272"
        assert chap == "128104"
        assert utt == "0001"

    def test_extract_identifiers_directory_fallback(self, tmp_path: Path) -> None:
        """Verify fallback to directory hierarchy when filename doesn't match standard regex."""
        split_root = tmp_path / "test-clean"
        file_path = split_root / "speaker_alice" / "chapter_01" / "audio_sample.wav"

        spk, chap, utt = DatasetInspector.extract_identifiers(file_path, split_root)
        assert spk == "speaker_alice"
        assert chap == "chapter_01"
        assert utt == "audio_sample"

    def test_inspect_valid_split(self, tmp_path: Path) -> None:
        """Verify inspection of a mock split containing multiple speakers and chapters."""
        split_root = tmp_path / "mock-split"

        # Speaker 100, Chapter 10, 2 utterances
        create_tiny_audio_file(split_root / "100" / "10" / "100-10-0001.wav", duration_sec=0.5)
        create_tiny_audio_file(split_root / "100" / "10" / "100-10-0002.wav", duration_sec=1.0)

        # Speaker 100, Chapter 11, 1 utterance
        create_tiny_audio_file(split_root / "100" / "11" / "100-11-0001.wav", duration_sec=0.8)

        # Speaker 200, Chapter 20, 1 utterance
        create_tiny_audio_file(split_root / "200" / "20" / "200-20-0001.wav", duration_sec=1.2)

        inspector = DatasetInspector(dataset_root=tmp_path, split_names=["mock-split"])
        report = inspector.inspect_split("mock-split")

        assert report.total_speakers == 2
        assert report.total_chapters == 3
        assert report.total_utterances == 4
        assert pytest.approx(report.total_duration_sec, abs=0.1) == 3.5
        assert report.min_duration_sec == pytest.approx(0.5, abs=0.05)
        assert report.max_duration_sec == pytest.approx(1.2, abs=0.05)
        assert report.sample_rate_distribution.get(16000) == 4
        assert report.channel_distribution.get(1) == 4
        assert len(report.corrupted_files) == 0
        assert len(report.empty_files) == 0

        # Check speaker metrics
        spk_100 = report.speakers["100"]
        assert spk_100.utterance_count == 3
        assert spk_100.chapter_count == 2
        assert pytest.approx(spk_100.total_duration_sec, abs=0.1) == 2.3

    def test_detect_empty_file(self, tmp_path: Path) -> None:
        """Verify detection of zero-byte audio files."""
        split_root = tmp_path / "mock-split"
        empty_file = split_root / "100" / "10" / "100-10-0001.wav"
        empty_file.parent.mkdir(parents=True, exist_ok=True)
        empty_file.write_bytes(b"")

        inspector = DatasetInspector(dataset_root=tmp_path, split_names=["mock-split"])
        report = inspector.inspect_split("mock-split")

        assert report.total_utterances == 0
        assert len(report.empty_files) == 1
        assert "0 bytes" in report.empty_files[0]["error"]

    def test_detect_corrupted_file(self, tmp_path: Path) -> None:
        """Verify detection of corrupt audio files that fail SoundFile decoding."""
        split_root = tmp_path / "mock-split"
        corrupt_file = split_root / "100" / "10" / "100-10-0001.flac"
        corrupt_file.parent.mkdir(parents=True, exist_ok=True)
        corrupt_file.write_bytes(b"fLaC\x00\x00\x00\x00THIS_IS_CORRUPT_PAYLOAD")

        inspector = DatasetInspector(dataset_root=tmp_path, split_names=["mock-split"])
        report = inspector.inspect_split("mock-split")

        assert report.total_utterances == 0
        assert len(report.corrupted_files) == 1
        assert "SoundFile decoding error" in report.corrupted_files[0]["error"]

    def test_speaker_overlap_detection(self, tmp_path: Path) -> None:
        """Verify detection of overlapping speaker IDs across splits."""
        dev_root = tmp_path / "dev-clean"
        test_root = tmp_path / "test-clean"

        # Speaker 100 is in BOTH dev and test
        create_tiny_audio_file(dev_root / "100" / "10" / "100-10-0001.wav")
        create_tiny_audio_file(dev_root / "200" / "10" / "200-10-0001.wav")

        create_tiny_audio_file(test_root / "100" / "10" / "100-10-0002.wav")
        create_tiny_audio_file(test_root / "300" / "10" / "300-10-0001.wav")

        inspector = DatasetInspector(dataset_root=tmp_path, split_names=["dev-clean", "test-clean"])
        overall_report = inspector.inspect_dataset()

        assert overall_report.has_speaker_overlap is True
        assert "100" in overall_report.speaker_overlap
        assert overall_report.total_speakers == 3  # 100, 200, 300
        assert overall_report.is_suitable_for_evaluation is False

    def test_zero_speaker_overlap_disjoint(self, tmp_path: Path) -> None:
        """Verify that disjoint splits report zero speaker overlap."""
        dev_root = tmp_path / "dev-clean"
        test_root = tmp_path / "test-clean"

        create_tiny_audio_file(dev_root / "100" / "10" / "100-10-0001.wav")
        create_tiny_audio_file(dev_root / "200" / "10" / "200-10-0001.wav")

        create_tiny_audio_file(test_root / "300" / "10" / "300-10-0001.wav")
        create_tiny_audio_file(test_root / "400" / "10" / "400-10-0001.wav")

        inspector = DatasetInspector(dataset_root=tmp_path, split_names=["dev-clean", "test-clean"])
        overall_report = inspector.inspect_dataset()

        assert overall_report.has_speaker_overlap is False
        assert len(overall_report.speaker_overlap) == 0
        assert overall_report.total_speakers == 4
        assert overall_report.is_suitable_for_evaluation is True

    def test_missing_split_directory_handled_gracefully(self, tmp_path: Path) -> None:
        """Verify missing directory does not raise an unhandled exception."""
        inspector = DatasetInspector(dataset_root=tmp_path, split_names=["nonexistent-split"])
        split_report = inspector.inspect_split("nonexistent-split")

        assert split_report.total_utterances == 0
        assert split_report.total_speakers == 0

        overall = inspector.inspect_dataset()
        assert overall.total_utterances == 0

    def test_json_and_markdown_export(self, tmp_path: Path) -> None:
        """Verify saving and re-loading structured JSON and Markdown reports."""
        split_root = tmp_path / "dev-clean"
        create_tiny_audio_file(split_root / "100" / "10" / "100-10-0001.wav", duration_sec=1.0)

        inspector = DatasetInspector(dataset_root=tmp_path, split_names=["dev-clean"])
        report = inspector.inspect_dataset()

        json_out = tmp_path / "report.json"
        md_out = tmp_path / "report.md"

        report.save_json(json_out)
        report.save_markdown(md_out)

        assert json_out.exists()
        assert md_out.exists()

        with open(json_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_speakers"] == 1
        assert data["total_utterances"] == 1

        md_content = md_out.read_text(encoding="utf-8")
        assert "# SentinelAI Dataset Inspection & Validation Report" in md_content
        assert "100% Acoustic Integrity" in md_content

