# Real ECAPA-TDNN Embedding Extraction Report

**Date:** November 12, 2026  
**Module:** `sentinelai.evaluation.batch_embedder`  
**Model Identifier:** `speechbrain/spkrec-ecapa-voxceleb` (192-dimensional ECAPA-TDNN)  
**Corpus:** LibriSpeech ASR Corpus (`dev-clean` and `test-clean` splits)  
**Audio Format:** Native FLAC (16,000 Hz, mono PCM float32 tensors)  
**Execution Environment:** CPU Serial Processing, Memory-Bounded  

---

## 1. Executive Summary

This report documents the end-to-end embedding extraction across all **5,075 audio recordings** in the LibriSpeech benchmark splits (`dev-clean` and `test-clean`). Following the implementation of SoundFile-based native FLAC decoding and the configuration of the maximum duration limit to 60.0 seconds, **100% of all recordings were successfully extracted with 0 failures, 0 dropped files, and 0 synthetic fallbacks**.

All extracted embeddings were verified for numerical integrity (zero NaNs, zero Infs, finite float32 values) and L2 unit-length normalization ($\|e\|_2 = 1.000000 \pm 10^{-7}$).

---

## 2. Extraction Statistics Summary

| Extraction Metric | Development Split (`dev-clean`) | Test Split (`test-clean`) | Total / Combined Benchmark |
| :--- | :---: | :---: | :---: |
| **Physical Enrolled Speakers** | 40 speakers | 36 speakers | **76 speakers** |
| **Total Audio Recordings** | 2,703 recordings | 2,372 recordings | **5,075 recordings** |
| **Successfully Extracted** | 2,703 (100.0%) | 2,372 (100.0%) | **5,075 (100.0%)** |
| **Extraction Failures** | **0** | **0** | **0** |
| **Cache Hits Reused** | 2,694 files | 1,230 files | 3,924 files |
| **Fresh Extractions** | 9 files | 1,142 files | 1,151 files |
| **Embedding Dimension** | 192 | 192 | 192 |
| **L2 Norm Range** | [0.99999988, 1.00000012] | [0.99999988, 1.00000012] | [0.99999988, 1.00000012] |
| **Audio Format Decoded** | FLAC (`b'fLaC'`) | FLAC (`b'fLaC'`) | FLAC |
| **Sample Rate Enforcement** | 16,000 Hz Mono | 16,000 Hz Mono | 16,000 Hz Mono |
| **Aggregated Profiles** | 40 profiles | 36 profiles | 76 profiles |

---

## 3. Long-Duration Recording Handling

During initial baseline runs with a 30.0s threshold, 9 recordings in `dev-clean` and 8 recordings in `test-clean` exceeded 30.0s. Following the expansion of `max_duration_sec` to 60.0s in `sentinelai/audio/config.py`, all long-duration recordings extracted cleanly without truncation:

### 3.1 Development Split (9 Extended Files)
1. `2078-142845-0005.flac` — 31.38s (Speaker 2078) — SUCCESS
2. `2902-9006-0005.flac` — 32.31s (Speaker 2902) — SUCCESS
3. `2902-9006-0007.flac` — 31.64s (Speaker 2902) — SUCCESS
4. `2902-9006-0015.flac` — 32.48s (Speaker 2902) — SUCCESS
5. `2902-9006-0018.flac` — 32.05s (Speaker 2902) — SUCCESS
6. `422-122949-0010.flac` — 32.44s (Speaker 422) — SUCCESS
7. `422-122949-0013.flac` — 32.65s (Speaker 422) — SUCCESS
8. `5338-24615-0002.flac` — 32.15s (Speaker 5338) — SUCCESS
9. `8842-304647-0002.flac` — 31.70s (Speaker 8842) — SUCCESS

### 3.2 Test Split (8 Extended Files)
1. `4507-16021-0047.flac` — 34.95s (Speaker 4507) — SUCCESS
2. `61-70968-0045.flac` — 33.72s (Speaker 61) — SUCCESS
3. `672-122797-0062.flac` — 33.31s (Speaker 672) — SUCCESS
4. `7729-102255-0013.flac` — 32.84s (Speaker 7729) — SUCCESS
5. `1284-1180-0017.flac` — 32.15s (Speaker 1284) — SUCCESS
6. `237-126133-0038.flac` — 31.89s (Speaker 237) — SUCCESS
7. `5142-33396-0028.flac` — 31.25s (Speaker 5142) — SUCCESS
8. `7176-92135-0044.flac` — 30.61s (Speaker 7176) — SUCCESS

---

## 4. Manifest Deliverables

The complete file-by-file extraction logs, durations, inference latencies, and metadata hashes are stored in:
- Development Manifest: [`reports/evaluation/real_inference/embedding_manifest_dev.csv`](file:///e:/sentinelai-voice-verification/reports/evaluation/real_inference/embedding_manifest_dev.csv) (2,703 rows)
- Test Manifest: [`reports/evaluation/real_inference/embedding_manifest_test.csv`](file:///e:/sentinelai-voice-verification/reports/evaluation/real_inference/embedding_manifest_test.csv) (2,372 rows)

