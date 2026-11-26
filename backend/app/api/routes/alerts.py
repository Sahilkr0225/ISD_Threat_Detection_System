"""Alert listing, detail, status workflow, and investigation history endpoints."""

from __future__ import annotations

import math
import sqlite3
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_db, require_csrf, require_roles
from backend.app.database.repository import (
    InvalidStatusTransitionError,
    get_alert_detail,
    get_alert_history,
    list_alerts,
    update_alert_status,
)
from backend.app.schemas.api_schemas import (
    AlertDetailResponse,
    AlertHistoryResponse,
    AlertListResponse,
    AlertStatusLiteral,
    AlertStatusUpdateRequest,
    PriorityLiteral,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
def read_alerts(
    priority: Optional[PriorityLiteral] = Query(default=None),
    status_filter: Optional[AlertStatusLiteral] = Query(default=None, alias="status"),
    employee_id: Optional[str] = Query(default=None, max_length=64),
    date_from: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    sort_by: Literal["anomaly_score", "activity_date"] = Query(default="anomaly_score"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _user: Dict[str, Any] = Depends(
        require_roles("ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR")
    ),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """List alerts with priority/status/employee/date filters, sorting, and pagination."""
    items, total = list_alerts(
        conn,
        priority=priority,
        status=status_filter,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, math.ceil(total / page_size)),
        },
    }


@router.get("/{alert_id}", response_model=AlertDetailResponse)
def read_alert_detail(
    alert_id: int,
    _user: Dict[str, Any] = Depends(
        require_roles("ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR")
    ),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Retrieve alert details, observation metrics, and causal behavioural explanations."""
    detail = get_alert_detail(conn, alert_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found.",
        )
    return detail


@router.patch("/{alert_id}/status", response_model=AlertDetailResponse, dependencies=[Depends(require_csrf)])
def patch_alert_status(
    alert_id: int,
    payload: AlertStatusUpdateRequest,
    user: Dict[str, Any] = Depends(require_roles("ADMINISTRATOR", "SECURITY_ANALYST")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Update alert investigation status and append an audit trail entry."""
    try:
        updated = update_alert_status(
            conn,
            alert_id=alert_id,
            new_status=payload.new_status,
            analyst_note=payload.analyst_note,
            actor_user_id=user["user_id"],
        )
    except InvalidStatusTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found.",
        )
    return updated


@router.get("/{alert_id}/history", response_model=AlertHistoryResponse)
def read_alert_history(
    alert_id: int,
    _user: Dict[str, Any] = Depends(
        require_roles("ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR")
    ),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Retrieve investigation status transition history for an alert."""
    history = get_alert_history(conn, alert_id)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found.",
        )
    return {"alert_id": alert_id, "items": history}

