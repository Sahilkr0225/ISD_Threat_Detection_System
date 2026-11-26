# Project Status

**Title:** AI-Based Insider Threat Detection System Using Unsupervised Anomaly Detection  
**Current Phase:** Phase 6 Complete (Authentication, Session Management & RBAC)  
**Target Submission:** 27 November 2026

## Implemented (Phase 1)
- [x] Repository & Git branch audit (`feature/backend-ml`)
- [x] Monorepo directory structure (`backend/`, `frontend/`, `data/`, `notebooks/`, `models/`, `scripts/`, `reports/`, `docs/`)
- [x] Python 3.10 `.venv` and `backend/requirements.txt` (`pip check`: 0 broken requirements)
- [x] Independent audit of `master_behavioral_matrix.parquet` and `feature_matrix_v1.parquet`
- [x] Data loader, validator, and cleaning/chronological splitting (`backend/app/data/`)
- [x] Causal behavioural feature engineering (`backend/app/features/feature_engineering.py`)
- [x] Processed Parquet artifacts & manifests (`data/processed/`, `reports/metrics/`)
- [x] Reproducible Jupyter notebooks (`notebooks/01–03`) and 5 EDA figures (`reports/figures/`)
- [x] Automated Pytest suite (`backend/tests/`: 15 passed)
- [x] Official CERT r4.2 ground-truth label mapping (`answers.tar.bz2` -> `data/processed/ground_truth_labels.parquet`, 966 matched malicious employee-days, 0 unmatched)

## Implemented (Phase 2)
- [x] Unscaled `IsolationForest` training, scoring, and Joblib persistence (`backend/app/ml/isolation_forest.py`)
- [x] Offline evaluation & validation-only threshold calibration (`backend/app/ml/evaluation.py`)
- [x] 6-feature vs. 20-feature ablation & held-out test evaluation (`scripts/train_phase2_models.py`, `models/isolation_forest_v1.joblib`)
- [x] Phase 2 evaluation figures (`06_phase2_pr_roc_curves.png`, `07_phase2_test_score_distribution.png`) and report (`docs/MODEL_EVALUATION.md`)
- [x] Phase 2 unit tests (`backend/tests/test_isolation_forest.py`)

## Implemented (Phase 3)
- [x] `ModelPredictor` singleton inference service (`backend/app/ml/predictor.py`)
- [x] Validation-reference `RiskScorer` and `PriorityClassifier` (`backend/app/risk/scoring.py`, `models/validation_score_reference.npy`)
- [x] Causal behavioural explainability engine (`backend/app/explainability/explainer.py`)
- [x] SQLite schema, parameterized repository, and idempotent test-partition importer (`backend/app/database/`, `scripts/init_and_import_db.py`)
- [x] FastAPI `/api/v1` REST API (Pydantic v2 schemas, localhost CORS)

## Implemented (Phase 4 & 5.1)
- [x] React + Vite + TypeScript + Tailwind CSS v4 SOC dashboard (`frontend/`)
- [x] Direction-aware deterministic explainability (`backend/app/explainability/explainer.py`) & safe idempotent DB refresh (`30,813` rows, backup preserved, Alert `#1184` history preserved)
- [x] Administrator-focused UI: grouped sidebar (`Security Operations` / `Advanced & Technical`), plain-language Alert Detail (`A–F` sections with collapsed technical details), accessible priority/percentile tooltips, and separate ROC-AUC/AP ablation charts

## Implemented (Phase 6)
- [x] Argon2id password hashing (`argon2-cffi==25.1.0`), 12–128 char policy, and interactive CLI admin bootstrap (`scripts/bootstrap_admin.py`)
- [x] Server-side opaque sessions (`isd_session` `HttpOnly` cookie, SHA-256 hashed in SQLite `sessions`), CSRF double-submit + `Origin` protection, and process-local login rate limiting (`5` failures / `60s`)
- [x] Backend-enforced RBAC across `ADMINISTRATOR`, `SECURITY_ANALYST`, and `AUDITOR`
- [x] Additive idempotent DB migration (`users`, `sessions`, `security_audit_logs`, `investigation_history.actor_user_id`) preserving all `877` employees, `61,473` observations, `10,271` alerts, `30,813` explanations, and `6` pre-Phase-6 investigation history rows
- [x] React authentication & governance UI (`Login`, `AccessDenied`, `UserManagement`, `AuditLogs`, `ProtectedRoute`, `AuthContext`, role-filtered `AppShell`, `AUDITOR` read-only `AlertDetail`, actor attribution)
- [x] `38` passing backend Pytest tests, clean `tsc -b && vite build`, and live authenticated HTTP smoke test (`reports/metrics/phase6_smoke_results.json`)

## Future Enhancements (Post-Submission)
- [ ] Real-time event streaming / SIEM integration
