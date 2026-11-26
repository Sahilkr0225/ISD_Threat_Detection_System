# ISD_Threat_Detection_System

**AI-Based Insider Threat Detection System Using Unsupervised Anomaly Detection**

> **Academic & Cybersecurity Disclaimer:** An anomaly detected by an unsupervised model (Isolation Forest) indicates statistical behavioural deviation—it must **never** be presented as definitive evidence of malicious intent. All alerts require human analyst investigation.

## Finalized Technology Stack
- **Frontend (Planned):** React + Vite + TypeScript, Tailwind CSS, Lucide React, Recharts, Axios
- **Backend:** FastAPI, Python 3.10, Scikit-learn (Isolation Forest), Pandas, NumPy, PyArrow, Joblib, SQLite, Pytest
- **Research & EDA:** Jupyter Notebook, Matplotlib, Seaborn

## Current Implementation Status (Phase 6 Complete)
- **Implemented:** Full-stack academic prototype — Phase 1 data pipeline & causal feature engineering, Phase 2 unscaled Isolation Forest (`ROC-AUC = 0.8843`), Phase 3 FastAPI + SQLite backend, Phase 4 React + Vite + TypeScript + Tailwind CSS SOC dashboard (`frontend/`), Phase 5.1 administrator-focused plain-language explainability & UI, and Phase 6 Argon2id authentication, server-side opaque sessions, CSRF protection, RBAC (`ADMINISTRATOR`, `SECURITY_ANALYST`, `AUDITOR`), user management, and immutable security audit logging (`38` passing Pytest tests).
- **Future Scope:** Live organisational event streaming and SIEM integration.

## Run Full-Stack Application (Local Demonstration)

1. **Provision an Initial Administrator (First Time Only):**
```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_admin.py
```

2. **Backend (Terminal 1):**
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
3. **Frontend (Terminal 2):**
```powershell
cd frontend
npm install
npm run dev
```

Frontend UI: `http://localhost:5173` · OpenAPI docs: `http://127.0.0.1:8000/docs`

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
- [Authentication & RBAC (Phase 6)](docs/AUTHENTICATION_AND_RBAC.md)
- [Project Status](docs/PROJECT_STATUS.md)
- [Architecture & Preliminary API Contract](docs/ARCHITECTURE.md)
- [Dataset Documentation](docs/DATASET_DOCUMENTATION.md)
- [Data Cleaning Report](docs/DATA_CLEANING_REPORT.md)
- [Feature Engineering](docs/FEATURE_ENGINEERING.md)
- [Data Leakage Audit](docs/DATA_LEAKAGE_AUDIT.md)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
