# SQLite Database Schema

**Database File:** `data/app/insider_threat.db` *(excluded from Git)*  
**Implementation:** `backend/app/database/schema.py`, `backend/app/database/repository.py`, `backend/app/database/auth_repository.py`  
**Foreign-Key Enforcement:** `PRAGMA foreign_keys = ON` on every connection.

## Operational & Explainability Tables

1. **`employees`**
   - `employee_id` (`TEXT PRIMARY KEY`), `role`, `department`, `functional_unit`, `first_activity_date`, `last_activity_date`.
2. **`employee_observations`**
   - `observation_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `employee_id` (`FK -> employees`), `activity_date`, 6 observable counts + `total_activity_count`, `after_hours_ratio`, `is_weekend`, `model_version`, `anomaly_score`, `risk_score`, `priority`, `created_at`.
   - `UNIQUE (employee_id, activity_date, model_version)`.
3. **`alerts`**
   - `alert_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `observation_id` (`FK -> employee_observations`, `UNIQUE` for idempotent alert creation), `employee_id` (`FK -> employees`), `anomaly_score`, `risk_score`, `priority`, `status` (`OPEN`, `UNDER_REVIEW`, `RESOLVED`, `DISMISSED`), `model_version`, `created_at`, `updated_at`.
4. **`alert_explanations`**
   - `explanation_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `alert_id` (`FK -> alerts`), `feature_name`, `activity_label`, `current_value`, `historical_mean`, `historical_std`, `deviation`, `direction`, `historical_obs_count`, `evidence_description`, `investigation_recommendation`.
   - `UNIQUE (alert_id, feature_name)`.
5. **`investigation_history`**
   - `history_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `alert_id` (`FK -> alerts`), `previous_status`, `new_status`, `analyst_note`, `changed_at`, `actor_user_id` (`INTEGER REFERENCES users(user_id)` — added via additive idempotent migration; `NULL` for pre-Phase-6 legacy records).

## Authentication, Session & Audit Tables (Phase 6)

6. **`users`**
   - `user_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `username` (`TEXT NOT NULL UNIQUE`), `display_name` (`TEXT NOT NULL`), `password_hash` (`TEXT NOT NULL`, Argon2id), `role` (`TEXT NOT NULL CHECK (role IN ('ADMINISTRATOR', 'SECURITY_ANALYST', 'AUDITOR'))`), `is_active` (`INTEGER NOT NULL DEFAULT 1`), `created_at`, `updated_at`, `last_login_at`.
7. **`sessions`**
   - `session_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `user_id` (`INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE`), `token_hash` (`TEXT NOT NULL UNIQUE`, SHA-256), `created_at`, `expires_at`, `revoked_at`, `user_agent`, `ip_address`.
8. **`security_audit_logs`**
   - `audit_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `actor_user_id` (`INTEGER REFERENCES users(user_id)`), `action` (`TEXT NOT NULL`), `resource_type` (`TEXT NOT NULL`), `resource_id`, `outcome` (`TEXT NOT NULL`), `timestamp` (`TEXT NOT NULL`), `details`.

## Historical Demonstration Scope
Imported from `data/processed/test.parquet` (`61,473` observations, `877` unique employees, `10,271` alerts, `30,813` explanations, `2011-02-06` to `2011-05-17`), preserving historical `activity_date` values separately from `created_at` ingestion timestamps.
