"""Live HTTP smoke test against uvicorn on 127.0.0.1:8000 using a temporary DB copy."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import DATABASE_PATH
from backend.app.database.auth_repository import create_user
from backend.app.database.connection import get_db_connection
from backend.app.database.schema import init_database
from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES


def _backup_sqlite(src: Path, dst: Path) -> None:
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Operational DB not found: {DATABASE_PATH}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="isd_smoke_"))
    tmp_db = tmp_dir / "smoke.db"
    _backup_sqlite(DATABASE_PATH, tmp_db)
    init_database(tmp_db)

    with get_db_connection(tmp_db) as conn:
        create_user(
            conn,
            username="smoke_admin",
            display_name="Smoke Test Admin",
            password="SmokeAdmin!2026",
            role="ADMINISTRATOR",
        )
        create_user(
            conn,
            username="smoke_analyst",
            display_name="Smoke Analyst",
            password="SmokeAnalyst!2026",
            role="SECURITY_ANALYST",
        )
        create_user(
            conn,
            username="smoke_auditor",
            display_name="Smoke Auditor",
            password="SmokeAuditor!2026",
            role="AUDITOR",
        )

    env = os.environ.copy()
    env["INSIDER_THREAT_DB_PATH"] = str(tmp_db)
    env["APP_ENV"] = "development"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8010",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    base = "http://127.0.0.1:8010"
    results: dict[str, int] = {}
    samples: dict[str, object] = {}

    try:
        for _ in range(30):
            try:
                r = httpx.get(f"{base}/api/v1/health", timeout=2.0)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.3)

        # Unauthenticated check
        unauth = httpx.get(f"{base}/api/v1/dashboard/summary", timeout=5.0)
        results["UNAUTH /api/v1/dashboard/summary"] = unauth.status_code
        assert unauth.status_code == 401

        with httpx.Client(base_url=base, timeout=5.0) as admin_client:
            login_resp = admin_client.post(
                "/api/v1/auth/login",
                json={"username": "smoke_admin", "password": "SmokeAdmin!2026"},
            )
            assert login_resp.status_code == 200, login_resp.text
            csrf_token = login_resp.json()["csrf_token"]
            csrf_headers = {"X-CSRF-Token": csrf_token}

            endpoints = [
                ("GET", "/docs"),
                ("GET", "/api/v1/health"),
                ("GET", "/api/v1/auth/me"),
                ("GET", "/api/v1/dashboard/summary"),
                ("GET", "/api/v1/dashboard/trends"),
                ("GET", "/api/v1/employees?page=1&page_size=5"),
                ("GET", "/api/v1/anomalies?page=1&page_size=5"),
                ("GET", "/api/v1/alerts?priority=Critical&page=1&page_size=3"),
                ("GET", "/api/v1/model/info"),
                ("GET", "/api/v1/model/metrics"),
                ("GET", "/api/v1/data/summary"),
                ("GET", "/api/v1/users"),
                ("GET", "/api/v1/audit-logs"),
            ]

            for method, path in endpoints:
                resp = admin_client.request(method, path)
                results[path] = resp.status_code
                assert resp.status_code == 200, f"{path} failed: {resp.status_code} {resp.text}"
                if path != "/docs":
                    samples[path] = resp.json()

            first_alert = samples["/api/v1/alerts?priority=Critical&page=1&page_size=3"]["items"][0]
            first_alert_id = first_alert["alert_id"]
            first_emp_id = first_alert["employee_id"]

            for path in [
                f"/api/v1/alerts/{first_alert_id}",
                f"/api/v1/alerts/{first_alert_id}/history",
                f"/api/v1/employees/{first_emp_id}",
                f"/api/v1/employees/{first_emp_id}/history?page=1&page_size=5",
            ]:
                resp = admin_client.get(path)
                results[path] = resp.status_code
                assert resp.status_code == 200
                samples[path] = resp.json()

            vec = {f: 0.0 for f in APPROVED_MODEL_FEATURES}
            pred_resp = admin_client.post(
                "/api/v1/model/predict",
                json={"observations": [vec]},
                headers=csrf_headers,
            )
            results["POST /api/v1/model/predict"] = pred_resp.status_code
            assert pred_resp.status_code == 200
            samples["POST /api/v1/model/predict"] = pred_resp.json()

        # Verify RBAC restrictions for analyst and auditor
        with httpx.Client(base_url=base, timeout=5.0) as analyst_client:
            r = analyst_client.post(
                "/api/v1/auth/login",
                json={"username": "smoke_analyst", "password": "SmokeAnalyst!2026"},
            )
            assert r.status_code == 200
            assert analyst_client.get("/api/v1/model/info").status_code == 403
            assert analyst_client.get("/api/v1/users").status_code == 403
            results["ANALYST /api/v1/model/info"] = 403

        with httpx.Client(base_url=base, timeout=5.0) as auditor_client:
            r = auditor_client.post(
                "/api/v1/auth/login",
                json={"username": "smoke_auditor", "password": "SmokeAuditor!2026"},
            )
            assert r.status_code == 200
            auditor_csrf = r.json()["csrf_token"]
            assert auditor_client.get("/api/v1/audit-logs").status_code == 200
            assert (
                auditor_client.patch(
                    f"/api/v1/alerts/{first_alert_id}/status",
                    json={"new_status": "UNDER_REVIEW", "analyst_note": "Forbidden"},
                    headers={"X-CSRF-Token": auditor_csrf},
                ).status_code
                == 403
            )
            results["AUDITOR PATCH alert"] = 403

        out_path = PROJECT_ROOT / "reports" / "metrics" / "phase6_smoke_results.json"
        out_path.write_text(
            json.dumps({"status_codes": results}, indent=2),
            encoding="utf-8",
        )
        print("SMOKE TEST PASSED:", json.dumps(results, indent=2))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
