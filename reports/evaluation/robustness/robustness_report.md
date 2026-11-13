# SentinelAI Voice Verification — Phase 5D: Statistical Validation & Robustness Analysis

**Report Generated:** `2026-11-12 15:39:54 UTC`  
**Primary Baseline Model:** `speechbrain/spkrec-ecapa-voxceleb`  
**Frozen Decision Threshold (θ\*):** `0.4059` (Calibrated on `dev-clean`)  
**Bootstrap Resampling Strategy:** Dyadic Multiway Speaker-Cluster Bootstrap ($B = 1,000$ Replicates)  

---

## 1. Executive Summary & Experimental Scope

Phase 5D rigorously investigates the empirical stability, sampling uncertainty, and operating robustness of the Phase 5C baseline speaker verification system. **The primary baseline results remain unchanged and anchored:**
- Primary Calibrated Threshold: **$\theta^* = 0.4059$**  
- Test Operational False Acceptance Rate (FAR): **0.28%**  
- Test Operational False Rejection Rate (FRR): **1.02%**  
- Test Classification Accuracy: **99.09%**  
- Test Diagnostic EER: **0.56%**  
- Test ROC-AUC: **0.9996**

---

## 2. Uncertainty Quantification & Speaker-Cluster Bootstrap (95% CIs)

> [!NOTE]
> **Resampling Unit & Theoretical Methodology:**
> In biometrics, trials sharing speakers and audio chapters violate the independent and identically > distributed (i.i.d.) assumption. A naive trial-level bootstrap dramatically underestimates sampling variance. > Here, we employ a **dyadic speaker-cluster bootstrap** with $B = 1,000$ iterations that resamples the 36 unique > speaker clusters with replacement while preserving the pairwise cross-speaker dyad structure. Within every replicate, > the complete ROC/FAR/FRR trajectory is recalculated from scratch to extract continuous EER and ROC-AUC.

| Metric | Observed Baseline | Bootstrap Mean | Bootstrap Median | Standard Error (SE) | 95% Confidence Interval [2.5%, 97.5%] |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FAR (False Accept Rate)** | 0.28% | 0.28% | 0.00% | 0.48% | **[0.00%, 1.64%]** |
| **FRR (False Reject Rate)** | 1.02% | 1.03% | 1.01% | 0.35% | **[0.39%, 1.77%]** |
| **Diagnostic EER** | 0.56% | 0.46% | 0.36% | 0.33% | **[0.04%, 1.19%]** |
| **Classification Accuracy** | 99.09% | 99.07% | 99.08% | 0.31% | **[98.46%, 99.63%]** |
| **Precision** | 99.96% | 99.96% | 100.00% | 0.08% | **[99.73%, 100.00%]** |
| **Recall (1 - FRR)** | 98.98% | 98.97% | 98.99% | 0.35% | **[98.23%, 99.61%]** |
| **F1-Score** | 0.9947 | 0.9946 | 0.9947 | 0.0018 | **[0.9910, 0.9979]** |
| **ROC-AUC** | 0.9996 | 0.9996 | 0.9996 | 0.0003 | **[0.9988, 1.0000]** |

---

## 3. Enrollment Selection Stability Across 5 Random Seeds

To test whether enrollment performance was an artifact of the specific 3 recordings chosen per speaker in Seed 42, we repeated enrollment triplet selection across 5 distinct seeds. For every seed, threshold calibration was performed strictly on development data, frozen, and applied to test data:

| Experiment Condition | Calibrated Threshold (θ\*) | Dev EER (%) | Test FAR (%) | Test FRR (%) | Test Accuracy (%) | Test ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Seed 42 **(Baseline)** | 0.4059 | 1.12% | 0.28% | 1.02% | 99.09% | 0.9996 |
| Seed 123  | 0.4082 | 1.25% | 0.00% | 1.02% | 99.12% | 0.9996 |
| Seed 456  | 0.3941 | 1.05% | 0.00% | 0.93% | 99.20% | 0.9996 |
| Seed 789  | 0.3964 | 1.00% | 0.56% | 0.97% | 99.09% | 0.9996 |
| Seed 2026  | 0.4126 | 1.16% | 0.28% | 1.19% | 98.93% | 0.9996 |

> [!TIP]
> **Enrollment Stability Findings:** Across all 5 seeds, Test Accuracy varied within a narrow band of **98.93% to 99.20%** ($\Delta = 0.27\%$), and FAR remained between **0.00% and 0.56%**. This confirms that reference profile aggregation in ECAPA-TDNN feature space is robust to intra-speaker utterance selection.

