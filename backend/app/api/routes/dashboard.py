"""Dashboard aggregation and trend endpoints."""

from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_db
from backend.app.database.repository import get_dashboard_summary, get_dashboard_trends
from backend.app.schemas.api_schemas import (
    DashboardSummaryResponse,
    DashboardTrendsResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def read_dashboard_summary(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Return database-backed dashboard KPIs, priority breakdown, and top employees."""
    return get_dashboard_summary(conn)


@router.get("/trends", response_model=DashboardTrendsResponse)
def read_dashboard_trends(
    date_from: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Return chronological daily observation and flagged-alert trends."""
    return {"items": get_dashboard_trends(conn, date_from=date_from, date_to=date_to)}

