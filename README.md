# ISD_Threat_Detection_System

**AI-Based Insider Threat Detection System Using Unsupervised Anomaly Detection**

> **Academic & Cybersecurity Disclaimer:** An anomaly detected by an unsupervised model (Isolation Forest) indicates statistical behavioural deviation—it must **never** be presented as definitive evidence of malicious intent. All alerts require human analyst investigation.

## Finalized Technology Stack
- **Frontend (Planned):** React + Vite + TypeScript, Tailwind CSS, Lucide React, Recharts, Axios
- **Backend:** FastAPI, Python 3.10, Scikit-learn (Isolation Forest), Pandas, NumPy, PyArrow, Joblib, SQLite, Pytest
- **Research & EDA:** Jupyter Notebook, Matplotlib, Seaborn

## Current Implementation Status (Phase 2 Complete)
- **Implemented:** Monorepo structure, Python 3.10 `.venv`, dataset audit & CERT r4.2 ground-truth mapping, data validation & cleaning (`backend/app/data/`), causal feature engineering (`backend/app/features/`), unscaled `IsolationForest` training/ablation/evaluation & Joblib persistence (`backend/app/ml/`, `models/`), 3 EDA notebooks, 7 figures, and automated Pytest suite (`backend/tests/`).
- **Planned (Phases 3–4):** Normalized risk scoring (`0–100`), behavioural explainability, SQLite alert persistence, FastAPI routes, and React security dashboard.

## Reproduction Instructions (Windows PowerShell)

```powershell
# 1. Create and activate Python 3.10 environment
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# 2. Audit raw Parquet datasets (requires files in data/raw/)
.\.venv\Scripts\python.exe scripts\audit_datasets.py

# 3. Run cleaning, causal feature engineering, and chronological splitting
.\.venv\Scripts\python.exe scripts\prepare_phase1_artifacts.py

# 4. Generate EDA figures
.\.venv\Scripts\python.exe scripts\generate_eda_figures.py

# 5. Run automated tests and dependency check
.\.venv\Scripts\python.exe -m pytest backend\tests -v
.\.venv\Scripts\python.exe -m pip check
```

## Documentation Index
- [Project Status](docs/PROJECT_STATUS.md)
- [Architecture & Preliminary API Contract](docs/ARCHITECTURE.md)
- [Dataset Documentation](docs/DATASET_DOCUMENTATION.md)
- [Data Cleaning Report](docs/DATA_CLEANING_REPORT.md)
- [Feature Engineering](docs/FEATURE_ENGINEERING.md)
- [Data Leakage Audit](docs/DATA_LEAKAGE_AUDIT.md)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
