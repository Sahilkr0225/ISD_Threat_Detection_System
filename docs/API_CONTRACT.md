# Backend API Contract (`/api/v1`)

**Base URL (Local Development):** `http://127.0.0.1:8000/api/v1` (proxied via Vite `/api` at `http://localhost:5173`)  
**CORS Allowed Origin (Default):** `http://localhost:5173` (`allow_credentials=True`, `allow_headers=["Content-Type", "X-CSRF-Token"]`)  
**Interactive OpenAPI Docs:** `http://127.0.0.1:8000/docs` (enabled when `APP_ENV=development`)

## Authentication, CSRF & RBAC
- **Session Cookie (`isd_session`):** Server-side opaque token (`HttpOnly`, `SameSite=Lax`, SHA-256 hashed in SQLite `sessions`).
- **CSRF Protection:** State-changing authenticated requests (`POST`, `PUT`, `PATCH`, `DELETE`) require `X-CSRF-Token` matching the `isd_csrf` cookie plus trusted `Origin` validation.
- **Roles:** `ADMINISTRATOR`, `SECURITY_ANALYST`, `AUDITOR` (monitored CERT r4.2 employees are dataset subjects, not login users).
- **Pagination:** `{ "page": int, "page_size": int, "total": int, "total_pages": int }`
- **Errors:** `{"detail": "<message>"}` with HTTP `401` (unauthenticated), `403` (RBAC / CSRF failure), `404` (missing resource), `409` (duplicate username / last-admin protection), `422` (validation / invalid transition), `429` (login rate limit), or `500` (safe generic error).

## Endpoints

| Method | Path | Allowed Roles | Summary | Codes |
| :--- | :--- | :--- | :--- | :---: |
| `GET` | `/health` | Public | `{status: "ok", phase: "6"}` | `200` |
| `GET` | `/auth/csrf` | Public | Issues `isd_csrf` cookie and returns `{csrf_token}` | `200` |
| `POST` | `/auth/login` | Public | `{username, password}` -> sets `isd_session` + `isd_csrf` cookies, returns `{user, csrf_token, expires_at}` | `200`, `401`, `429` |
| `POST` | `/auth/logout` | Authenticated (CSRF) | Revokes current session and clears cookies | `200`, `401`, `403` |
| `GET` | `/auth/me` | Authenticated | `{user: UserPublic, session_expires_at}` | `200`, `401` |
| `POST` | `/auth/change-password` | Authenticated (CSRF) | `{current_password, new_password}` -> updates Argon2id hash, revokes other sessions | `200`, `400`, `401`, `403` |
| `GET` | `/users` | `ADMINISTRATOR` | Lists users with pagination | `200`, `401`, `403` |
| `POST` | `/users` | `ADMINISTRATOR` (CSRF) | Creates user (`username`, `display_name`, `password`, `role`) | `201`, `401`, `403`, `409`, `422` |
| `GET` | `/users/{user_id}` | `ADMINISTRATOR` | Single user details (`UserPublic`) | `200`, `401`, `403`, `404` |
| `PATCH` | `/users/{user_id}` | `ADMINISTRATOR` (CSRF) | Updates `display_name`, `role`, `is_active` (last-admin & self-protection enforced) | `200`, `401`, `403`, `404`, `409` |
| `POST` | `/users/{user_id}/reset-password` | `ADMINISTRATOR` (CSRF) | Resets user password and revokes active sessions | `200`, `401`, `403`, `404`, `422` |
| `GET` | `/audit-logs` | `ADMINISTRATOR`, `AUDITOR` | Paginated, filterable (`action`, `outcome`, `actor_user_id`) security audit logs | `200`, `401`, `403` |
| `GET` | `/dashboard/summary` | All 3 roles | Unique employees (`877`), total obs (`61473`), flagged (`10271`), status/priority counts, top employees, recent investigations (with actor info) | `200`, `401` |
| `GET` | `/dashboard/trends` | All 3 roles | Daily anomaly trend series (`date_from`, `date_to`) | `200`, `401`, `422` |
| `GET` | `/employees` | All 3 roles | Paginated employee directory (`department`, `search`) | `200`, `401` |
| `GET` | `/employees/{employee_id}` | All 3 roles | `EmployeeDetailResponse` | `200`, `401`, `404` |
| `GET` | `/employees/{employee_id}/history` | All 3 roles | Paginated observation history | `200`, `401`, `404` |
| `GET` | `/anomalies` | All 3 roles | Paginated flagged observations | `200`, `401` |
| `GET` | `/alerts` | All 3 roles | Filtered/sorted paginated alerts | `200`, `401` |
| `GET` | `/alerts/{alert_id}` | All 3 roles | `AlertDetailResponse` with observation counts & `explanations` | `200`, `401`, `404` |
| `PATCH` | `/alerts/{alert_id}/status` | `ADMINISTRATOR`, `SECURITY_ANALYST` (CSRF) | Transitions status (`OPEN`\|`UNDER_REVIEW`\|`RESOLVED`\|`DISMISSED`), records `actor_user_id` & audit log | `200`, `401`, `403`, `404`, `422` |
| `GET` | `/alerts/{alert_id}/history` | All 3 roles | `{alert_id, items: [InvestigationHistoryItem]}` (includes `actor_username`, `actor_display_name`) | `200`, `401`, `404` |
| `GET` | `/model/info` | `ADMINISTRATOR`, `AUDITOR` | Model version, algorithm, `feature_count` (`20`), hyperparameters, calibrated thresholds, disclaimer | `200`, `401`, `403` |
| `GET` | `/model/metrics` | `ADMINISTRATOR`, `AUDITOR` | Offline Phase 2 validation ablation, held-out test ROC-AUC/AP/PR-AUC, threshold confusion matrices | `200`, `401`, `403`, `404` |
| `POST` | `/model/predict` | `ADMINISTRATOR` (CSRF) | `{observations: [FeatureVectorInput]}` (1–500 items) -> scores, percentiles, priorities | `200`, `401`, `403`, `422` |
| `GET` | `/data/summary` | `ADMINISTRATOR`, `AUDITOR` | Imported dataset coverage & counts | `200`, `401`, `403` |
