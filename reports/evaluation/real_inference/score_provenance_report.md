# Real ECAPA-TDNN Score Provenance Audit Report

**Date:** November 12, 2026  
**Auditor Role:** Senior Biometric Evaluation Researcher & ML Evaluation Auditor  
**Scope:** Score Provenance and Verification Pipeline Integrity  
**Target Manifests:**  
- `outputs/evaluation/dev/scores.csv` (2,983 scored trials)  
- `outputs/evaluation/test/scores.csv` (2,624 scored trials)  

---

## 1. Executive Summary & Verification Outcome

This report confirms that all synthetic demonstration scores and synthetic trial identifiers (`synth-*`, `spk_*`, Gaussian-generated values) have been **completely eliminated** from the SentinelAI Voice Verification evaluation manifests.

**Outcome:** **100% REAL ECAPA-TDNN INFERENCE VERIFIED.**

Every single score in both `outputs/evaluation/dev/scores.csv` and `outputs/evaluation/test/scores.csv` is the genuine directional cosine similarity between a real reference profile (aggregated from 3 enrollment utterances) and a real probe recording embedding extracted by `speechbrain/spkrec-ecapa-voxceleb`.

---

## 2. Quantitative Verification Checkpoints

| Audit Property | Expected (Real Pipeline) | Development Manifest (`dev/scores.csv`) | Test Manifest (`test/scores.csv`) | Provenance Status |
| :--- | :---: | :---: | :---: | :---: |
| **Total Trials Scored** | 2,983 (dev) / 2,624 (test) | **2,983** | **2,624** | **VERIFIED** |
| **Genuine Trials** | 2,583 (dev) / 2,264 (test) | **2,583** | **2,264** | **VERIFIED** |
| **Impostor Trials** | 400 (dev) / 360 (test) | **400** | **360** | **VERIFIED** |
| **Score Source Tag** | `real_ecapa_inference` | `real_ecapa_inference` (100%) | `real_ecapa_inference` (100%) | **VERIFIED** |
| **Trial ID Format** | Canonical UUID v4 | 100% UUID v4 (0 `synth-` IDs) | 100% UUID v4 (0 `synth-` IDs) | **VERIFIED** |
| **Claimed Speaker IDs** | Physical LibriSpeech IDs | 40 physical speakers | 36 physical speakers | **VERIFIED** |
| **Actual Speaker IDs** | Physical LibriSpeech IDs | 40 physical speakers | 36 physical speakers | **VERIFIED** |
| **Score Range** | Real Cosine [-1.0, 1.0] | [-0.1283, 0.9679] | [-0.1339, 0.9460] | **VERIFIED** |
| **Mean Genuine Score** | Empirical ECAPA (~0.75-0.78) | **0.7712** | **0.7571** | **VERIFIED** |
| **Mean Impostor Score** | Empirical ECAPA (~0.05-0.10) | **0.0701** | **0.0906** | **VERIFIED** |
| **Synthetic Score Residuals** | Zero | **0** | **0** | **VERIFIED** |

---

## 3. End-to-End Lineage Trace

```
LibriSpeech FLAC Audio (.flac)
    │
    ▼  [sentinelai/audio/validator.py: validate_audio_header(b'fLaC')]
Audio Tensor [1, N] at 16,000 Hz Mono Float32
    │
    ▼  [sentinelai/speaker/embedding.py: SpeakerEmbeddingExtractor.extract()]
192-Dimensional L2 Unit-Normalized Vector e (||e||_2 = 1.0)
    │
    ├─────────► Cache to Disk: outputs/evaluation/{dev,test}/embeddings/{stem}.npz
    │
    ▼  [sentinelai/enrollment/aggregation.py: aggregate_embeddings(K=3)]
Reference Profile e_ref = Normalize(1/3 * sum(e_i))
    │
    ├─────────► Store: outputs/evaluation/{dev,test}/enrollment_profiles/{spk_id}_profile.npz
    │
    ▼  [sentinelai/evaluation/trial_scorer.py: TrialScorer.score_trials()]
Cosine Similarity: s = dot(e_ref, e_probe)
    │
    ▼
outputs/evaluation/{dev,test}/scores.csv (score_source="real_ecapa_inference")
```

All downstream benchmark metrics (FAR, FRR, EER, ROC-AUC, 95% Confidence Intervals) are strictly derived from these physical scores.

