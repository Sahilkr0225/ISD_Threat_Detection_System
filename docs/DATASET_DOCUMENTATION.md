# Dataset Documentation

## 1. Provenance & Attribution
- **Original Source:** CERT Insider Threat Dataset r4.2 ([DOI: 10.1184/R1/12841247.v1](https://doi.org/10.1184/R1/12841247.v1)) — contains **simulated** organisational activities, not real confidential employee records.
- **Selected Derivative:** Third-party preprocessed Parquet derivative ([Zenodo Record 19435851](https://zenodo.org/records/19435851)), **not** an official CMU-preprocessed release.
- **Synthetic Data Limitation:** Simulated CERT behaviour does not guarantee real-world enterprise generalization.

## 2. Dataset Comparison

| Metric | `master_behavioral_matrix.parquet` (Primary) | `feature_matrix_v1.parquet` (Reference Only) |
| :--- | :--- | :--- |
| File Size (Disk) | 2.761 MB | 9.135 MB |
| Memory Usage (RAM) | 127.747 MB | 156.741 MB |
| Rows / Columns | 330,452 / 17 | 330,452 / 33 |
| Unique Employees (`user`) | 1,000 | 1,000 |
| Date Range (`day`) | `2010-01-02` to `2011-05-17` (501 unique dates) | `2010-01-02` to `2011-05-17` (501 unique dates) |
| Duplicates (rows / user-day) | 0 / 0 | 0 / 0 |
| Infinite Values | 0 | 0 |
| Ground-Truth Labels | **None** | **None** |
| Selection Decision | **Selected as primary dataset** | **Excluded from training** (proven full-timeline `*_z_user` leakage) |

## 3. Canonical Column Mapping

| Original Column (`master_behavioral_matrix.parquet`) | Canonical Name | Type | Category |
| :--- | :--- | :--- | :--- |
| `user` | `employee_id` | string | Identifier (excluded from ML) |
| `day` | `activity_date` | datetime64 | Date (excluded from ML) |
| `total_logon_activity` | `login_count` | int64 | Observable behavioural |
| `after_hours_activity` | `after_hours_login_count` | int64 | Observable behavioural |
| `http_activity_count` | `http_activity_count` | int64 | Observable behavioural |
| `total_emails` | `email_activity_count` | int64 | Observable behavioural |
| `file_activity_count` | `file_activity_count` | int64 | Observable behavioural |
| `usb_activity_count` | `usb_activity_count` | int64 | Observable behavioural |
| `role`, `department`, `functional_unit` | preserved as metadata | string | Context only (excluded from ML) |
| `avg_sentiment`, `O`, `C`, `E`, `A`, `N` | **excluded** | — | Psychometric/sentiment (excluded) |

## 4. Ground-Truth Availability & CERT r4.2 Acquisition Strategy
Neither Parquet file includes insider threat labels. Official CERT r4.2 ground-truth annotations are distributed separately on CMU KiltHub/Figshare ([DOI: 10.1184/R1/12841247.v1](https://doi.org/10.1184/R1/12841247.v1)) in `answers.tar.bz2`, which contains:
- `insiders.csv`: Lists malicious `user` IDs, `scenario` (1, 2, or 3), `start`/`end` timestamps, and `details`.
- Scenario event files (`r4.2-1.csv`, `r4.2-2.csv`, `r4.2-3.csv`): Individual malicious event rows with `user` IDs and exact event timestamps.

**Mapping Strategy (when `answers.tar.bz2` is downloaded manually to `data/raw/`):**
1. Parse `r4.2-*.csv` event timestamps into `(employee_id, activity_date)` pairs—never label all days of a malicious user as positive.
2. Left-join onto the canonical index `(employee_id, activity_date)` **outside** `APPROVED_MODEL_FEATURES` for validation/test evaluation only, reporting any unmatched user IDs or dates.
