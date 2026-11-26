# Implementation Roadmap

## Phase 1 — Repository Initialization, Audit, EDA, Cleaning & Feature Engineering (Complete)
- Monorepo setup, Python 3.10 environment, independent audit of both Parquet datasets, validation & cleaning pipeline, causal feature engineering (20 approved features with `14obs` window and `epsilon=1.0`), chronological splitting, 3 executed EDA notebooks, 5 EDA figures, and 15 Pytest tests.

## Phase 2 — Unsupervised Anomaly Detection (Isolation Forest) (Complete)
- Trained unscaled `IsolationForest` strictly on `data/processed/train.parquet` (`208,167` rows, zero labels).
- Completed 6-feature raw baseline vs. 20-feature causal engineered ablation on `validation.parquet` (`full_engineered_20` won: Val ROC-AUC `0.8826`, PR-AUC `0.0177`).
- Evaluated once on held-out `test.parquet` (Test ROC-AUC `0.8843`, PR-AUC `0.0105`).
- Persisted `models/isolation_forest_v1.joblib` and added Phase 2 unit tests.

## Phase 3 — Risk Scoring, Explainability, Alerting & FastAPI Backend (Complete)
- Implemented `ModelPredictor`, validation-reference `RiskScorer`, `PriorityClassifier`, and causal `BehaviouralExplainer`.
- Implemented SQLite persistence (`data/app/insider_threat.db`) and imported `61,473` held-out test observations (`877` employees, `10,271` alerts, `30,813` explanations).
- Implemented FastAPI `/api/v1` endpoints with Pydantic schemas and verified with Pytest and live HTTP smoke tests.

## Phase 4 — React Security Monitoring Dashboard & Final Integration (Complete)
- Built React + Vite + TypeScript + Tailwind CSS v4 + Recharts SOC dashboard (`frontend/`).
- Integrated all FastAPI `/api/v1` endpoints with server-side pagination, causal explainability cards, interactive investigation status transitions, and Phase 2 model evaluation explorer.

## Phase 5.1 — Administrator Experience & Actionable Explainability (Complete)
- Added direction-aware plain-language explanations and safely refreshed `30,813` persisted `alert_explanations` rows (preserving all `10,271` alerts and Alert `#1184` investigation history).
- Reorganized sidebar navigation (`Security Operations` vs. `Advanced & Technical`), added accessible priority/percentile tooltips, collapsed raw technical metrics into an expandable section on Alert Detail, and separated ROC-AUC / Average Precision ablation charts.

## Phase 6 — Authentication, Session Management & Role-Based Access Control (Complete)
- Added Argon2id password hashing, opaque SHA-256 server-side sessions (`HttpOnly` cookie), CSRF + `Origin` protection, login rate limiting, interactive admin bootstrap (`scripts/bootstrap_admin.py`), and additive SQLite migrations (`users`, `sessions`, `security_audit_logs`, `investigation_history.actor_user_id`).
- Enforced RBAC across `ADMINISTRATOR`, `SECURITY_ANALYST`, and `AUDITOR`, added User Management & Audit Logs UI, read-only Auditor enforcement, and verified with `38` Pytest tests, `npm run build`, and live authenticated HTTP smoke tests.
