# System Architecture & Preliminary API Contract

## 1. Monorepo Architecture
- `backend/app/data/`: Dataset loading (`loader.py`), schema/type/integrity validation (`validator.py`), canonical mapping, cleaning, and chronological splitting (`preprocessing.py`). *(Implemented)*
- `backend/app/features/`: Causal rolling behavioural feature engineering (`feature_engineering.py`). *(Implemented)*
- `backend/app/ml/`: Isolation Forest training, Joblib persistence, and inference. *(Planned — Phase 2)*
- `backend/app/risk/` & `backend/app/explainability/`: Normalized `0–100` risk scoring and per-feature deviation explanations. *(Planned — Phase 3)*
- `backend/app/database/` & `backend/app/api/routes/`: SQLite alert persistence and FastAPI REST endpoints. *(Planned — Phase 3)*
- `frontend/`: React + Vite + TypeScript + Tailwind CSS + Recharts monitoring UI. *(Planned — Phase 4)*

## 2. Data Flow
```text
data/raw/master_behavioral_matrix.parquet
   └─▶ loader.py ─▶ validator.py ─▶ preprocessing.py (canonical schema + chronological split)
          └─▶ feature_engineering.py (20 causal features) ─▶ data/processed/{train,validation,test}.parquet
                 └─▶ [Phase 2] Isolation Forest ─▶ [Phase 3] Risk + Explainability + SQLite ─▶ [Phase 4] React UI
```

## 3. Preliminary REST API Contract (Planned for Phase 3+)
Only `GET /api/v1/health` is active in Phase 1. All remaining routes below are preliminary contracts for future implementation:

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service liveness check *(Implemented minimal stub)* |
| `GET` | `/api/v1/dashboard/summary` | Aggregate risk & alert KPIs |
| `GET` | `/api/v1/employees` | Paginated employee risk directory |
| `GET` | `/api/v1/employees/{employee_id}` | Employee behavioural timeline & baseline |
| `GET` | `/api/v1/anomalies` | Detected anomalous employee-day records |
| `GET` | `/api/v1/alerts` | Generated security alerts |
| `GET` | `/api/v1/alerts/{alert_id}` | Alert detail with behavioural deviation explanation |
| `PATCH` | `/api/v1/alerts/{alert_id}/status` | Analyst investigation status update |
| `GET` | `/api/v1/model/metrics` | Model metadata & evaluation metrics |
| `POST` | `/api/v1/model/predict` | Score uploaded/new employee-day activity |
| `POST` | `/api/v1/data/upload` | Ingest & validate new activity dataset |

