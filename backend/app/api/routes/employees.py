"""Employee directory, behavioural history, and flagged anomaly endpoints."""

from __future__ import annotations

import math
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_db, require_roles
from backend.app.database.repository import (
    get_employee_detail,
    get_employee_history,
    list_anomalies,
    list_employees,
)
from backend.app.schemas.api_schemas import (
    AnomalyListResponse,
    EmployeeDetailResponse,
    EmployeeHistoryResponse,
    EmployeeListResponse,
    PriorityLiteral,
)

router = APIRouter(tags=["Employees & Anomalies"])


@router.get("/employees", response_model=EmployeeListResponse)
def read_employees(
    department: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _user: Dict[str, Any] = Depends(
        require_roles("ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR")
    ),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """List employees represented in the imported dataset with pagination."""
    items, total = list_employees(
        conn, department=department, search=search, page=page, page_size=page_size
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


@router.get("/employees/{employee_id}", response_model=EmployeeDetailResponse)
def read_employee_detail(
    employee_id: str,
    _user: Dict[str, Any] = Depends(
        require_roles("ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR")
    ),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Retrieve profile and aggregated risk metrics for a single employee."""
    emp = get_employee_detail(conn, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{employee_id}' not found.",
        )
    return emp


@router.get("/employees/{employee_id}/history", response_model=EmployeeHistoryResponse)
def read_employee_history(
    employee_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _user: Dict[str, Any] = Depends(
        require_roles("ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR")
    ),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Retrieve chronological behavioural observations for an employee."""
    if not get_employee_detail(conn, employee_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{employee_id}' not found.",
        )
    items, total = get_employee_history(conn, employee_id, page=page, page_size=page_size)
    return {
        "employee_id": employee_id,
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, math.ceil(total / page_size)),
        },
    }


@router.get("/anomalies", response_model=AnomalyListResponse)
def read_anomalies(
    priority: Optional[PriorityLiteral] = Query(default=None),
    employee_id: Optional[str] = Query(default=None, max_length=64),
    date_from: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _user: Dict[str, Any] = Depends(
        require_roles("ADMINISTRATOR", "SECURITY_ANALYST", "AUDITOR")
    ),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """List flagged observations (priority != Informational) with filtering and pagination."""
    items, total = list_anomalies(
        conn,
        priority=priority,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
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

