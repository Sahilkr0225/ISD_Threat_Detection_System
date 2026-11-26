# Data Cleaning Report

**Source File:** `data/raw/master_behavioral_matrix.parquet` (read-only; never modified)  
**Implementation:** `backend/app/data/validator.py`, `backend/app/data/preprocessing.py`

## Summary Metrics (`reports/metrics/cleaning_summary.json`)
- **Original Row Count:** 330,452
- **Cleaned Row Count:** 330,452 (0 rows dropped)
- **Duplicate Rows / Employee-Date Pairs:** 0 / 0
- **Infinite / Invalid Numeric Values:** 0 / 0
- **Missing Values Handled:**
  - `role`: 31,281 missing -> filled with `"Unknown"` (metadata only, excluded from ML)
  - `department`: 36,125 missing -> filled with `"Unknown"` (metadata only, excluded from ML)
  - `functional_unit`: 31,973 missing -> filled with `"Unknown"` (metadata only, excluded from ML)
  - All 6 observable numeric activity columns had **0** missing values and **0** negative values.

## Cleaning Methodology & Justification
1. **No Outlier Removal:** Extreme upper-tail activity counts (e.g., `http_activity_count` max `400`, `file_activity_count` max `54`, `usb_activity_count` max `28`) are preserved because extreme deviations are primary candidates for insider threat anomalies.
2. **Exact-Integer Casting:** `http_activity_count`, `total_emails`, `file_activity_count`, and `usb_activity_count` were stored as `float64` in the raw Parquet file despite containing exact integer counts; casting to `int64` reduces memory footprint without information loss.
3. **Identifier & Date Preservation:** `employee_id` and `activity_date` are preserved for chronological sorting, causal grouping, and future analyst investigation, while excluded from model input features.
4. **Remaining Issue:** Ground-truth insider threat labels are absent from the source Parquet files.

