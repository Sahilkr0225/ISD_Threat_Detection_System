"""Integration tests for SQLite persistence, alert workflow, and FastAPI endpoints."""

from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import MODEL_BUNDLE_PATH, VALIDATION_SCORE_REF_PATH
from backend.app.database.connection import get_db_connection
from backend.app.database.repository import (
    InvalidStatusTransitionError,
    get_dashboard_summary,
    update_alert_status,
)
from backend.app.database.schema import init_database
from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES
from backend.app.main import create_app


def _seed_temp_db(db_path: Path) -> None:
    """Populate a temporary SQLite DB with deterministic sample records."""
    init_database(db_path)
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO employees (employee_id, role, department, functional_unit, first_activity_date, last_activity_date)
            VALUES ('EMP_T1', 'Engineer', '3 - Engineering', '2 - R&D', '2011-02-06', '2011-02-07')
            """
        )
        conn.execute(
            """
            INSERT INTO employee_observations (
                employee_id, activity_date, login_count, after_hours_login_count,
                http_activity_count, email_activity_count, file_activity_count,
                usb_activity_count, total_activity_count, after_hours_ratio,
                is_weekend, model_version, anomaly_score, risk_score, priority, created_at
            ) VALUES (
                'EMP_T1', '2011-02-06', 4, 3, 120, 10, 15, 6, 155, 0.75, 0,
                'isolation_forest_v1', 0.14, 99.5, 'Critical', '2026-11-26T12:00:00+00:00'
            )
            """
        )
        obs_id = conn.execute("SELECT observation_id FROM employee_observations").fetchone()[0]
        conn.execute(
            """
            INSERT INTO alerts (
                observation_id, employee_id, anomaly_score, risk_score, priority,
                status, model_version, created_at, updated_at
            ) VALUES (
                ?, 'EMP_T1', 0.14, 99.5, 'Critical', 'OPEN',
                'isolation_forest_v1', '2026-11-26T12:00:00+00:00', '2026-11-26T12:00:00+00:00'
            )
            """,
            (obs_id,),
        )
        alert_id = conn.execute("SELECT alert_id FROM alerts").fetchone()[0]
        conn.execute(
            """
            INSERT INTO alert_explanations (
                alert_id, feature_name, activity_label, current_value,
                historical_mean, historical_std, deviation, direction,
                historical_obs_count, evidence_description, investigation_recommendation
            ) VALUES (
                ?, 'usb_activity_count', 'USB / Removable Device Activity', 6.0,
                0.2, 0.4, 5.8, 'above_baseline', 14,
                'USB / Removable Device Activity count (6) is 5.80 stabilized historical deviation above baseline.',
                'Verify business justification.'
            )
            """,
            (alert_id,),
        )


def test_sqlite_foreign_keys_and_idempotency(tmp_path: Path) -> None:
    db_path = tmp_path / "test_fk.db"
    _seed_temp_db(db_path)

    with get_db_connection(db_path) as conn:
        # Foreign-key enforcement rejects observation for unknown employee
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO employee_observations (
                    employee_id, activity_date, login_count, after_hours_login_count,
                    http_activity_count, email_activity_count, file_activity_count,
                    usb_activity_count, total_activity_count, after_hours_ratio,
                    is_weekend, model_version, anomaly_score, risk_score, priority, created_at
                ) VALUES (
                    'UNKNOWN_EMP', '2011-02-06', 1, 0, 1, 1, 0, 0, 3, 0.0, 0,
                    'isolation_forest_v1', 0.0, 50.0, 'Medium', '2026-11-26T12:00:00+00:00'
                )
                """
            )

        # Idempotent alert insert ignores duplicate observation_id
        obs_id = conn.execute("SELECT observation_id FROM employee_observations").fetchone()[0]
        conn.execute(
            """
            INSERT OR IGNORE INTO alerts (
                observation_id, employee_id, anomaly_score, risk_score, priority,
                status, model_version, created_at, updated_at
            ) VALUES (
                ?, 'EMP_T1', 0.14, 99.5, 'Critical', 'OPEN',
                'isolation_forest_v1', '2026-11-26T12:00:00+00:00', '2026-11-26T12:00:00+00:00'
            )
            """,
            (obs_id,),
        )
        assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1


