"""Read-only security audit log endpoints (ADMINISTRATOR and AUDITOR)."""

from __future__ import annotations

import math
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_db, require_roles
from backend.app.database.auth_repository import list_audit_logs
from backend.app.schemas.api_schemas import SecurityAuditLogListResponse

router = APIRouter(prefix="/audit-logs", tags=["Security Audit Logs"])


@router.get("", response_model=SecurityAuditLogListResponse)
def read_audit_logs(
    action: Optional[str] = Query(default=None, max_length=64),
    outcome: Optional[str] = Query(default=None, max_length=32),
    actor_user_id: Optional[int] = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _user: Dict[str, Any] = Depends(require_roles("ADMINISTRATOR", "AUDITOR")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """List paginated, read-only security audit log entries."""
    items, total = list_audit_logs(
        conn,
        action=action,
        outcome=outcome,
        actor_user_id=actor_user_id,
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

