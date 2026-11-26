"""Acceptance verification script for Phase 3 checks 2, 3, 4, 5, and 7."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import DATABASE_PATH, METRICS_DIR, PROCESSED_DATA_DIR


def main() -> None:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row

    # Check 4: Update any existing DB rows to 'stabilized historical deviation'
    updated_rows = conn.execute(
        """
        UPDATE alert_explanations
        SET evidence_description = REPLACE(
            evidence_description,
            'stabilized std',
            'stabilized historical deviation'
        )
        WHERE evidence_description LIKE '%stabilized std%'
        """
    ).rowcount
    conn.commit()

    # Check 2: Early held-out test observations (2011-02-06) use prior train/val history
    early_rows = conn.execute(
        """
        SELECT ae.historical_obs_count
        FROM alert_explanations ae
        JOIN alerts a ON a.alert_id = ae.alert_id
        JOIN employee_observations o ON o.observation_id = a.observation_id
        WHERE o.activity_date = '2011-02-06'
        """
    ).fetchall()
    early_counts = [int(r["historical_obs_count"]) for r in early_rows]

    # Check 3: Numerically compare explanation deviations vs Phase 1 *_hist_dev_14obs
    feature_to_dev_col = {
        "login_count": "login_hist_dev_14obs",
        "after_hours_login_count": "after_hours_hist_dev_14obs",
        "http_activity_count": "http_hist_dev_14obs",
        "email_activity_count": "email_hist_dev_14obs",
        "file_activity_count": "file_hist_dev_14obs",
        "usb_activity_count": "usb_hist_dev_14obs",
    }
    test_df = pd.read_parquet(PROCESSED_DATA_DIR / "test.parquet")
    test_df["activity_date_str"] = pd.to_datetime(test_df["activity_date"]).dt.strftime("%Y-%m-%d")
    test_lookup = test_df.set_index(["employee_id", "activity_date_str"])[list(feature_to_dev_col.values())]

    sample_exps = conn.execute(
        """
        SELECT a.employee_id, o.activity_date, ae.feature_name, ae.deviation
        FROM alert_explanations ae
        JOIN alerts a ON a.alert_id = ae.alert_id
        JOIN employee_observations o ON o.observation_id = a.observation_id
        WHERE ae.deviation IS NOT NULL
        LIMIT 1000
        """
    ).fetchall()

    diffs = []
    for r in sample_exps:
        dev_col = feature_to_dev_col[r["feature_name"]]
        p1_val = float(test_lookup.loc[(r["employee_id"], r["activity_date"]), dev_col])
        diffs.append(abs(float(r["deviation"]) - p1_val))

    max_diff = float(np.max(diffs)) if diffs else 0.0

    # Check 5 & 7: Verify smoke results have no GT labels and have all dashboard summary fields
    smoke_path = METRICS_DIR / "phase3_smoke_results.json"
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))["samples"]
    summary_keys = set(smoke["/api/v1/dashboard/summary"].keys())
    required_summary_keys = {
        "unique_employees",
        "total_observations",
        "flagged_observations",
        "total_alerts",
        "open_alerts",
        "under_review_alerts",
        "resolved_alerts",
        "dismissed_alerts",
        "alerts_by_priority",
        "top_employees",
        "recent_investigations",
        "model_version",
        "coverage_start_date",
        "coverage_end_date",
    }
    missing_summary_keys = sorted(required_summary_keys - summary_keys)

    gt_forbidden = {"is_malicious_day", "scenario", "malicious_event_count"}
    predict_keys = set(smoke["POST /api/v1/model/predict"]["predictions"][0].keys())
    alert_detail_keys = set(smoke[next(k for k in smoke if k.startswith("/api/v1/alerts/") and not k.endswith("/history"))].keys())

    report = {
        "check2_early_test_date_2011_02_06": {
            "explanation_rows_checked": len(early_counts),
            "min_historical_obs_count": min(early_counts) if early_counts else None,
            "max_historical_obs_count": max(early_counts) if early_counts else None,
        },
        "check3_deviation_vs_phase1": {
            "compared_explanations": len(diffs),
            "max_abs_diff": round(max_diff, 8),
        },
        "check4_updated_db_wording_rows": updated_rows,
        "check5_gt_excluded": {
            "predict_has_gt": bool(gt_forbidden & predict_keys),
            "alert_detail_has_gt": bool(gt_forbidden & alert_detail_keys),
        },
        "check7_dashboard_summary_missing_keys": missing_summary_keys,
    }
    print(json.dumps(report, indent=2))
    conn.close()


if __name__ == "__main__":
    main()

