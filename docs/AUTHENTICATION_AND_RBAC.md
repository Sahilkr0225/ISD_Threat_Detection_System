# Authentication, Session Management & Role-Based Access Control (Phase 6)

## 1. Overview

Phase 6 introduces server-side session authentication, Argon2id password hashing, CSRF protection, login rate limiting, Role-Based Access Control (RBAC), user management, and immutable security audit logging to the **AI-Based Insider Threat Detection System** without altering the trained Isolation Forest model, the 20 engineered features, calibrated thresholds, anomaly scores, or historical CERT r4.2 operational records.

## 2. Password Hashing & Policy

- **Algorithm:** Argon2id via `argon2-cffi==25.1.0` (`PasswordHasher()`).
- **Policy:** Minimum 12 characters, maximum 128 characters (`validate_password_policy` in `backend/app/core/security.py`).
- **Bootstrap:** No hardcoded default passwords or public self-registration exist. Initial administrator accounts are provisioned interactively via:
  ```powershell
  .\.venv\Scripts\python.exe scripts/bootstrap_admin.py
  ```
  using `getpass` for masked password entry.

## 3. Session Architecture & Cookies

- **Opaque Server-Side Tokens:** On successful `POST /api/v1/auth/login`, a 32-byte URL-safe random token (`secrets.token_urlsafe(32)`) is generated. Only its **SHA-256 hash** (`hash_session_token`) is stored in the `sessions` SQLite table.
- **Session Cookie (`isd_session`):** `HttpOnly=True`, `SameSite=Lax`, `Path=/`, `Secure` configurable via `SESSION_COOKIE_SECURE` (default `false` for local HTTP development), TTL configurable via `SESSION_TTL_HOURS` (default `12`).
- **Revocation:** Logout (`POST /api/v1/auth/logout`), password change (`POST /api/v1/auth/change-password`), admin password reset, role change, and user deactivation immediately revoke active sessions in SQLite.

## 4. CSRF Protection & Origin Validation

- All state-changing authenticated requests (`POST`, `PUT`, `PATCH`, `DELETE`) enforce `require_csrf` (`backend/app/api/deps.py`):
  1. If an `Origin` header is present, it must match `CORS_ORIGINS`.
  2. The `X-CSRF-Token` request header must match the `isd_csrf` cookie via constant-time comparison (`secrets.compare_digest`).
  3. Failures return HTTP `403` and record a `CSRF_REJECTED` entry in `security_audit_logs`.

## 5. Login Rate Limiting

- `LoginRateLimiter` (`backend/app/core/security.py`) enforces a process-local sliding window of `5` failed login attempts per `60` seconds (per client IP + username key), returning HTTP `429` when exceeded.
- *Limitation:* State is held in process memory; multi-worker deployments maintain per-worker counters.

## 6. Roles & Permission Matrix

| Capability / Endpoint Group | `ADMINISTRATOR` | `SECURITY_ANALYST` | `AUDITOR` | Unauthenticated |
| :--- | :---: | :---: | :---: | :---: |
| `GET /api/v1/health`, `GET /api/v1/auth/csrf`, `POST /api/v1/auth/login` | Allowed | Allowed | Allowed | Allowed |
| `GET /api/v1/dashboard/*`, `GET /api/v1/employees*`, `GET /api/v1/anomalies` | Allowed | Allowed | Allowed | `401` |
| `GET /api/v1/alerts*` (list, detail, history) | Allowed | Allowed | Allowed | `401` |
| `PATCH /api/v1/alerts/{alert_id}/status` | Allowed | Allowed | `403` | `401` |
| `GET /api/v1/model/info`, `/model/metrics`, `/data/summary` | Allowed | `403` | Allowed | `401` |
| `POST /api/v1/model/predict` | Allowed | `403` | `403` | `401` |
| `GET /api/v1/audit-logs` | Allowed | `403` | Allowed | `401` |
| `/api/v1/users*` (create, list, update, reset password) | Allowed | `403` | `403` | `401` |

## 7. User Management & Safety Invariants

- Usernames are normalized (`strip().lower()`). Duplicate normalized usernames return HTTP `409`.
- **Last-Active-Admin & Self-Protection:** An administrator cannot deactivate or demote themselves, and the system blocks deactivating or demoting the last active `ADMINISTRATOR` (HTTP `409`).

## 8. Accountability & Audit Logging

- `investigation_history.actor_user_id` records the authenticated user who performed each alert status transition (nullable for legacy pre-Phase-6 rows, displayed in the UI as `"Legacy / Unauthenticated"`).
- `security_audit_logs` records immutable audit events (`LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`, `ACCESS_DENIED`, `CSRF_REJECTED`, `USER_CREATED`, `USER_UPDATED`, `PASSWORD_RESET`, `PASSWORD_CHANGED`, `INVESTIGATION_STATUS_CHANGED`), committed immediately so denied and failed requests are always persisted.

