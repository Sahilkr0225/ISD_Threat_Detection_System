# Risk Scoring & Priority Classification

**Implementation:** `backend/app/risk/scoring.py`

## 1. Mathematical Formula (Validation-Reference Percentile)
For a raw Isolation Forest anomaly score $s = -\text{decision\_function}(x)$, the normalized risk score is:

$$\text{risk\_score}(s) = 100.0 \times \frac{\text{searchsorted}(\mathbf{S}_{\text{val}}, s, \text{side}=\text{"right"})}{|\mathbf{S}_{\text{val}}|}$$

where $\mathbf{S}_{\text{val}}$ is the frozen sorted validation anomaly score distribution (`models/validation_score_reference.npy`, $N = 60{,}812$).

- **Properties:** Bounded in $[0.0, 100.0]$, monotonically non-decreasing in $s$, deterministic on ties (`side="right"`), and independent of held-out test data or incoming request batch size.
- **Interpretation:** `risk_score` is an **anomaly prioritization percentile**, **not** a probability that an employee is malicious.

## 2. Investigation Priority Classification Policy
Evaluated in descending order against exact persisted validation-calibrated thresholds (`models/isolation_forest_v1.joblib`):

| Priority | Raw Anomaly Score Condition | Exact Threshold | Held-Out Test Alert Count |
| :--- | :--- | :---: | :---: |
| **Critical** | $s \ge \text{top\_1pct\_threshold}$ | `0.12598789585707226` | 541 |
| **High** | $\text{top\_2pct} \le s < \text{Critical}$ | `0.09913609888340638` | 497 |
| **Medium** | $0.0 \le s < \text{High}$ | `0.0` | 5,644 |
| **Low** | $\text{f1\_optimal} \le s < \text{Medium}$ | `-0.04226230960953481` | 3,589 |
| **Informational** | $s < \text{f1\_optimal}$ | — | 51,202 *(not alerted)* |

- **Precision/Recall Trade-Off:** Because malicious days represent `0.25%` of test observations, the broad F1-optimized queue (`10,271` alerts) captures `79.87%` recall at `1.20%` precision, whereas `High/Critical` (`1,038` alerts, `~10.3/day`) supports capacity-limited SOC triage.

