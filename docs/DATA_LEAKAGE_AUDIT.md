# Data Leakage Audit & Chronological Splitting

## 1. Audit of `feature_matrix_v1.parquet` (Conclusive Leakage Proof)
Independent numerical comparison (`scripts/verify_phase1_maintenance.py`) between `feature_matrix_v1.parquet` and full-timeline per-user sample standardization (`ddof=1`) across all `330,452` rows and `501` days confirmed:
- `total_logon_activity_z_user`: `max_abs_diff = 0.0`, `corr = 1.0`
- `http_activity_count_z_user`: `max_abs_diff = 0.0`, `corr = 1.0`
- `total_emails_z_user`: `max_abs_diff = 0.0`, `corr = 1.0`
- `file_activity_count_z_user`: `max_abs_diff = 0.0`, `corr = 1.0`
- `usb_activity_count_z_user`: `max_abs_diff = 0.0`, `corr = 1.0`

This conclusively proves `*_z_user` in `feature_matrix_v1.parquet` was computed using **full-timeline per-user statistics** (including future observations). Therefore, `feature_matrix_v1.parquet` is strictly excluded from model training.

## 2. Leakage Mitigations in Phase 1 Pipeline
1. **Strict Causal Baselines:** All `*_hist_dev_14obs` features use `series.shift(1)` before `.rolling(window=14, min_periods=3)`, guaranteeing the current and future observations never enter the historical baseline (verified by `test_no_future_leakage_in_causal_rolling_features`).
2. **No Global Scaling/Imputation:** No global `StandardScaler` or global mean/median imputation is applied in Phase 1.
3. **Identifier & Psychometric Exclusion:** `employee_id`, `activity_date`, `O/C/E/A/N`, `avg_sentiment`, and `role/department/functional_unit` are excluded from `APPROVED_MODEL_FEATURES`.

## 3. Chronological Partitioning (`reports/metrics/split_manifest.json`)
Split strictly by unique sorted dates (`60%` / `20%` / `20%`):

| Partition | Date Range | Unique Dates | Rows | Unique Employees |
| :--- | :--- | :---: | :---: | :---: |
| `train.parquet` | `2010-01-02` to `2010-10-28` | 300 | 208,167 | 1,000 |
| `validation.parquet` | `2010-10-29` to `2011-02-05` | 100 | 60,812 | 922 |
| `test.parquet` | `2011-02-06` to `2011-05-17` | 101 | 61,473 | 877 |
