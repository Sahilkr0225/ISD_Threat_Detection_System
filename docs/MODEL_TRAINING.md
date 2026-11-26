# Phase 2 Model Training & Score Semantics

## 1. Training Methodology
- **Training Data:** Fitted **exclusively** on `data/processed/train.parquet` (`208,167` rows, `2010-01-02` to `2010-10-28`). Zero ground-truth labels are supplied to `IsolationForest.fit()`.
- **No Feature Scaling:** Isolation Forest partitions feature space with random axis-aligned cuts, which are invariant to monotonic feature scaling. An unscaled pipeline avoids fitting an unnecessary `StandardScaler`.
- **Hyperparameters (`random_state=42`):**
  - `n_estimators=200` (increased from `100` to `200` to reduce Monte Carlo variance of random tree splits on 208k rows while keeping training time under 2 seconds).
  - `max_samples=256`, `contamination="auto"`, `max_features=1.0`.
  - **Controlled Ablation:** Both `raw_baseline_6` and `full_engineered_20` used identical hyperparameters.
- **Temporal Stability Note:** Validation (`0.8826`) and held-out Test (`0.8843`) ROC-AUC are closely aligned, which suggests temporal stability across the 2010–2011 timeline, though it does not conclusively rule out subtle distribution shifts or overfitting in all subgroups.

## 2. Anomaly Score Mathematical Semantics
Scikit-learn's `IsolationForest` defines:
$$\text{decision\_function}(X) = \text{score\_samples}(X) - \text{offset\_}$$
where `offset_ = -0.5` when `contamination="auto"`.

Our implementation defines:
$$\text{anomaly\_score}(X) = -\text{decision\_function}(X) = -\text{score\_samples}(X) + \text{offset\_}$$

- **Orientation:** Higher `anomaly_score` = more anomalous.
- **Valid Negative Scores:** Normal/inlier points have `decision_function(X) > 0`, so negative `anomaly_score` values (e.g., median `-0.1497`) are expected and valid.
- **Default Boundary:** `anomaly_score >= 0.0` corresponds exactly to `decision_function(X) <= 0.0` (`predict(X) == -1`).
- **Not a Probability:** Anomaly scores reflect average isolation path length, **not** a calibrated probability of malicious intent.

## 3. Model Persistence (`models/isolation_forest_v1.joblib`)
Only the validation-selected model (`full_engineered_20`) is persisted as a `joblib` bundle containing `model`, `feature_names` (exact 20-feature order), and `metadata` (including validation-calibrated thresholds). All `models/*.joblib` files are excluded from Git.

