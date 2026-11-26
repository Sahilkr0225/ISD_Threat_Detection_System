"""Read-only acceptance audit for Phase 5 & Phase 5.1 (Tasks 1, 2, 3, 6)."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
import tempfile

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import DATABASE_PATH, METRICS_DIR, PROCESSED_DATA_DIR
from scripts.refresh_explanations import refresh_explanations_in_db


def main() -> None:
    bak_path = DATABASE_PATH.with_suffix(".db.bak")
    if not bak_path.exists():
        raise FileNotFoundError(f"Backup not found: {bak_path}")

    cur = sqlite3.connect(str(DATABASE_PATH))
    bak = sqlite3.connect(str(bak_path))
    cur.row_factory = sqlite3.Row
    bak.row_factory = sqlite3.Row

    # --- Task 1: DB Preservation & Integrity ---
    integrity_res = [r[0] for r in cur.execute("PRAGMA integrity_check;").fetchall()]
    fk_res = cur.execute("PRAGMA foreign_key_check;").fetchall()

    emp_diff = cur.execute(
        "SELECT COUNT(*) FROM (SELECT * FROM employees EXCEPT SELECT * FROM bak_db.employees)"
    ) if False else None

    # Compare tables using Python sets/tuples for clean read-only comparison
    def fetch_all(conn: sqlite3.Connection, sql: str) -> list:
        return [tuple(r) for r in conn.execute(sql).fetchall()]

    emp_match = fetch_all(cur, "SELECT * FROM employees ORDER BY employee_id") == fetch_all(
        bak, "SELECT * FROM employees ORDER BY employee_id"
    )
    obs_match = fetch_all(
        cur, "SELECT * FROM employee_observations ORDER BY observation_id"
    ) == fetch_all(bak, "SELECT * FROM employee_observations ORDER BY observation_id")

    alerts_num_match = fetch_all(
        cur,
        "SELECT alert_id, observation_id, employee_id, anomaly_score, risk_score, priority, model_version FROM alerts ORDER BY alert_id",
    ) == fetch_all(
        bak,
        "SELECT alert_id, observation_id, employee_id, anomaly_score, risk_score, priority, model_version FROM alerts ORDER BY alert_id",
    )

    exp_num_match = fetch_all(
        cur,
        "SELECT explanation_id, alert_id, feature_name, current_value, historical_mean, historical_std, deviation, direction, historical_obs_count FROM alert_explanations ORDER BY explanation_id",
    ) == fetch_all(
        bak,
        "SELECT explanation_id, alert_id, feature_name, current_value, historical_mean, historical_std, deviation, direction, historical_obs_count FROM alert_explanations ORDER BY explanation_id",
    )

    bak_hist = fetch_all(bak, "SELECT * FROM investigation_history ORDER BY history_id")
    cur_hist_prefix = fetch_all(
        cur,
        f"SELECT * FROM investigation_history WHERE history_id <= {len(bak_hist)} ORDER BY history_id",
    )
    preexisting_hist_match = bak_hist == cur_hist_prefix

    cur_statuses = {
        r["status"]: int(r["cnt"])
        for r in cur.execute("SELECT status, COUNT(*) AS cnt FROM alerts GROUP BY status").fetchall()
    }
    cur_priorities = {
        r["priority"]: int(r["cnt"])
        for r in cur.execute("SELECT priority, COUNT(*) AS cnt FROM alerts GROUP BY priority").fetchall()
    }
    cur_counts = {
        t: int(cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
        for t in ["employees", "employee_observations", "alerts", "alert_explanations", "investigation_history"]
    }

    # --- Task 2: Idempotency on Temporary SQLite Backup ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "temp_audit.db"
        tmp_conn = sqlite3.connect(str(tmp_db))
        cur.backup(tmp_conn)
        tmp_conn.close()

        res1 = refresh_explanations_in_db(tmp_db)
        tc = sqlite3.connect(str(tmp_db))
        snap1_text = fetch_all(
            tc, "SELECT explanation_id, evidence_description, investigation_recommendation FROM alert_explanations ORDER BY explanation_id"
        )
        snap1_alerts = fetch_all(tc, "SELECT * FROM alerts ORDER BY alert_id")
        snap1_hist = fetch_all(tc, "SELECT * FROM investigation_history ORDER BY history_id")
        tc.close()

        res2 = refresh_explanations_in_db(tmp_db)
        tc2 = sqlite3.connect(str(tmp_db))
        snap2_text = fetch_all(
            tc2, "SELECT explanation_id, evidence_description, investigation_recommendation FROM alert_explanations ORDER BY explanation_id"
        )
        snap2_alerts = fetch_all(tc2, "SELECT * FROM alerts ORDER BY alert_id")
        snap2_hist = fetch_all(tc2, "SELECT * FROM investigation_history ORDER BY history_id")
        tc2.close()

        idempotency = {
            "run1_rows": res1["refreshed_explanation_rows"],
            "run2_rows": res2["refreshed_explanation_rows"],
            "identical_text_after_both_runs": snap1_text == snap2_text,
            "identical_alerts_after_both_runs": snap1_alerts == snap2_alerts,
            "identical_history_after_both_runs": snap1_hist == snap2_hist,
        }

    # --- Task 3: Alert #1184 email_activity_count std discrepancy ---
    bak_1184 = dict(
        bak.execute(
            "SELECT * FROM alert_explanations WHERE alert_id=1184 AND feature_name='email_activity_count'"
        ).fetchone()
    )
    cur_1184 = dict(
        cur.execute(
            "SELECT * FROM alert_explanations WHERE alert_id=1184 AND feature_name='email_activity_count'"
        ).fetchone()
    )

    hist_df = pd.read_parquet(
        PROCESSED_DATA_DIR / "cleaned_behavioral_data.parquet",
        columns=["employee_id", "activity_date", "email_activity_count"],
    )
    hist_df["activity_date_str"] = pd.to_datetime(hist_df["activity_date"]).dt.strftime("%Y-%m-%d")
    bmg_prior = (
        hist_df[(hist_df["employee_id"] == "BMG0917") & (hist_df["activity_date_str"] < "2011-03-19")]
        .sort_values("activity_date_str")
        .tail(14)
    )
    emails = bmg_prior["email_activity_count"].to_numpy(dtype=float)
    exact_mean = float(np.mean(emails))
    exact_std = float(np.std(emails, ddof=0))
    exact_dev = float((0.0 - exact_mean) / max(exact_std, 1.0))

    # --- Task 6: Explanation Accuracy Examples ---
    def sample_exp(where_sql: str) -> dict | None:
        r = cur.execute(
            f"""
            SELECT a.alert_id, a.priority, ae.feature_name, ae.current_value,
                   ae.historical_mean, ae.historical_std, ae.deviation, ae.direction,
                   ae.historical_obs_count, ae.evidence_description, ae.investigation_recommendation
            FROM alert_explanations ae
            JOIN alerts a ON a.alert_id = ae.alert_id
            WHERE {where_sql}
            LIMIT 1
            """
        ).fetchone()
        return dict(r) if r else None

    examples = {
        "increased_activity": sample_exp("ae.direction = 'above_baseline' AND ae.current_value >= 15"),
        "decreased_nonzero_activity": sample_exp("ae.direction = 'below_baseline' AND ae.current_value > 0"),
        "zero_recorded_activity": sample_exp("ae.direction = 'below_baseline' AND ae.current_value = 0"),
        "insufficient_history": sample_exp("ae.direction = 'insufficient_history'"),
        "zero_historical_variance": sample_exp("ae.historical_std = 0.0 AND ae.direction != 'insufficient_history'"),
    }

    bad_phrases = ("malicious intent", "confirmed insider", "data theft", "caused the isolation forest")
    bad_hits = int(
        cur.execute(
            "SELECT COUNT(*) FROM alert_explanations WHERE "
            + " OR ".join([f"LOWER(evidence_description) LIKE '%{p}%' OR LOWER(investigation_recommendation) LIKE '%{p}%'" for p in bad_phrases])
        ).fetchone()[0]
    )

    cur.close()
    bak.close()

    report = {
        "task1_preservation": {
            "sqlite_integrity_check": integrity_res,
            "sqlite_foreign_key_check_violations": len(fk_res),
            "employees_exact_match": emp_match,
            "observations_exact_match": obs_match,
            "alerts_numerical_and_fk_match": alerts_num_match,
            "explanations_numerical_match": exp_num_match,
            "preexisting_history_preserved": preexisting_hist_match,
            "preexisting_history_rows": len(bak_hist),
            "current_table_counts": cur_counts,
            "current_statuses": cur_statuses,
            "current_priorities": cur_priorities,
        },
        "task2_idempotency": idempotency,
        "task3_alert_1184_email_std": {
            "prior_14_values": [int(x) for x in emails.tolist()],
            "exact_mean": exact_mean,
            "exact_std_ddof0": exact_std,
            "exact_stabilized_dev": exact_dev,
            "backup_db_row": {k: bak_1184[k] for k in ["current_value", "historical_mean", "historical_std", "deviation"]},
            "current_db_row": {k: cur_1184[k] for k in ["current_value", "historical_mean", "historical_std", "deviation"]},
        },
        "task6_explanation_examples": examples,
        "task6_forbidden_claim_hits": bad_hits,
    }

    (METRICS_DIR / "phase5_1_acceptance_audit.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

