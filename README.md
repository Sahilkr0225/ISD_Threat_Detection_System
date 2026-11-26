# ISD_Threat_Detection_System

**AI-Based Insider Threat Detection System Using Unsupervised Anomaly Detection**

> **Academic & Cybersecurity Disclaimer:** An anomaly detected by an unsupervised model (Isolation Forest) indicates statistical behavioural deviation—it must **never** be presented as definitive evidence of malicious intent. All alerts require human analyst investigation.

## Finalized Technology Stack
- **Frontend (Planned):** React + Vite + TypeScript, Tailwind CSS, Lucide React, Recharts, Axios
- **Backend:** FastAPI, Python 3.10, Scikit-learn (Isolation Forest), Pandas, NumPy, PyArrow, Joblib, SQLite, Pytest
- **Research & EDA:** Jupyter Notebook, Matplotlib, Seaborn

## Current Implementation Status (Phase 3 Complete)
- **Implemented:** Monorepo structure, Python 3.10 `.venv`, dataset audit & CERT r4.2 ground-truth mapping, data validation & cleaning (`backend/app/data/`), causal feature engineering (`backend/app/features/`), unscaled `IsolationForest` (`backend/app/ml/`), validation-reference risk scoring & priority classification (`backend/app/risk/`), causal explainability (`backend/app/explainability/`), SQLite persistence (`backend/app/database/`), `15` FastAPI `/api/v1` endpoints (`backend/app/api/routes/`), and `29` passing Pytest tests.
- **Planned (Phase 4):** React + Vite + TypeScript + Tailwind CSS + Recharts security dashboard (`frontend/`).

## Run Backend API (Local Demonstration)

```powershell
.\.venv\Scripts\python.exe scripts\init_and_import_db.py
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`

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
