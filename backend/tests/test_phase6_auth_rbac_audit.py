"""Phase 6 tests for Authentication, Session Management, CSRF, RBAC, and Audit Logs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import MODEL_BUNDLE_PATH, VALIDATION_SCORE_REF_PATH
from backend.app.core.security import (
    hash_password,
    hash_session_token,
    login_rate_limiter,
    validate_password_policy,
    verify_password,
)
from backend.app.database.auth_repository import create_user
from backend.app.database.connection import get_db_connection
from backend.app.database.schema import init_database
from backend.app.features.feature_engineering import APPROVED_MODEL_FEATURES
from backend.app.main import create_app


def _seed_phase6_db(db_path: Path) -> None:
    """Create a temp DB with one employee, one alert, and three role users."""
    init_database(db_path)
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO employees (
                employee_id, role, department, functional_unit,
                first_activity_date, last_activity_date
            ) VALUES (
                'EMP_P6', 'Engineer', '3 - Engineering', '2 - R&D',
                '2011-02-06', '2011-02-07'
            )
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
                'EMP_P6', '2011-02-06', 5, 3, 120, 12, 20, 4, 161, 0.6, 0,
                'isolation_forest_v1', 0.14, 99.5, 'Critical', '2026-11-26T12:00:00+00:00'
            )
            """
        )
        obs_id = conn.execute(
            "SELECT observation_id FROM employee_observations"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO alerts (
                observation_id, employee_id, anomaly_score, risk_score, priority,
                status, model_version, created_at, updated_at
            ) VALUES (
                ?, 'EMP_P6', 0.14, 99.5, 'Critical', 'OPEN',
                'isolation_forest_v1', '2026-11-26T12:00:00+00:00', '2026-11-26T12:00:00+00:00'
            )
            """,
            (obs_id,),
        )
        create_user(
            conn,
            username="admin_user",
            display_name="System Admin",
            password="AdminPassword!123",
            role="ADMINISTRATOR",
        )
        create_user(
            conn,
            username="analyst_user",
            display_name="SOC Analyst",
            password="AnalystPassword!123",
            role="SECURITY_ANALYST",
        )
        create_user(
            conn,
            username="auditor_user",
            display_name="Compliance Auditor",
            password="AuditorPassword!123",
            role="AUDITOR",
        )


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["csrf_token"]


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    login_rate_limiter._failures.clear()


def test_argon2id_hashing_and_password_policy() -> None:
    hashed = hash_password("StrongPass!2026")
    assert hashed.startswith("$argon2id$")
    assert verify_password("StrongPass!2026", hashed) is True
    assert verify_password("WrongPass!2026", hashed) is False

    with pytest.raises(ValueError):
        validate_password_policy("short123")
    with pytest.raises(ValueError):
        validate_password_policy("x" * 129)


def test_session_lifecycle_expiry_revocation_and_rate_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "session_test.db"
    _seed_phase6_db(db_path)

    app = create_app(
        db_path=db_path,
        model_bundle_path=MODEL_BUNDLE_PATH,
        val_ref_path=VALIDATION_SCORE_REF_PATH,
    )
    with TestClient(app) as client:
        # Unauthenticated health and csrf work, /auth/me fails with 401
        assert client.get("/api/v1/health").json() == {"status": "ok", "phase": "6"}
        assert client.get("/api/v1/auth/me").status_code == 401

        # Invalid login attempts trigger rate limit after 5 failures
        for _ in range(5):
            bad = client.post(
                "/api/v1/auth/login",
                json={"username": "admin_user", "password": "WrongPassword!999"},
            )
            assert bad.status_code == 401
        throttled = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": "AdminPassword!123"},
        )
        assert throttled.status_code == 429

        login_rate_limiter._failures.clear()

        # Successful login sets HttpOnly session cookie & returns user + csrf_token
        csrf = _login(client, "admin_user", "AdminPassword!123")
        raw_session = client.cookies.get("isd_session")
        assert raw_session is not None

        with get_db_connection(db_path) as conn:
            row = conn.execute(
                "SELECT token_hash, revoked_at FROM sessions LIMIT 1"
            ).fetchone()
            assert row["token_hash"] == hash_session_token(raw_session)
            assert row["token_hash"] != raw_session
            assert row["revoked_at"] is None

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["username"] == "admin_user"
        assert me.json()["user"]["role"] == "ADMINISTRATOR"

        # Logout revokes session
        out = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
        assert out.status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401

        # Expired session in DB is rejected
        _login(client, "admin_user", "AdminPassword!123")
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        with get_db_connection(db_path) as conn:
            conn.execute("UPDATE sessions SET expires_at = ?", (past,))
        assert client.get("/api/v1/auth/me").status_code == 401


def test_csrf_and_origin_enforcement(tmp_path: Path) -> None:
    db_path = tmp_path / "csrf_test.db"
    _seed_phase6_db(db_path)
    app = create_app(
        db_path=db_path,
        model_bundle_path=MODEL_BUNDLE_PATH,
        val_ref_path=VALIDATION_SCORE_REF_PATH,
    )

    with TestClient(app) as client:
        csrf = _login(client, "analyst_user", "AnalystPassword!123")

        # Missing CSRF header -> 403
        no_csrf = client.patch(
            "/api/v1/alerts/1/status",
            json={"new_status": "UNDER_REVIEW", "analyst_note": "No CSRF"},
        )
        assert no_csrf.status_code == 403

        # Wrong CSRF header -> 403
        bad_csrf = client.patch(
            "/api/v1/alerts/1/status",
            json={"new_status": "UNDER_REVIEW", "analyst_note": "Bad CSRF"},
            headers={"X-CSRF-Token": "invalid-token"},
        )
        assert bad_csrf.status_code == 403

        # Untrusted Origin -> 403
        bad_origin = client.patch(
            "/api/v1/alerts/1/status",
            json={"new_status": "UNDER_REVIEW", "analyst_note": "Bad origin"},
            headers={"X-CSRF-Token": csrf, "Origin": "https://evil.example"},
        )
        assert bad_origin.status_code == 403

        # Valid CSRF + trusted Origin -> 200
        ok = client.patch(
            "/api/v1/alerts/1/status",
            json={"new_status": "UNDER_REVIEW", "analyst_note": "Valid CSRF"},
            headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"},
        )
        assert ok.status_code == 200

    with get_db_connection(db_path) as conn:
        csrf_logs = conn.execute(
            "SELECT COUNT(*) FROM security_audit_logs WHERE action = 'CSRF_REJECTED'"
        ).fetchone()[0]
        assert csrf_logs >= 3


def test_rbac_matrix_across_all_roles(tmp_path: Path) -> None:
    db_path = tmp_path / "rbac_test.db"
    _seed_phase6_db(db_path)
    app = create_app(
        db_path=db_path,
        model_bundle_path=MODEL_BUNDLE_PATH,
        val_ref_path=VALIDATION_SCORE_REF_PATH,
    )
    vec = {f: 0.0 for f in APPROVED_MODEL_FEATURES}

    # Unauthenticated requests -> 401
    with TestClient(app) as anon:
        for path in [
            "/api/v1/dashboard/summary",
            "/api/v1/employees",
            "/api/v1/alerts",
            "/api/v1/model/info",
            "/api/v1/users",
            "/api/v1/audit-logs",
        ]:
            assert anon.get(path).status_code == 401

    # SECURITY_ANALYST
    with TestClient(app) as analyst:
        csrf = _login(analyst, "analyst_user", "AnalystPassword!123")
        assert analyst.get("/api/v1/dashboard/summary").status_code == 200
        assert analyst.get("/api/v1/employees").status_code == 200
        assert analyst.get("/api/v1/anomalies").status_code == 200
        assert analyst.get("/api/v1/alerts").status_code == 200
        assert analyst.get("/api/v1/alerts/1").status_code == 200
        assert (
            analyst.patch(
                "/api/v1/alerts/1/status",
                json={"new_status": "UNDER_REVIEW", "analyst_note": "Analyst triage"},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 200
        )
        assert analyst.get("/api/v1/model/info").status_code == 403
        assert analyst.get("/api/v1/model/metrics").status_code == 403
        assert (
            analyst.post(
                "/api/v1/model/predict",
                json={"observations": [vec]},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )
        assert analyst.get("/api/v1/data/summary").status_code == 403
        assert analyst.get("/api/v1/users").status_code == 403
        assert analyst.get("/api/v1/audit-logs").status_code == 403

    # AUDITOR
    with TestClient(app) as auditor:
        csrf = _login(auditor, "auditor_user", "AuditorPassword!123")
        assert auditor.get("/api/v1/dashboard/summary").status_code == 200
        assert auditor.get("/api/v1/employees").status_code == 200
        assert auditor.get("/api/v1/alerts").status_code == 200
        assert auditor.get("/api/v1/model/info").status_code == 200
        assert auditor.get("/api/v1/model/metrics").status_code == 200
        assert auditor.get("/api/v1/data/summary").status_code == 200
        assert auditor.get("/api/v1/audit-logs").status_code == 200
        assert (
            auditor.patch(
                "/api/v1/alerts/1/status",
                json={"new_status": "RESOLVED", "analyst_note": "Auditor attempt"},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )
        assert (
            auditor.post(
                "/api/v1/model/predict",
                json={"observations": [vec]},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )
        assert auditor.get("/api/v1/users").status_code == 403

    # ADMINISTRATOR + investigation actor attribution check
    with TestClient(app) as admin:
        csrf = _login(admin, "admin_user", "AdminPassword!123")
        assert admin.get("/api/v1/users").status_code == 200
        assert admin.get("/api/v1/audit-logs").status_code == 200
        assert (
            admin.post(
                "/api/v1/model/predict",
                json={"observations": [vec]},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 200
        )

        hist = admin.get("/api/v1/alerts/1/history").json()
        assert len(hist["items"]) == 1
        assert hist["items"][0]["actor_username"] == "analyst_user"
        assert hist["items"][0]["actor_display_name"] == "SOC Analyst"


def test_user_management_and_last_admin_protection(tmp_path: Path) -> None:
    db_path = tmp_path / "users_test.db"
    _seed_phase6_db(db_path)
    app = create_app(
        db_path=db_path,
        model_bundle_path=MODEL_BUNDLE_PATH,
        val_ref_path=VALIDATION_SCORE_REF_PATH,
    )

    with TestClient(app) as admin_client, TestClient(app) as user_client:
        admin_csrf = _login(admin_client, "admin_user", "AdminPassword!123")
        admin_id = admin_client.get("/api/v1/auth/me").json()["user"]["user_id"]

        # Create new analyst
        created = admin_client.post(
            "/api/v1/users",
            json={
                "username": "new_analyst",
                "display_name": "New Analyst",
                "password": "NewAnalyst!2026",
                "role": "SECURITY_ANALYST",
            },
            headers={"X-CSRF-Token": admin_csrf},
        )
        assert created.status_code == 201
        new_id = created.json()["user_id"]

        # Duplicate username -> 409
        dup = admin_client.post(
            "/api/v1/users",
            json={
                "username": "new_analyst",
                "display_name": "Dup",
                "password": "NewAnalyst!2026",
                "role": "AUDITOR",
            },
            headers={"X-CSRF-Token": admin_csrf},
        )
        assert dup.status_code == 409

        # Admin cannot deactivate or demote self / last active admin
        assert (
            admin_client.patch(
                f"/api/v1/users/{admin_id}",
                json={"is_active": False},
                headers={"X-CSRF-Token": admin_csrf},
            ).status_code
            == 409
        )
        assert (
            admin_client.patch(
                f"/api/v1/users/{admin_id}",
                json={"role": "AUDITOR"},
                headers={"X-CSRF-Token": admin_csrf},
            ).status_code
            == 409
        )

        # Log in as new_analyst, then deactivate -> session revoked immediately
        _login(user_client, "new_analyst", "NewAnalyst!2026")
        assert user_client.get("/api/v1/auth/me").status_code == 200

        deact = admin_client.patch(
            f"/api/v1/users/{new_id}",
            json={"is_active": False},
            headers={"X-CSRF-Token": admin_csrf},
        )
        assert deact.status_code == 200
        assert user_client.get("/api/v1/auth/me").status_code == 401


def test_schema_migration_idempotency(tmp_path: Path) -> None:
    """Running init_database twice preserves rows and adds actor_user_id cleanly."""
    db_path = tmp_path / "migrate.db"
    init_database(db_path)
    init_database(db_path)

    with get_db_connection(db_path) as conn:
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(investigation_history)").fetchall()
        }
        assert "actor_user_id" in cols
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {"users", "sessions", "security_audit_logs"}.issubset(tables)
