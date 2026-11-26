"""SQLite schema initialization for employees, observations, alerts, explanations, and history."""

from __future__ import annotations

from pathlib import Path
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

CREATE TABLE IF NOT EXISTS investigation_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    previous_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    analyst_note TEXT,
    changed_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
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
"""


def init_database(db_path: Union[str, Path] = DATABASE_PATH) -> Path:
    """Create SQLite database tables and indexes idempotently."""
    path = Path(db_path)
    with get_db_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)
    return path

