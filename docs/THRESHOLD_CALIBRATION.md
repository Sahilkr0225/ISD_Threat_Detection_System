# Threshold Calibration & Phase 3 Alert Policy

## 1. Validation-Only Calibration
All candidate operating thresholds were derived **exclusively** on `data/processed/validation.parquet` (`60,812` rows, `100` unique dates, `255` malicious days) without inspecting `test.parquet`:

| Policy | Threshold | Val Alert Rate | Test Alert Rate | Test Avg Alerts/Day | Test Precision | Test Recall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `top_1pct_threshold` | `0.125988` | `1.00%` | `0.88%` (`541`) | `5.36` | `0.0037` | `0.0130` (`2/154`) |
| `top_2pct_threshold` | `0.099136` | `2.00%` | `1.69%` (`1,038`) | `10.28` | `0.0096` | `0.0649` (`10/154`) |
| `sklearn_default_zero` | `0.000000` | `11.58%` | `10.87%` (`6,682`) | `66.16` | `0.0111` | `0.4805` (`74/154`) |
| `f1_optimal_threshold` | `-0.042262` | `17.53%` | `16.71%` (`10,271`) | `101.69` | `0.0120` | `0.7987` (`123/154`) |

## 2. False-Positive Burden & Operational Recommendation for Phase 3
- Because CERT r4.2 malicious days represent only `0.25%` of test observations, **all** purely unsupervised thresholds exhibit low precision (`0.37%–1.20%`) and high false-positive volume at high-recall settings (`~66` to `~102` alerts/day across 1,000 employees).
- **Recommended Phase 3 Policy:** Use a **configurable, tiered risk prioritization policy** rather than a single high-volume binary cutoff:
  1. Map `anomaly_score` to a **0–100 normalized risk score** (prioritization indicator, never a probability of guilt).
  2. Default **High/Critical alert queue** at `top_2pct_threshold` (`0.099136`, ~`10` alerts/day across 1,000 employees) for immediate SOC triage, while surfacing `sklearn_default_zero` (`0.0`) and `f1_optimal_threshold` (`-0.042262`) as **Medium/Low** watchlist tiers or configurable slider thresholds in the dashboard.

