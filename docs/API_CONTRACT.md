# Backend API Contract (`/api/v1`)

**Base URL (Local Development):** `http://127.0.0.1:8000/api/v1`  
**CORS Allowed Origin (Default):** `http://localhost:5173`  
**Interactive OpenAPI Docs:** `http://127.0.0.1:8000/docs`  
*(Security Note: Localhost demonstration backend prior to authentication/RBAC; not for public deployment.)*

## Pagination & Error Format
- **Pagination:** `{ "page": int, "page_size": int, "total": int, "total_pages": int }`
- **Errors:** `{"detail": "<message>"}` with HTTP `404` (missing resource), `422` (validation / invalid status transition), or `500` (safe generic error).

## Endpoints

| Method | Path | Query / Body | Response Summary | Codes |
| :--- | :--- | :--- | :--- | :---: |
| `GET` | `/health` | — | `{status, phase, model_loaded, database_ready}` | `200` |
| `GET` | `/dashboard/summary` | — | Unique employees (`877`), total obs (`61473`), flagged (`10271`), status & priority counts, top 10 employees, recent investigations, coverage dates | `200` |
| `GET` | `/dashboard/trends` | `date_from`, `date_to` (`YYYY-MM-DD`) | `{items: [{activity_date, total_observations, flagged_count, high_critical_count, avg_risk_score}]}` | `200`, `422` |
| `GET` | `/employees` | `department`, `search`, `page`, `page_size` | `{items: [EmployeeSummary], pagination}` | `200` |
| `GET` | `/employees/{employee_id}` | — | `EmployeeDetailResponse` (`avg_risk_score`, `max_risk_score`, `alert_count`, `open_alert_count`) | `200`, `404` |
| `GET` | `/employees/{employee_id}/history` | `page`, `page_size` | `{employee_id, items: [EmployeeObservationItem], pagination}` | `200`, `404` |
| `GET` | `/anomalies` | `priority`, `employee_id`, `date_from`, `date_to`, `page`, `page_size` | `{items: [AnomalyItem], pagination}` | `200` |
| `GET` | `/alerts` | `priority`, `status`, `employee_id`, `date_from`, `date_to`, `sort_by` (`anomaly_score`\|`activity_date`), `sort_order` (`asc`\|`desc`), `page`, `page_size` | `{items: [AlertSummaryItem], pagination}` | `200` |
| `GET` | `/alerts/{alert_id}` | — | `AlertDetailResponse` including observation counts and `explanations` list | `200`, `404` |
| `PATCH` | `/alerts/{alert_id}/status` | `{new_status: OPEN\|UNDER_REVIEW\|RESOLVED\|DISMISSED, analyst_note?: str}` | Updated `AlertDetailResponse` | `200`, `404`, `422` |
| `GET` | `/alerts/{alert_id}/history` | — | `{alert_id, items: [InvestigationHistoryItem]}` | `200`, `404` |
| `GET` | `/model/info` | — | Model version, algorithm, `feature_count` (`20`), `feature_names`, `hyperparameters`, `calibrated_thresholds`, `disclaimer` | `200` |
| `GET` | `/model/metrics` | — | Offline Phase 2 validation ablation, held-out test ROC-AUC/AP/PR-AUC, and exact threshold confusion matrices | `200`, `404` |
| `POST` | `/model/predict` | `{observations: [FeatureVectorInput]}` (20 approved features, 1–500 items) | `{model_version, disclaimer, predictions: [{anomaly_score, risk_score, priority, estimator_default_is_anomaly, is_flagged_for_review}]}` | `200`, `422` |
| `GET` | `/data/summary` | — | Imported dataset coverage (`source_partition`, `unique_employees`, `observation_count`, `alert_count`, `note`) | `200` |

