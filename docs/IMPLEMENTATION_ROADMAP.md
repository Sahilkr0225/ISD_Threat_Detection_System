# Implementation Roadmap

## Phase 1 — Repository Initialization, Audit, EDA, Cleaning & Feature Engineering (Complete)
- Monorepo setup, Python 3.10 environment, independent audit of both Parquet datasets, validation & cleaning pipeline, causal feature engineering (20 approved features with `14obs` window and `epsilon=1.0`), chronological splitting, 3 executed EDA notebooks, 5 EDA figures, and 15 Pytest tests.

## Phase 2 — Unsupervised Anomaly Detection (Isolation Forest) (Complete)
- Trained unscaled `IsolationForest` strictly on `data/processed/train.parquet` (`208,167` rows, zero labels).
- Completed 6-feature raw baseline vs. 20-feature causal engineered ablation on `validation.parquet` (`full_engineered_20` won: Val ROC-AUC `0.8826`, PR-AUC `0.0177`).
- Evaluated once on held-out `test.parquet` (Test ROC-AUC `0.8843`, PR-AUC `0.0105`).
- Persisted `models/isolation_forest_v1.joblib` and added Phase 2 unit tests.

## Phase 3 — Risk Scoring, Explainability, Alerting & FastAPI Backend
- Implement `0–100` normalized risk scoring (`backend/app/risk/`) and per-feature deviation explanations (`backend/app/explainability/`).
- Implement SQLite persistence (`backend/app/database/`) and FastAPI routes (`backend/app/api/routes/`).

## Phase 4 — React Security Monitoring Dashboard & Final Integration
- Build React + Vite + TypeScript + Tailwind CSS + Recharts dashboard (`frontend/`) on `feature/frontend` and integrate end-to-end.
