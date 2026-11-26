# Feature Engineering Documentation

**Implementation:** `backend/app/features/feature_engineering.py`  
**Total Approved Model Features:** 20 (6 canonical observable counts + 14 engineered features)

## 1. Engineered Features & Formulas

| Feature | Formula / Definition | Safeguard |
| :--- | :--- | :--- |
| `total_activity_count` | `login_count + http_activity_count + email_activity_count + file_activity_count + usb_activity_count` | Exact integer sum |
| `after_hours_ratio` | `after_hours_login_count / max(login_count, 1)` | Returns `0.0` when `login_count == 0` |
| `is_weekend` | `1` if `activity_date.dayofweek >= 5` else `0` | Binary indicator |
| `log_http_activity` | `log1p(http_activity_count)` | Handles zero counts cleanly |
| `log_email_activity` | `log1p(email_activity_count)` | Handles zero counts cleanly |
| `log_file_activity` | `log1p(file_activity_count)` | Handles zero counts cleanly |
| `log_usb_activity` | `log1p(usb_activity_count)` | Handles zero counts cleanly |
| `*_hist_dev_14obs` (7 features) | `(x_t - mean(x_{t-14..t-1})) / max(std(x_{t-14..t-1}), 1.0)` | `shift(1)` excludes current row; `min_periods=3` (< 3 prior obs -> `0.0`); `epsilon=1.0` prevents artificial 1,000x amplification on zero-variance windows |

The 7 causal rolling deviation features (`*_hist_dev_14obs`) are computed per `employee_id` sorted by `activity_date` over the preceding **14 active employee observations** (not 14 calendar days, as weekends/holidays may have no activity) for: `login_count`, `after_hours_login_count`, `http_activity_count`, `email_activity_count`, `file_activity_count`, `usb_activity_count`, and `total_activity_count`.

## 2. Feature Redundancy & Phase 2 Ablation Configurations
On `train.parquet`, several pairs exhibit high Pearson correlation (`|r| >= 0.80`), such as `http_activity_count` vs `total_activity_count` (`0.9914`), `http_activity_count` vs `email_activity_count` (`0.9739`), and raw counts vs `log1p` transforms (`0.9153–0.9469`). Valid features are retained rather than blindly pruned, and Phase 2 will compare:
1. **Raw-Feature Baseline (6 features):** `login_count`, `after_hours_login_count`, `http_activity_count`, `email_activity_count`, `file_activity_count`, `usb_activity_count`.
2. **Full Engineered Configuration (20 features):** All 6 raw counts + 14 engineered features.

## 3. Excluded Features & Justification
- **`employee_id`, `activity_date`:** Identifiers/timestamps — excluded so Isolation Forest learns generalizable behavioural patterns rather than memorizing users or dates.
- **`role`, `department`, `functional_unit`:** Organisational metadata with 9.5%–10.9% missingness — reserved for analyst context.
- **`O`, `C`, `E`, `A`, `N`, `avg_sentiment`:** Psychometric Big-5 traits and email sentiment — excluded to focus on observable security-related behavioural activity.
