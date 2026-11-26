"""Parameterized SQLite repository operations for alerts, employees, and dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_STATUSES = ("OPEN", "UNDER_REVIEW", "RESOLVED", "DISMISSED")

ALLOWED_STATUS_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "OPEN": ("UNDER_REVIEW", "RESOLVED", "DISMISSED"),
    "UNDER_REVIEW": ("OPEN", "RESOLVED", "DISMISSED"),
    "RESOLVED": ("UNDER_REVIEW", "OPEN"),
    "DISMISSED": ("UNDER_REVIEW", "OPEN"),
}


class InvalidStatusTransitionError(ValueError):
    """Raised when an alert status update violates allowed workflow transitions."""


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_dashboard_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Compute database-backed dashboard summary aggregates."""
    emp_count = int(conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0])

    obs_row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_observations,
            SUM(CASE WHEN priority != 'Informational' THEN 1 ELSE 0 END) AS flagged_observations,
            MIN(activity_date) AS date_min,
            MAX(activity_date) AS date_max,
            MAX(model_version) AS model_version
        FROM employee_observations
        """
    ).fetchone()

    status_rows = conn.execute(
        "SELECT status, COUNT(*) AS cnt FROM alerts GROUP BY status"
    ).fetchall()
    status_counts = {s: 0 for s in ALLOWED_STATUSES}
    for r in status_rows:
        status_counts[str(r["status"])] = int(r["cnt"])

    critical_open_alerts = int(
        conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE priority = 'Critical' AND status = 'OPEN'"
        ).fetchone()[0]
    )

    prio_rows = conn.execute(
        "SELECT priority, COUNT(*) AS cnt FROM alerts GROUP BY priority"
    ).fetchall()
    priority_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in prio_rows:
        priority_counts[str(r["priority"])] = int(r["cnt"])

    top_emp_rows = conn.execute(
        """
        SELECT
            a.employee_id,
            e.role,
            e.department,
            COUNT(*) AS alert_count,
            MAX(a.risk_score) AS max_risk_score,
            MAX(a.anomaly_score) AS max_anomaly_score
        FROM alerts a
        JOIN employees e ON e.employee_id = a.employee_id
        GROUP BY a.employee_id
        ORDER BY max_anomaly_score DESC, alert_count DESC
        LIMIT 10
        """
    ).fetchall()

    recent_inv_rows = conn.execute(
        """
        SELECT
            h.history_id,
            h.alert_id,
            a.employee_id,
            h.previous_status,
            h.new_status,
            h.analyst_note,
            h.changed_at
        FROM investigation_history h
        JOIN alerts a ON a.alert_id = h.alert_id
        ORDER BY h.history_id DESC
        LIMIT 10
        """
    ).fetchall()

    return {
        "unique_employees": emp_count,
        "total_observations": int(obs_row["total_observations"] or 0),
        "flagged_observations": int(obs_row["flagged_observations"] or 0),
        "total_alerts": sum(status_counts.values()),
        "open_alerts": status_counts["OPEN"],
        "critical_open_alerts": critical_open_alerts,
        "under_review_alerts": status_counts["UNDER_REVIEW"],
        "resolved_alerts": status_counts["RESOLVED"],
        "dismissed_alerts": status_counts["DISMISSED"],
        "alerts_by_priority": priority_counts,
        "top_employees": [dict(r) for r in top_emp_rows],
        "recent_investigations": [dict(r) for r in recent_inv_rows],
        "model_version": obs_row["model_version"] or "isolation_forest_v1",
        "coverage_start_date": obs_row["date_min"],
        "coverage_end_date": obs_row["date_max"],
    }


def get_dashboard_trends(
    conn: sqlite3.Connection,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return daily observation and alert counts ordered chronologically."""
    clauses: List[str] = []
    params: List[Any] = []
    if date_from:
        clauses.append("o.activity_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("o.activity_date <= ?")
        params.append(date_to)

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""
        SELECT
            o.activity_date,
            COUNT(*) AS total_observations,
            SUM(CASE WHEN o.priority != 'Informational' THEN 1 ELSE 0 END) AS flagged_count,
            SUM(CASE WHEN o.priority IN ('Critical', 'High') THEN 1 ELSE 0 END) AS high_critical_count,
            ROUND(AVG(o.risk_score), 2) AS avg_risk_score
        FROM employee_observations o
        {where_sql}
        GROUP BY o.activity_date
        ORDER BY o.activity_date ASC
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def list_employees(
    conn: sqlite3.Connection,
    department: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    """Paginated employee directory with aggregated observation and alert summaries."""
    clauses: List[str] = []
    params: List[Any] = []
    if department:
        clauses.append("e.department = ?")
        params.append(department)
    if search:
        clauses.append("e.employee_id LIKE ?")
        params.append(f"%{search.strip()}%")

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = int(
        conn.execute(f"SELECT COUNT(*) FROM employees e {where_sql}", params).fetchone()[0]
    )

    offset = (page - 1) * page_size
    rows = conn.execute(
        f"""
        SELECT
            e.employee_id,
            e.role,
            e.department,
            e.functional_unit,
            e.first_activity_date,
            e.last_activity_date,
            COUNT(o.observation_id) AS observation_count,
            COALESCE(MAX(o.risk_score), 0.0) AS max_risk_score,
            CASE MAX(
                CASE o.priority
                    WHEN 'Critical' THEN 4
                    WHEN 'High' THEN 3
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 1
                    ELSE 0
                END
            )
                WHEN 4 THEN 'Critical'
                WHEN 3 THEN 'High'
                WHEN 2 THEN 'Medium'
                WHEN 1 THEN 'Low'
                ELSE 'Informational'
            END AS highest_priority,
            SUM(CASE WHEN a.alert_id IS NOT NULL THEN 1 ELSE 0 END) AS alert_count,
            SUM(CASE WHEN a.status = 'OPEN' THEN 1 ELSE 0 END) AS open_alert_count
        FROM employees e
        LEFT JOIN employee_observations o ON o.employee_id = e.employee_id
        LEFT JOIN alerts a ON a.observation_id = o.observation_id
        {where_sql}
        GROUP BY e.employee_id
        ORDER BY max_risk_score DESC, e.employee_id ASC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def get_employee_detail(conn: sqlite3.Connection, employee_id: str) -> Optional[Dict[str, Any]]:
    """Return employee profile and aggregated risk/alert statistics."""
    row = conn.execute(
        """
        SELECT
            e.employee_id,
            e.role,
            e.department,
            e.functional_unit,
            e.first_activity_date,
            e.last_activity_date,
            COUNT(o.observation_id) AS observation_count,
            COALESCE(AVG(o.risk_score), 0.0) AS avg_risk_score,
            COALESCE(MAX(o.risk_score), 0.0) AS max_risk_score,
            SUM(CASE WHEN a.alert_id IS NOT NULL THEN 1 ELSE 0 END) AS alert_count,
            SUM(CASE WHEN a.status = 'OPEN' THEN 1 ELSE 0 END) AS open_alert_count
        FROM employees e
        LEFT JOIN employee_observations o ON o.employee_id = e.employee_id
        LEFT JOIN alerts a ON a.observation_id = o.observation_id
        WHERE e.employee_id = ?
        GROUP BY e.employee_id
        """,
        (employee_id,),
    ).fetchone()
    return dict(row) if row else None


def get_employee_history(
    conn: sqlite3.Connection,
    employee_id: str,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    """Return chronological behavioural observations for a single employee."""
    total = int(
        conn.execute(
            "SELECT COUNT(*) FROM employee_observations WHERE employee_id = ?",
            (employee_id,),
        ).fetchone()[0]
    )
    offset = (page - 1) * page_size
    rows = conn.execute(
        """
        SELECT
            o.observation_id,
            o.employee_id,
            o.activity_date,
            o.login_count,
            o.after_hours_login_count,
            o.http_activity_count,
            o.email_activity_count,
            o.file_activity_count,
            o.usb_activity_count,
            o.total_activity_count,
            o.after_hours_ratio,
            o.is_weekend,
            o.anomaly_score,
            o.risk_score,
            o.priority,
            a.alert_id,
            a.status AS alert_status
        FROM employee_observations o
        LEFT JOIN alerts a ON a.observation_id = o.observation_id
        WHERE o.employee_id = ?
        ORDER BY o.activity_date DESC
        LIMIT ? OFFSET ?
        """,
        (employee_id, page_size, offset),
    ).fetchall()
    return [dict(r) for r in rows], total


def list_anomalies(
    conn: sqlite3.Connection,
    priority: Optional[str] = None,
    employee_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    """List flagged employee-day observations (priority != Informational)."""
    clauses = ["o.priority != 'Informational'"]
    params: List[Any] = []
    if priority:
        clauses.append("o.priority = ?")
        params.append(priority)
    if employee_id:
        clauses.append("o.employee_id = ?")
        params.append(employee_id)
    if date_from:
        clauses.append("o.activity_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("o.activity_date <= ?")
        params.append(date_to)

    where_sql = "WHERE " + " AND ".join(clauses)
    total = int(
        conn.execute(
            f"SELECT COUNT(*) FROM employee_observations o {where_sql}", params
        ).fetchone()[0]
    )
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"""
        SELECT
            o.observation_id,
            o.employee_id,
            o.activity_date,
            o.login_count,
            o.after_hours_login_count,
            o.http_activity_count,
            o.email_activity_count,
            o.file_activity_count,
            o.usb_activity_count,
            o.total_activity_count,
            o.anomaly_score,
            o.risk_score,
            o.priority,
            a.alert_id,
            a.status AS alert_status
        FROM employee_observations o
        LEFT JOIN alerts a ON a.observation_id = o.observation_id
        {where_sql}
        ORDER BY o.anomaly_score DESC, o.activity_date DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def list_alerts(
    conn: sqlite3.Connection,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "anomaly_score",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    """List alerts with filtering, sorting, and pagination."""
    clauses: List[str] = []
    params: List[Any] = []
    if priority:
        clauses.append("a.priority = ?")
        params.append(priority)
    if status:
        clauses.append("a.status = ?")
        params.append(status)
    if employee_id:
        clauses.append("a.employee_id = ?")
        params.append(employee_id)
    if date_from:
        clauses.append("o.activity_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("o.activity_date <= ?")
        params.append(date_to)

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sort_col = "o.activity_date" if sort_by == "activity_date" else "a.anomaly_score"
    order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

    total = int(
        conn.execute(
            f"""
            SELECT COUNT(*)
            FROM alerts a
            JOIN employee_observations o ON o.observation_id = a.observation_id
            {where_sql}
            """,
            params,
        ).fetchone()[0]
    )

    offset = (page - 1) * page_size
    rows = conn.execute(
        f"""
        SELECT
            a.alert_id,
            a.observation_id,
            a.employee_id,
            e.role,
            e.department,
            o.activity_date,
            a.anomaly_score,
            a.risk_score,
            a.priority,
            a.status,
            a.model_version,
            (
                SELECT ae.evidence_description
                FROM alert_explanations ae
                WHERE ae.alert_id = a.alert_id
                ORDER BY ABS(COALESCE(ae.deviation, 0.0)) DESC, ae.explanation_id ASC
                LIMIT 1
            ) AS activity_summary,
            a.created_at,
            a.updated_at
        FROM alerts a
        JOIN employee_observations o ON o.observation_id = a.observation_id
        JOIN employees e ON e.employee_id = a.employee_id
        {where_sql}
        ORDER BY {sort_col} {order_dir}, a.alert_id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def get_alert_detail(conn: sqlite3.Connection, alert_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve alert with employee metadata, observation counts, and causal explanations."""
    row = conn.execute(
        """
        SELECT
            a.alert_id,
            a.observation_id,
            a.employee_id,
            e.role,
            e.department,
            e.functional_unit,
            o.activity_date,
            o.login_count,
            o.after_hours_login_count,
            o.http_activity_count,
            o.email_activity_count,
            o.file_activity_count,
            o.usb_activity_count,
            o.total_activity_count,
            o.after_hours_ratio,
            o.is_weekend,
            a.anomaly_score,
            a.risk_score,
            a.priority,
            a.status,
            a.model_version,
            (
                SELECT ae.evidence_description
                FROM alert_explanations ae
                WHERE ae.alert_id = a.alert_id
                ORDER BY ABS(COALESCE(ae.deviation, 0.0)) DESC, ae.explanation_id ASC
                LIMIT 1
            ) AS activity_summary,
            a.created_at,
            a.updated_at
        FROM alerts a
        JOIN employee_observations o ON o.observation_id = a.observation_id
        JOIN employees e ON e.employee_id = a.employee_id
        WHERE a.alert_id = ?
        """,
        (alert_id,),
    ).fetchone()
    if not row:
        return None

    exps = conn.execute(
        """
        SELECT
            explanation_id,
            feature_name,
            activity_label,
            current_value,
            historical_mean,
            historical_std,
            deviation,
            direction,
            historical_obs_count,
            evidence_description,
            investigation_recommendation
        FROM alert_explanations
        WHERE alert_id = ?
        ORDER BY ABS(COALESCE(deviation, 0.0)) DESC, explanation_id ASC
        """,
        (alert_id,),
    ).fetchall()

    result = dict(row)
    result["explanations"] = [dict(e) for e in exps]
    return result


def get_alert_history(conn: sqlite3.Connection, alert_id: int) -> Optional[List[Dict[str, Any]]]:
    """Retrieve investigation audit trail for an alert (None if alert does not exist)."""
    exists = conn.execute("SELECT 1 FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
    if not exists:
        return None
    rows = conn.execute(
        """
        SELECT history_id, alert_id, previous_status, new_status, analyst_note, changed_at
        FROM investigation_history
        WHERE alert_id = ?
        ORDER BY history_id DESC
        """,
        (alert_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def update_alert_status(
    conn: sqlite3.Connection,
    alert_id: int,
    new_status: str,
    analyst_note: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Validate and apply an alert status transition, recording investigation history."""
    if new_status not in ALLOWED_STATUSES:
        raise InvalidStatusTransitionError(
            f"Unsupported status '{new_status}'. Allowed: {ALLOWED_STATUSES}"
        )

    row = conn.execute(
        "SELECT alert_id, status FROM alerts WHERE alert_id = ?",
        (alert_id,),
    ).fetchone()
    if not row:
        return None

    prev_status = str(row["status"])
    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(prev_status, ())
    if new_status not in allowed_next:
        raise InvalidStatusTransitionError(
            f"Invalid transition from '{prev_status}' to '{new_status}'. Allowed: {allowed_next}"
        )

    now = utc_now_iso()
    conn.execute(
        "UPDATE alerts SET status = ?, updated_at = ? WHERE alert_id = ?",
        (new_status, now, alert_id),
    )
    conn.execute(
        """
        INSERT INTO investigation_history (alert_id, previous_status, new_status, analyst_note, changed_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (alert_id, prev_status, new_status, analyst_note, now),
    )
    return get_alert_detail(conn, alert_id)


def get_data_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Return imported dataset coverage and table counts."""
    emp_cnt = int(conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0])
    obs_row = conn.execute(
        """
        SELECT
            COUNT(*) AS obs_count,
            COUNT(DISTINCT activity_date) AS unique_dates,
            MIN(activity_date) AS min_date,
            MAX(activity_date) AS max_date
        FROM employee_observations
        """
    ).fetchone()
    alert_cnt = int(conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0])
    exp_cnt = int(conn.execute("SELECT COUNT(*) FROM alert_explanations").fetchone()[0])
    hist_cnt = int(conn.execute("SELECT COUNT(*) FROM investigation_history").fetchone()[0])

    return {
        "source_partition": "held_out_test_partition",
        "unique_employees": emp_cnt,
        "observation_count": int(obs_row["obs_count"] or 0),
        "unique_dates": int(obs_row["unique_dates"] or 0),
        "date_min": obs_row["min_date"],
        "date_max": obs_row["max_date"],
        "alert_count": alert_cnt,
        "explanation_count": exp_cnt,
        "investigation_history_count": hist_cnt,
    }

