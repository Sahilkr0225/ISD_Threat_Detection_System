# Phase 2 Model Evaluation Report

**Algorithm:** Unscaled `IsolationForest` (`n_estimators=200`, `max_samples=256`, `contamination="auto"`, `random_state=42`)  
**Training Set:** `data/processed/train.parquet` (`208,167` rows, strictly **unsupervised** — zero labels supplied)  
**Model Artifact:** `models/isolation_forest_v1.joblib`

## 1. Validation Ablation (6-Feature Raw Baseline vs. 20-Feature Engineered)
Evaluated on `data/processed/validation.parquet` (`60,812` rows, `255` malicious days, base rate `0.004193`):

| Configuration | Features | Fit Time | Val ROC-AUC | Val PR-AUC | Top-250 Hits (Lift) | Top-1000 Hits (Lift) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `raw_baseline_6` | 6 | 2.372s | 0.8393 | 0.0127 | 3 (`2.86x`) | 4 (`0.95x`) |
| **`full_engineered_20`** | **20** | **1.655s** | **0.8826** | **0.0177** | **7 (`6.68x`)** | **17 (`4.05x`)** |

**Selection Decision:** `full_engineered_20` outperformed `raw_baseline_6` on both Validation ROC-AUC (`+0.0433`) and PR-AUC (`+0.0050`), as well as Top-250/500/1000 lift.

## 2. Held-Out Test Evaluation (`full_engineered_20`)
Evaluated **once** on `data/processed/test.parquet` (`61,473` rows, `154` malicious days, base rate `0.002505`):
- **Test ROC-AUC:** **`0.8843`** (consistent with Validation `0.8826`)
- **Test PR-AUC:** **`0.0105`** (`4.19x` over `0.002505` base rate)

### Validation-Calibrated Operating Thresholds on Held-Out Test
| Threshold Policy | Value | Alert Rate | Precision | Recall | F1 | Scenario Recall (`S1 / S2 / S3`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `f1_optimal_threshold` | `-0.042262` | `16.71%` (`10,271`) | `0.0120` | **`0.7987`** (`123/154`) | `0.0236` | `100% / 78.47% / 100%` |
| `sklearn_default_zero` | `0.000000` | `10.87%` (`6,682`) | `0.0111` | `0.4805` (`74/154`) | `0.0217` | `100% / 45.14% / 50%` |
| `top_2pct_threshold` | `0.099136` | `1.69%` (`1,038`) | `0.0096` | `0.0649` (`10/154`) | `0.0168` | `75% / 2.08% / 50%` |
| `top_1pct_threshold` | `0.125988` | `0.88%` (`541`) | `0.0037` | `0.0130` (`2/154`) | `0.0058` | `12.5% / 0% / 50%` |

## 3. Interpretation & Operational Implications for Phase 3
- Because CERT r4.2 malicious days represent only `0.25%` of test observations and many Scenario 2/3 days blend into normal daily volume, a **purely unsupervised** Isolation Forest achieves strong ranking (`ROC-AUC = 0.8843`) and high recall (`79.87%`) at broader score thresholds, while strict top-1% thresholds miss subtle Scenario 2 days.
- Therefore, in **Phase 3**, continuous anomaly scores will be mapped to **0–100 normalized risk scores** with **tiered alert severities** (`Low`, `Medium`, `High`, `Critical`) and **per-feature deviation explanations** so security analysts can triage high-risk employees and behavioural shifts rather than relying on a single binary cutoff.
- **Reminder:** An anomaly score is a statistical indicator of deviation, **never** proof of malicious intent.

## 4. Generated Figures
- `reports/figures/06_phase2_pr_roc_curves.png`
- `reports/figures/07_phase2_test_score_distribution.png`