def test_status_transition_validation_and_history(tmp_path: Path) -> None:
    db_path = tmp_path / "test_wf.db"
    _seed_temp_db(db_path)

    with get_db_connection(db_path) as conn:
        with pytest.raises(InvalidStatusTransitionError):
            update_alert_status(conn, alert_id=1, new_status="OPEN", analyst_note="No-op")

        updated = update_alert_status(
            conn, alert_id=1, new_status="UNDER_REVIEW", analyst_note="Checking USB logs"
        )
        assert updated is not None
        assert updated["status"] == "UNDER_REVIEW"

        summary = get_dashboard_summary(conn)
        assert summary["open_alerts"] == 0
        assert summary["under_review_alerts"] == 1


def test_fastapi_endpoints_end_to_end(tmp_path: Path) -> None:
    if not MODEL_BUNDLE_PATH.exists() or not VALIDATION_SCORE_REF_PATH.exists():
        pytest.skip("Model bundle or validation score reference missing.")

    db_path = tmp_path / "api_test.db"
    _seed_temp_db(db_path)

    app = create_app(
        db_path=db_path,
        model_bundle_path=MODEL_BUNDLE_PATH,
        val_ref_path=VALIDATION_SCORE_REF_PATH,
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        assert client.get("/api/v1/dashboard/summary").json()["unique_employees"] == 1
        assert len(client.get("/api/v1/dashboard/trends").json()["items"]) == 1
        assert client.get("/api/v1/employees").json()["pagination"]["total"] == 1
        assert client.get("/api/v1/employees/EMP_T1").json()["employee_id"] == "EMP_T1"
        assert client.get("/api/v1/employees/UNKNOWN").status_code == 404
        assert len(client.get("/api/v1/employees/EMP_T1/history").json()["items"]) == 1
        assert client.get("/api/v1/anomalies").json()["pagination"]["total"] == 1

        alerts_resp = client.get("/api/v1/alerts?priority=Critical&status=OPEN")
        assert alerts_resp.status_code == 200
        assert alerts_resp.json()["pagination"]["total"] == 1

        detail = client.get("/api/v1/alerts/1").json()
        assert len(detail["explanations"]) == 1
        assert "is_malicious_day" not in detail

        # Investigation workflow: OPEN -> UNDER_REVIEW -> RESOLVED
        r1 = client.patch(
            "/api/v1/alerts/1/status",
            json={"new_status": "UNDER_REVIEW", "analyst_note": "Investigating"},
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "UNDER_REVIEW"

        r2 = client.patch(
            "/api/v1/alerts/1/status",
            json={"new_status": "RESOLVED", "analyst_note": "Authorized transfer"},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "RESOLVED"

        hist = client.get("/api/v1/alerts/1/history").json()
        assert len(hist["items"]) == 2

        # Model info, metrics, data summary, predict
        assert client.get("/api/v1/model/info").json()["feature_count"] == 20
        assert client.get("/api/v1/model/metrics").json()["held_out_test_summary"]["roc_auc"] == 0.8843
        assert client.get("/api/v1/data/summary").json()["observation_count"] == 1

        vec = {f: 0.0 for f in APPROVED_MODEL_FEATURES}
        pred = client.post("/api/v1/model/predict", json={"observations": [vec]})
        assert pred.status_code == 200
        assert 0.0 <= pred.json()["predictions"][0]["risk_score"] <= 100.0


def test_import_idempotency_preserves_alert_status_and_history(tmp_path: Path) -> None:
    """Importing twice into a temp SQLite DB preserves counts, statuses, notes, and history."""
    import pandas as pd
    from backend.app.core.config import PROCESSED_DATA_DIR
    from backend.app.database.importer import import_test_predictions_to_db

    test_src = PROCESSED_DATA_DIR / "test.parquet"
    preds_src = PROCESSED_DATA_DIR / "test_predictions.parquet"
    hist_src = PROCESSED_DATA_DIR / "cleaned_behavioral_data.parquet"
    if not (test_src.exists() and preds_src.exists() and hist_src.exists() and MODEL_BUNDLE_PATH.exists() and VALIDATION_SCORE_REF_PATH.exists()):
        pytest.skip("Processed artifacts missing for idempotency test.")

    # Use a small 200-row slice so the test runs in < 1s
    sub_test = tmp_path / "sub_test.parquet"
    sub_preds = tmp_path / "sub_preds.parquet"
    df_t = pd.read_parquet(test_src).head(200)
    df_p = pd.read_parquet(preds_src).head(200)
    df_t.to_parquet(sub_test, index=False)
    df_p.to_parquet(sub_preds, index=False)

    db_path = tmp_path / "idem.db"
    res1 = import_test_predictions_to_db(
        db_path=db_path,
        test_parquet_path=sub_test,
        test_preds_path=sub_preds,
        cleaned_history_path=hist_src,
    )
    assert res1["table_counts"]["alerts"] > 0

    # Mutate first alert status & add analyst note
    with get_db_connection(db_path) as conn:
        first_alert_id = conn.execute("SELECT alert_id FROM alerts ORDER BY alert_id LIMIT 1").fetchone()[0]
        update_alert_status(conn, first_alert_id, "UNDER_REVIEW", "Preserved note check")

    # Re-import identical dataset
    res2 = import_test_predictions_to_db(
        db_path=db_path,
        test_parquet_path=sub_test,
        test_preds_path=sub_preds,
        cleaned_history_path=hist_src,
    )
    assert res2["table_counts"]["employees"] == res1["table_counts"]["employees"]
    assert res2["table_counts"]["employee_observations"] == res1["table_counts"]["employee_observations"]
    assert res2["table_counts"]["alerts"] == res1["table_counts"]["alerts"]
    assert res2["table_counts"]["alert_explanations"] == res1["table_counts"]["alert_explanations"]
    assert res2["table_counts"]["investigation_history"] == 1

    with get_db_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM alerts WHERE alert_id = ?", (first_alert_id,)).fetchone()
        hist = conn.execute("SELECT analyst_note FROM investigation_history WHERE alert_id = ?", (first_alert_id,)).fetchone()
        assert row["status"] == "UNDER_REVIEW"
        assert hist["analyst_note"] == "Preserved note check"


def test_explanation_refresh_preserves_alerts_and_history(tmp_path: Path) -> None:
    from scripts.refresh_explanations import refresh_explanations_in_db

    db_path = tmp_path / "refresh_test.db"
    _seed_temp_db(db_path)
    with get_db_connection(db_path) as conn:
        update_alert_status(conn, 1, "UNDER_REVIEW", "Keep my note")

    res = refresh_explanations_in_db(db_path)
    assert res["refreshed_explanation_rows"] == 1

    with get_db_connection(db_path) as conn:
        al = conn.execute("SELECT status, priority, anomaly_score, risk_score FROM alerts WHERE alert_id = 1").fetchone()
        hist = conn.execute("SELECT analyst_note FROM investigation_history WHERE alert_id = 1").fetchone()
        exp = conn.execute("SELECT evidence_description, investigation_recommendation FROM alert_explanations WHERE alert_id = 1").fetchone()
        assert al["status"] == "UNDER_REVIEW"
        assert al["priority"] == "Critical"
        assert hist["analyst_note"] == "Keep my note"
        assert "higher than usual" in exp["evidence_description"]
        assert "removable-device" in exp["investigation_recommendation"]

