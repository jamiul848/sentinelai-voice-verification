# Real ECAPA-TDNN Evaluation & Performance Report

**Date:** November 12, 2026  
**Architecture:** ECAPA-TDNN (`speechbrain/spkrec-ecapa-voxceleb`, 192 dimensions)  
**Corpus:** LibriSpeech `dev-clean` (Calibration) and `test-clean` (Frozen Test)  
**Verification Protocol:** 1:1 Biometric Verification, Cosine Similarity  
**Standards Compliance:** ISO/IEC 19795-1 Biometric Performance Testing and Reporting  

---

## 1. Primary Benchmark Results

The table below presents the verified real performance metrics computed from genuine ECAPA-TDNN inference on LibriSpeech recordings:

| Performance Metric | Development Split (`dev-clean`) | Test Split (`test-clean`) | 95% Bootstrap Confidence Interval |
| :--- | :---: | :---: | :---: |
| **Operating Role** | **Calibration Corpus** | **Frozen Evaluation** | **Uncertainty Quantification** |
| **Decision Threshold ($\theta^*$)** | **0.4059** (Calibrated at EER) | **0.4059** (Frozen) | Fixed at $\theta^* = 0.4059$ |
| **Total Evaluation Trials** | 2,983 trials | 2,624 trials | 2,624 trials |
| **Genuine Trials** | 2,583 trials | 2,264 trials | 2,264 trials |
| **Impostor Trials** | 400 trials | 360 trials | 360 trials |
| **Equal Error Rate (EER)** | **1.12%** | **0.56%** (Diagnostic) | **[0.04%, 1.19%]** |
| **False Acceptance Rate (FAR)** | **1.25%** | **0.28%** | **[0.00%, 1.64%]** |
| **False Rejection Rate (FRR)** | **1.12%** | **1.02%** | **[0.39%, 1.77%]** |
| **Classification Accuracy** | **98.86%** | **99.09%** | **[98.46%, 99.63%]** |
| **Precision** | **99.80%** | **99.96%** | **[99.73%, 100.00%]** |
| **Recall ($1 - \text{FRR}$)** | **98.88%** | **98.98%** | **[98.23%, 99.61%]** |
| **F1-Score** | **0.9934** | **0.9947** | **[0.9910, 0.9979]** |
| **Area Under ROC Curve (ROC-AUC)** | **0.9995** | **0.9996** | **[0.9988, 1.0000]** |

---

## 2. Test Confusion Matrix Analysis

Operating at the frozen threshold $\theta^* = 0.4059$:

```
                       Actual Genuine       Actual Impostor
Predicted Genuine        2,241 (TP)               1 (FP)
Predicted Impostor          23 (FN)             359 (TN)
```

- **True Acceptance Rate (TAR):** $2,241 / 2,264 = 98.98\%$
- **True Rejection Rate (TRR):** $359 / 360 = 99.72\%$
- **Total Verification Errors:** 24 out of 2,624 trials ($0.91\%$ error rate).
- **Security Posture:** Only 1 out of 360 impostor attempts bypassed verification ($\text{FAR} = 0.28\%$), demonstrating high resistance to zero-effort impostors.

---

## 3. Score Distribution Statistics

| Split | Minimum Score | Mean Impostor Score | Calibrated Threshold ($\theta^*$) | Mean Genuine Score | Maximum Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`dev-clean`** | -0.1283 | 0.0701 | **0.4059** | 0.7712 | 0.9679 |
| **`test-clean`** | -0.1339 | 0.0906 | **0.4059** | 0.7571 | 0.9460 |

The genuine and impostor distributions exhibit exceptional separation ($\Delta\mu \approx 0.67$), explaining the near-perfect ROC-AUC of **0.9996**.

