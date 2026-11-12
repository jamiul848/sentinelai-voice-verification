# SentinelAI Voice Verification — Phase 5C: Threshold Calibration & Performance Analysis

**Report Generated:** `2026-11-12 06:26:47 UTC`  
**Pretrained Model:** `speechbrain/spkrec-ecapa-voxceleb`  
**Scoring Metric:** `cosine_similarity` (Cosine Similarity in [-1.0, 1.0])  
**Operating Decision Threshold (θ*):** `0.6057` (Calibrated on dev-clean)

---

## 1. Executive Summary & Calibration Protocol

Phase 5C establishes an empirical benchmark evaluation and decision threshold calibration for the SentinelAI speaker recognition pipeline. In accordance with biometric evaluation standards:
1. **Calibration:** Operating threshold $\theta^* = 0.6057$ was calibrated strictly on `dev-clean` by finding the point minimizing the difference between False Acceptance Rate (FAR) and False Rejection Rate (FRR) (Equal Error Rate operating point: 3.41%).
2. **Threshold Freezing:** The calibrated threshold was frozen into an immutable configuration without any hyperparameter tuning on the test partition.
3. **Independent Evaluation:** The exact frozen threshold $\theta^*$ was subsequently evaluated on `test-clean` (2,624 trials across 2,264 genuine and 360 impostor comparisons), guaranteeing zero test-to-threshold data contamination.

---

## 2. Performance Comparison: Development vs. Test Partitions

| Metric | Development Split (`dev-clean`) | Test Split (`test-clean`) | Generalization Gap (Δ) |
| :--- | :---: | :---: | :---: |
| **Calibration Status** | **Calibrated Operating Point** | **Frozen Evaluation (Unseen)** | — |
| **Decision Threshold (θ)** | **0.6057** | **0.6057 (Frozen)** | 0.0000 |
| **Total Trials** | 2,983 | 2,624 | — |
| **Genuine Trials** | 2,583 | 2,264 | — |
| **Impostor Trials** | 400 | 360 | — |
| **False Acceptance Rate (FAR)** | **3.50%** | **1.94%** | 1.56% |
| **False Rejection Rate (FRR)** | **3.41%** | **2.65%** | 0.76% |
| **Classification Accuracy** | 96.58% | 97.45% | 0.87% |
| **Precision** | 99.44% | 99.68% | — |
| **Recall (1 - FRR)** | 96.59% | 97.35% | — |
| **F1-Score** | 0.9800 | 0.9850 | — |
| **ROC-AUC** | **0.9954** | **0.9976** | 0.0022 |
| **Equal Error Rate (EER)** | **3.41%** (Operating) | **2.47%** (Diagnostic only) | 0.93% |

> [!IMPORTANT]
> **Operational Error vs. Diagnostic EER:**
> On `test-clean`, the operational error rates achieved by applying the frozen threshold $\theta^* = 0.6057$ are **FAR = 1.94%** and **FRR = 2.65%**. 
> The test split's theoretical EER (2.47%) is reported strictly as an acoustic diagnostic metric; the threshold was not recalibrated to match test data.

---

## 3. Confusion Matrix Breakdown at Operating Threshold

### Decision Rule: $\text{Decision}(s) = \text{MATCH}$ if $s \ge 0.6057$, else $\text{NO\_MATCH}$

#### Test Partition (`test-clean`):

| True Condition | Predicted MATCH (1) | Predicted NO_MATCH (0) | Total |
| :--- | :---: | :---: | :---: |
| **Genuine Speaker** | **TP = 2,204** (97.3%) | **FN (FR) = 60** (2.65%) | 2,264 |
| **Impostor Speaker** | **FP (FA) = 7** (1.94%) | **TN = 353** (98.1%) | 360 |
| **Total** | 2,211 | 413 | **2,624** |

---

## 4. Benchmark Visualizations

All figures are generated via Matplotlib and saved to `reports/evaluation/figures/`:

1. **Receiver Operating Characteristic (ROC) Curve:** Demonstrates true positive rate vs. false alarm rate across all possible thresholds.
2. **Detection Error Trade-off (DET) Curve:** Displays miss probability vs. false alarm probability on normal deviate scales.
3. **FAR & FRR vs. Threshold Curve:** Shows the error crossover point determining Equal Error Rate.
4. **Cosine Similarity Score Distributions:** Dual histograms demonstrating acoustic separation between genuine and impostor trials.
5. **Confusion Matrix Heatmap:** Normalized classification breakdown at the operating point.

---

## 5. Critical Research Validity & Academic Disclaimers

To uphold rigorous scientific standards in biometrics and machine learning research, the following methodological limitations must be explicitly recognized:

1. **Domain Mismatch & Read Speech Nature:** LibriVox audiobook recordings represent scripted read speech recorded with high vocal projection, consistent cadence, and minimal emotional volatility. Performance metrics do not directly generalize to conversational speech, telephony channels, or spontaneous dialogue.
2. **Acoustic Cleanliness (High SNR):** Recordings exhibit near-studio cleanliness with low ambient noise and negligible room reverberation. Real-world acoustic degradations (cocktail party noise, street traffic, reverberant rooms) will degrade directional cosine similarity.
3. **Absence of Presentation Attacks (Anti-Spoofing):** LibriSpeech contains 100% bona fide human recordings. The system was evaluated solely on zero-effort impostor attempts. It provides **zero defense against physical acoustic replays, speech synthesis (TTS), or voice conversion deepfakes**. A production biometric pipeline must incorporate a dedicated Presentation Attack Detection (PAD) front-end.
4. **Pretrained Model Heritage:** The underlying ECAPA-TDNN was pretrained on the VoxCeleb 1 & 2 datasets (`speechbrain/spkrec-ecapa-voxceleb`). Consequently, this benchmark constitutes a cross-corpus evaluation rather than an in-domain fine-tuned evaluation.
5. **Statistical Dependency Among Trials:** Multiple trials originate from the same pool of speakers and chapters. Trials are statistically correlated and cannot be treated as completely independent human subject samples. The total trial count (5,607) reflects verification attempts, not the number of independent participants (76 speakers).

---

## 6. Artifact Artifact Locations

- Calibrated Threshold: [`reports/evaluation/calibrated_threshold.json`](file:///reports/evaluation/calibrated_threshold.json)
- Development Metrics: [`reports/evaluation/development_metrics.json`](file:///reports/evaluation/development_metrics.json)
- Test Metrics: [`reports/evaluation/test_metrics.json`](file:///reports/evaluation/test_metrics.json)
- Benchmark Figures: [`reports/evaluation/figures/`](file:///reports/evaluation/figures)
