# SentinelAI Dataset Inspection & Validation Report: LibriSpeech (dev-clean & test-clean)

**Inspection Timestamp (UTC):** `2026-11-12T05:51:03.042861+00:00`  
**Dataset Root Directory:** `datasets\librispeech`  
**Overall Status:** `VALIDATED & SUITABLE`

---

## 1. Executive Summary

| Metric | Overall Total |
| :--- | :--- |
| **Total Splits Inspected** | 2 (dev-clean, test-clean) |
| **Unique Speakers** | **76** |
| **Total Chapters** | **174** |
| **Total Audio Utterances** | **5,075** |
| **Total Audio Duration** | **10h 11m 01.55s** (36661.55 s) |
| **Corrupted Audio Files** | **0** |
| **Empty (0-byte) Files** | **0** |
| **Dev/Test Speaker Overlap** | **0** (None (Disjoint)) |

---

## 2. Split Comparison & Acoustic Properties

| Metric | `dev-clean` | `test-clean` |
| :--- | :---: | :---: |
| **Speakers** | 40 | 36 |
| **Chapters** | 97 | 77 |
| **Utterances** | 2,703 | 2,372 |
| **Total Duration** | 5h 23m 16.12s | 4h 47m 45.43s |
| **Mean Duration** | 7.18 s (±4.70) | 7.28 s (±5.08) |
| **Min / Max Duration** | 1.45s / 32.65s | 1.28s / 34.95s |
| **Total Size** | 342.40 MB | 312.11 MB |

---

## 3. Acoustic Signal Distributions

### Split: `dev-clean`

- **Sample Rates:** 16000 Hz (2703 files)
- **Channels:** Mono (2703 files)
- **Subtypes / Bit Depth:** PCM_16 (2703 files)
- **Audio Formats:** FLAC (2703 files)

### Split: `test-clean`

- **Sample Rates:** 16000 Hz (2372 files)
- **Channels:** Mono (2372 files)
- **Subtypes / Bit Depth:** PCM_16 (2372 files)
- **Audio Formats:** FLAC (2372 files)

---

## 4. Speaker Overlap & Data Leakage Assessment

> [!NOTE]
> **Zero Speaker Overlap Confirmed:** There are 0 overlapping speakers between the development and test splits. 
> The speaker identity distributions are strictly disjoint, ensuring clean separation for genuine/impostor trial design without identity contamination.

---

## 5. File Integrity & Health Report

> [!TIP]
> **100% Acoustic Integrity:** All inspected audio files passed header decoding, have valid positive non-zero durations, valid channels, and non-empty byte payloads. Zero corrupted files detected.

---

## 6. Evaluation Readiness & Benchmark Limitations

**Suitability Determination:** `SUITABLE FOR PHASE 5 BENCHMARKING`  
The dataset is fully suitable as a controlled, clean development testbed for Phase 5B (Enrollment & Genuine/Impostor Trial Generation) and Phase 5C (Equal Error Rate Calibration). The zero speaker overlap guarantees that the dev-clean and test-clean splits are strictly disjoint, preventing biometric evaluation leakage.

### Critical Scientific Limitations of LibriSpeech:
1. Read Audiobook Speech Domain: Utterances originate from LibriVox audiobooks (clean read speech), lacking the prosodic variance, conversational turn-taking, and emotional shifts of real-world dialogue.
2. High Acoustic Cleanliness: The recordings have near-studio Signal-to-Noise Ratio (SNR) with minimal background noise or reverberation, not testing acoustic robustness or cross-channel variability.
3. ASR Origin: LibriSpeech was compiled primarily for speech-to-text benchmark evaluations; speaker verification trials (genuine and impostor pairs) must be synthetically coupled rather than collected as natural multi-session claimant trials.
4. Phonetic & Lexical Disparity: Because each speaker reads different book chapters, differences in lexical content may introduce phonetic variance that influences ECAPA-TDNN feature trajectories.
5. Absence of Synthetic / Replay Spoofs: The dataset contains exclusively bona fide recordings and provides zero presentation attack detection (PAD) samples for anti-spoofing evaluations.
