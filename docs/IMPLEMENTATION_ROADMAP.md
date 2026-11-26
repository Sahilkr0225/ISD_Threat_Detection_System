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
- Implemented `15` FastAPI `/api/v1` endpoints with Pydantic schemas and verified with `29` Pytest tests and live HTTP smoke tests.

## Phase 4 — React Security Monitoring Dashboard & Final Integration
- Build React + Vite + TypeScript + Tailwind CSS + Recharts dashboard (`frontend/`) on `feature/frontend` and integrate end-to-end.
