"""SQLite schema initialization and additive Phase 6 auth migrations."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Union

from backend.app.core.config import DATABASE_PATH
from backend.app.database.connection import get_db_connection

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    role TEXT,
    department TEXT,
    functional_unit TEXT,
    first_activity_date TEXT NOT NULL,
    last_activity_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    activity_date TEXT NOT NULL,
    login_count INTEGER NOT NULL,
    after_hours_login_count INTEGER NOT NULL,
    http_activity_count INTEGER NOT NULL,
    email_activity_count INTEGER NOT NULL,
    file_activity_count INTEGER NOT NULL,
    usb_activity_count INTEGER NOT NULL,
    total_activity_count INTEGER NOT NULL,
    after_hours_ratio REAL NOT NULL,
    is_weekend INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    anomaly_score REAL NOT NULL,
    risk_score REAL NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    UNIQUE (employee_id, activity_date, model_version)
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL UNIQUE,
    employee_id TEXT NOT NULL,
    anomaly_score REAL NOT NULL,
    risk_score REAL NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    model_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (observation_id) REFERENCES employee_observations(observation_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alert_explanations (
    explanation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    activity_label TEXT NOT NULL,
    current_value REAL NOT NULL,
    historical_mean REAL,
    historical_std REAL,
    deviation REAL,
    direction TEXT NOT NULL,
    historical_obs_count INTEGER NOT NULL,
    evidence_description TEXT NOT NULL,
    investigation_recommendation TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE,
    UNIQUE (alert_id, feature_name)
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMINISTRATOR', 'SECURITY_ANALYST', 'AUDITOR')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS security_audit_logs (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    outcome TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY (actor_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS investigation_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    previous_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    analyst_note TEXT,
    changed_at TEXT NOT NULL,
    actor_user_id INTEGER,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE,
    FOREIGN KEY (actor_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_obs_employee_id ON employee_observations(employee_id);
CREATE INDEX IF NOT EXISTS idx_obs_activity_date ON employee_observations(activity_date);
CREATE INDEX IF NOT EXISTS idx_obs_priority ON employee_observations(priority);
CREATE INDEX IF NOT EXISTS idx_obs_anomaly_score ON employee_observations(anomaly_score DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_employee_id ON alerts(employee_id);
CREATE INDEX IF NOT EXISTS idx_alerts_priority ON alerts(priority);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_anomaly_score ON alerts(anomaly_score DESC);

CREATE INDEX IF NOT EXISTS idx_inv_history_alert_id ON investigation_history(alert_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON security_audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON security_audit_logs(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON security_audit_logs(action);
"""


def _apply_additive_migrations(conn: sqlite3.Connection) -> None:
    """Apply non-destructive, idempotent column migrations on existing tables."""
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(investigation_history)").fetchall()
    }
    if "actor_user_id" not in cols:
        conn.execute(
            "ALTER TABLE investigation_history ADD COLUMN actor_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL"
        )


def init_database(db_path: Union[str, Path] = DATABASE_PATH) -> Path:
    """Create SQLite database tables, indexes, and additive migrations idempotently."""
    path = Path(db_path)
    with get_db_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)
        _apply_additive_migrations(conn)
    return path
