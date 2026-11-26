"""FastAPI dependency providers including session auth, CSRF, and RBAC."""

from __future__ import annotations

from pathlib import Path
import secrets
import sqlite3
from typing import Any, Callable, Dict, Iterator

from fastapi import Depends, HTTPException, Request, status

from backend.app.core.config import (
    CORS_ORIGINS,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
)
from backend.app.database.auth_repository import (
    get_active_session_user,
    record_audit_log,
)
from backend.app.database.connection import get_db_connection
from backend.app.ml.predictor import ModelPredictor
from backend.app.risk.scoring import PriorityClassifier, RiskScorer


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection bound to the configured application database path."""
    db_path: Path = request.app.state.db_path
    with get_db_connection(db_path) as conn:
        yield conn


def get_predictor(request: Request) -> ModelPredictor:
    return request.app.state.predictor


def get_risk_scorer(request: Request) -> RiskScorer:
    return request.app.state.risk_scorer


def get_priority_classifier(request: Request) -> PriorityClassifier:
    return request.app.state.priority_classifier


def get_current_user(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Authenticate the request via HttpOnly session cookie."""
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user = get_active_session_user(conn, raw_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid, expired, or revoked.",
        )
    return user


def require_csrf(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    """Enforce CSRF token and trusted Origin validation on state-changing requests."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    origin = request.headers.get("origin")
    if origin and origin not in CORS_ORIGINS:
        record_audit_log(
            conn,
            actor_user_id=current_user["user_id"],
            action="CSRF_REJECTED",
            resource_type="request",
            resource_id=request.url.path,
            outcome="FAILURE",
            details=f"untrusted origin={origin}",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted request origin.",
        )

    cookie_csrf = request.cookies.get(CSRF_COOKIE_NAME)
    header_csrf = request.headers.get(CSRF_HEADER_NAME)
    if (
        not cookie_csrf
        or not header_csrf
        or not secrets.compare_digest(cookie_csrf, header_csrf)
    ):
        record_audit_log(
            conn,
            actor_user_id=current_user["user_id"],
            action="CSRF_REJECTED",
            resource_type="request",
            resource_id=request.url.path,
            outcome="FAILURE",
            details="missing or mismatched CSRF token",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed.",
        )


def require_roles(*allowed_roles: str) -> Callable[..., Dict[str, Any]]:
    """Dependency factory enforcing backend Role-Based Access Control (HTTP 403)."""

    def _role_checker(
        request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
        conn: sqlite3.Connection = Depends(get_db),
    ) -> Dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            record_audit_log(
                conn,
                actor_user_id=current_user["user_id"],
                action="ACCESS_DENIED",
                resource_type="endpoint",
                resource_id=f"{request.method} {request.url.path}",
                outcome="DENIED",
                details=f"role={current_user['role']}, required={list(allowed_roles)}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this resource.",
            )
        return current_user

    return _role_checker