---

## 4. Enrollment Recording Quantity Sensitivity (K = 1, 2, 3 Utterances)

To evaluate how reference template accuracy scales with enrollment sample size, we compared nested conditions: $K=1$ (single-shot), $K=2$ (two-shot), and $K=3$ (three-shot baseline):

| Enrollment Utterances (K) | Calibrated Threshold (θ\*) | Dev EER (%) | Test FAR (%) | Test FRR (%) | Test Accuracy (%) | Test ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| K = 1 Utterance   | 0.3920 | 1.32% | 0.00% | 1.33% | 98.86% | 0.9996 |
| K = 2 Utterances  | 0.3991 | 1.25% | 0.28% | 1.15% | 98.97% | 0.9995 |
| K = 3 Utterances **(Baseline)** | 0.4059 | 1.12% | 0.28% | 1.02% | 99.09% | 0.9996 |

> [!IMPORTANT]
> **Interpretation of Sample Quantity:** Single-shot enrollment ($K=1$) displays higher acoustic dispersion > due to utterance-level phoneme and prosodic variability. Aggregating $K=3$ utterances reduces centroid variance > and produces tighter genuine distribution clustering.

---

## 5. Diagnostic Verification Error Analysis

At operating threshold $\theta^* = 0.4059$, the test split produced **24 errors** out of 2,624 trials (0.91% error rate):
- **False Rejections (FR):** 23 trials (1.02% FRR)
- **False Acceptances (FA):** 1 trials (0.28% FAR)
- **Boundary Errors (|score - θ\*| ≤ 0.05):** 11 errors (45.8% of total errors)

### Speaker Error Distribution:

#### Top Most Frequently Rejected Genuine Speakers:
- Speaker `672`: 6 False Rejections
- Speaker `4446`: 4 False Rejections
- Speaker `260`: 3 False Rejections
- Speaker `3729`: 3 False Rejections
- Speaker `5142`: 2 False Rejections

#### Top Speakers Associated with False Acceptances:
- Speaker `3570`: 1 False Acceptances

---

## 6. Threshold Sensitivity & Tolerance Window

We swept the decision threshold from 0.21 to 0.61 in increments of 0.005. The **5% error tolerance window**—defined as the range of thresholds where both $\text{FAR} \le 5.0\%$ and $\text{FRR} \le 5.0\%$—spans:

> **Operating Stability Window:** $\theta \in [0.2700, 0.5350]$ (Width = 0.2650)
> Calibrated threshold $\theta^* = 0.4059$ sits safely inside this operating window.

---

## 7. Research Validity & Limitations

1. **Corpus Scope:** LibriSpeech consists of clean, read audiobook speech from LibriVox (76 total speakers). It does not test natural conversational speech or noisy acoustic environments.
2. **Anti-Spoofing Absence:** All recordings are bona fide. This analysis provides **zero assessment of presentation attack detection (PAD)** against replays, text-to-speech, or voice conversion.
3. **Cross-Corpus Transfer:** The underlying ECAPA-TDNN model was pretrained on VoxCeleb 1 & 2. Performance here evaluates zero-shot cross-corpus generalizability.
4. **Trial Correlation:** While speaker-cluster bootstrap addresses inter-trial correlation, the total participant count (36 test speakers) remains small relative to large-scale operational benchmarks.

---

## 8. Artifact Directory

- Confidence Intervals JSON: [`reports/evaluation/robustness/confidence_intervals.json`](file:///reports/evaluation/robustness/confidence_intervals.json)
- Bootstrap Results JSON: [`reports/evaluation/robustness/bootstrap_results.json`](file:///reports/evaluation/robustness/bootstrap_results.json)
- Multi-Seed Results CSV: [`reports/evaluation/robustness/random_seed_results.csv`](file:///reports/evaluation/robustness/random_seed_results.csv)
- Enrollment Count Results CSV: [`reports/evaluation/robustness/enrollment_count_results.csv`](file:///reports/evaluation/robustness/enrollment_count_results.csv)
- Error Analysis JSON: [`reports/evaluation/robustness/error_analysis.json`](file:///reports/evaluation/robustness/error_analysis.json)
- Threshold Sensitivity CSV: [`reports/evaluation/robustness/threshold_sensitivity.csv`](file:///reports/evaluation/robustness/threshold_sensitivity.csv)
- Figures Directory: [`reports/evaluation/robustness/figures/`](file:///reports/evaluation/robustness/figures)
