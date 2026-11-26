"""SQLite persistence package."""

from backend.app.database.connection import connect_sqlite, get_db_connection
from backend.app.database.repository import (
    ALLOWED_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
    InvalidStatusTransitionError,
    get_alert_detail,
    get_alert_history,
    get_dashboard_summary,
    get_dashboard_trends,
    get_data_summary,
    get_employee_detail,
    get_employee_history,
    list_alerts,
    list_anomalies,
    list_employees,
    update_alert_status,
)
from backend.app.database.schema import init_database

__all__ = [
    "ALLOWED_STATUSES",
    "ALLOWED_STATUS_TRANSITIONS",
    "InvalidStatusTransitionError",
    "connect_sqlite",
    "get_alert_detail",
    "get_alert_history",
    "get_dashboard_summary",
    "get_dashboard_trends",
    "get_data_summary",
    "get_db_connection",
    "get_employee_detail",
    "get_employee_history",
    "init_database",
    "list_alerts",
    "list_anomalies",
    "list_employees",
    "update_alert_status",
]
