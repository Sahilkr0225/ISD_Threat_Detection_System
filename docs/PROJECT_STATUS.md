# Project Status

**Title:** AI-Based Insider Threat Detection System Using Unsupervised Anomaly Detection  
**Current Phase:** Phase 5.1 Complete (Administrator Experience & Actionable Explainability Ready for Submission)  
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

## Known Blockers / Limitations
- None for Phase 3. Ground-truth labels are stored separately from `APPROVED_MODEL_FEATURES` and used strictly for offline evaluation.

## Implemented (Phase 3)
- [x] `ModelPredictor` singleton inference service (`backend/app/ml/predictor.py`)
- [x] Validation-reference `RiskScorer` and `PriorityClassifier` (`backend/app/risk/scoring.py`, `models/validation_score_reference.npy`)
- [x] Causal behavioural explainability engine (`backend/app/explainability/explainer.py`)
- [x] SQLite schema, parameterized repository, and idempotent test-partition importer (`backend/app/database/`, `scripts/init_and_import_db.py`)
- [x] FastAPI `/api/v1` REST API (`15` endpoints, Pydantic v2 schemas, localhost CORS)
- [x] Phase 3 unit, integration, and live HTTP smoke tests (`29` total Pytest tests passing)

## Implemented (Phase 4)
- [x] React + Vite + TypeScript + Tailwind CSS v4 SOC dashboard (`frontend/`)
- [x] Centralized typed Axios API layer (`frontend/src/api/`) connected to FastAPI `/api/v1`
- [x] All 6 core pages + detail views (`Overview`, `Employees`, `EmployeeDetail`, `AlertCenter`, `AlertDetail`, `Investigations`, `ModelEvaluation`, `DatasetSystem`)
- [x] End-to-end investigation workflow (`OPEN -> UNDER_REVIEW -> RESOLVED/DISMISSED`) with confirmation dialogs and toast feedback
- [x] Strict `tsc -b` + `vite build` verification and live browser integration testing

## Implemented (Phase 5.1)
- [x] Direction-aware deterministic explainability (`backend/app/explainability/explainer.py`) & safe idempotent DB refresh (`30,813` rows, backup preserved, Alert `#1184` history preserved)
- [x] Backward-compatible API enhancements (`critical_open_alerts`, `highest_priority`, `activity_summary`)
- [x] Administrator-focused UI: grouped sidebar (`Security Operations` / `Advanced & Technical`), plain-language Alert Detail (`A–F` sections with collapsed technical details), accessible priority/percentile tooltips, and separate ROC-AUC/AP ablation charts

## Future Enhancements (Post-Submission)
- [ ] Authentication, Role-Based Access Control (RBAC), and authenticated analyst identities
- [ ] Real-time event streaming / dataset replay

