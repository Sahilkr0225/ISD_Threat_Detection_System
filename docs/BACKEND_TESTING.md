# Backend Testing & Verification

## Test Suite Structure (`backend/tests/`)
- `test_data_pipeline.py`: Parquet/CSV loading, schema/type/date/numeric/duplicate validation, canonical mapping, chronological splitting, and ground-truth alignment (`13` tests).
- `test_feature_engineering.py`: Causal `14obs` rolling deviations, zero-denominator/insufficient-history handling, no-future-leakage test, identifier/label exclusion (`3` tests).
- `test_isolation_forest.py`: Deterministic training, Joblib bundle roundtrip, non-finite rejection, validation threshold calibration, feature ordering (`5` tests).
- `test_phase3_scoring_and_explainability.py`: `ModelPredictor` validation/consistency, `RiskScorer` range/monotonicity/ties, `PriorityClassifier` boundaries, causal explainability & insufficient history (`5` tests).
- `test_phase3_database_and_api.py`: Temporary SQLite FK enforcement, idempotent inserts, status transition validation, investigation history, import/refresh idempotency, and authenticated FastAPI `TestClient` end-to-end tests (`5` tests).
- `test_phase6_auth_rbac_audit.py`: Argon2id hashing & password policy, session lifecycle/expiry/revocation/rate-limiting (`429`), CSRF & origin enforcement (`403`), full RBAC matrix across `ADMINISTRATOR`/`SECURITY_ANALYST`/`AUDITOR` and unauthenticated (`401`/`403`), user management + last-admin/self-protection (`409`), actor attribution, and schema migration idempotency (`6` tests).

## Execution Commands
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\smoke_test_api.py
```
- **Latest Verified Result:** `38 passed` in `backend/tests`; `pip check` reported `No broken requirements found.`; `scripts/smoke_test_api.py` passed against a temporary copy of `insider_threat.db`.

## Known Test Warning
- `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` (originating from `fastapi/testclient.py:1` with `httpx 0.28.1`). This is an upstream Starlette/FastAPI test-client notice and does not affect runtime or test correctness.
