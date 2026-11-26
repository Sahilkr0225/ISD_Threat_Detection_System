# Backend Testing & Verification

## Test Suite Structure (`backend/tests/`)
- `test_data_pipeline.py`: Parquet/CSV loading, schema/type/date/numeric/duplicate validation, canonical mapping, chronological splitting, and ground-truth alignment (`13` tests).
- `test_feature_engineering.py`: Causal `14obs` rolling deviations, zero-denominator/insufficient-history handling, no-future-leakage test, identifier/label exclusion (`3` tests).
- `test_isolation_forest.py`: Deterministic training, Joblib bundle roundtrip, non-finite rejection, validation threshold calibration, feature ordering (`5` tests).
- `test_phase3_scoring_and_explainability.py`: `ModelPredictor` validation/consistency, `RiskScorer` range/monotonicity/ties, `PriorityClassifier` boundaries, causal explainability & insufficient history (`5` tests).
- `test_phase3_database_and_api.py`: Temporary SQLite FK enforcement, idempotent inserts, status transition validation, investigation history, and end-to-end FastAPI `TestClient` tests for all 15 endpoints (`3` tests).

## Execution Commands
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\smoke_test_api.py
```

## Known Test Warning
- `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` (originating from `fastapi/testclient.py:1` with `httpx 0.28.1`). This is an upstream Starlette/FastAPI test-client notice and does not affect runtime or test correctness.

