"""Live HTTP smoke test against uvicorn on 127.0.0.1:8000 (read-only on prod DB)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES


def main() -> None:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    base = "http://127.0.0.1:8000"
    results = {}
    try:
        # Wait for server readiness
        for _ in range(30):
            try:
                r = httpx.get(f"{base}/api/v1/health", timeout=2.0)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.3)

        endpoints = [
            ("GET", "/docs"),
            ("GET", "/api/v1/health"),
            ("GET", "/api/v1/dashboard/summary"),
            ("GET", "/api/v1/dashboard/trends"),
            ("GET", "/api/v1/employees?page=1&page_size=5"),
            ("GET", "/api/v1/anomalies?page=1&page_size=5"),
            ("GET", "/api/v1/alerts?priority=Critical&page=1&page_size=3"),
            ("GET", "/api/v1/model/info"),
            ("GET", "/api/v1/model/metrics"),
            ("GET", "/api/v1/data/summary"),
        ]

        samples = {}
        for method, path in endpoints:
            resp = httpx.request(method, f"{base}{path}", timeout=5.0)
            results[path] = resp.status_code
            assert resp.status_code == 200, f"{path} failed with {resp.status_code}: {resp.text}"
            if path != "/docs":
                samples[path] = resp.json()

        # Fetch detail + history for first Critical alert & first employee
        first_alert_id = samples["/api/v1/alerts?priority=Critical&page=1&page_size=3"]["items"][0]["alert_id"]
        first_emp_id = samples["/api/v1/alerts?priority=Critical&page=1&page_size=3"]["items"][0]["employee_id"]

        for path in [
            f"/api/v1/alerts/{first_alert_id}",
            f"/api/v1/alerts/{first_alert_id}/history",
            f"/api/v1/employees/{first_emp_id}",
            f"/api/v1/employees/{first_emp_id}/history?page=1&page_size=5",
        ]:
            resp = httpx.get(f"{base}{path}", timeout=5.0)
            results[path] = resp.status_code
            assert resp.status_code == 200, f"{path} failed with {resp.status_code}"
            samples[path] = resp.json()

        # POST /api/v1/model/predict
        vec = {f: 0.0 for f in APPROVED_MODEL_FEATURES}
        pred_resp = httpx.post(
            f"{base}/api/v1/model/predict",
            json={"observations": [vec]},
            timeout=5.0,
        )
        results["POST /api/v1/model/predict"] = pred_resp.status_code
        assert pred_resp.status_code == 200
        samples["POST /api/v1/model/predict"] = pred_resp.json()

        out_path = PROJECT_ROOT / "reports" / "metrics" / "phase3_smoke_results.json"
        out_path.write_text(
            json.dumps({"status_codes": results, "samples": samples}, indent=2),
            encoding="utf-8",
        )
        print(json.dumps({"status_codes": results}, indent=2))
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()

