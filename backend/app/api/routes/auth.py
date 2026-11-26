"""Authentication, session management, CSRF, and password change endpoints."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.app.api.deps import get_current_user, get_db, require_csrf
from backend.app.core.config import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    SESSION_TTL_HOURS,
)
from backend.app.core.security import (
    PasswordPolicyError,
    generate_opaque_token,
    login_rate_limiter,
    normalize_username,
)
from backend.app.database.auth_repository import (
    AuthRepositoryError,
    authenticate_user_and_create_session,
    change_own_password,
    record_audit_log,
    revoke_session_by_raw_token,
)
from backend.app.schemas.api_schemas import (
    ChangePasswordRequest,
    CsrfResponse,
    LoginRequest,
    LoginResponse,
    SessionMeResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(response: Response, raw_session_token: str, csrf_token: str) -> None:
    max_age = SESSION_TTL_HOURS * 3600
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_session_token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


@router.get("/csrf", response_model=CsrfResponse)
def get_csrf_token(request: Request, response: Response) -> dict:
    """Issue or return a CSRF token cookie for state-changing requests."""
    token = request.cookies.get(CSRF_COOKIE_NAME) or generate_opaque_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )
    return {"csrf_token": token}


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Authenticate user with Argon2id, issue HttpOnly session cookie and CSRF token."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{normalize_username(payload.username)}"

    if login_rate_limiter.is_throttled(rate_key):
        record_audit_log(
            conn,
            actor_user_id=None,
            action="LOGIN_THROTTLED",
            resource_type="session",
            resource_id=None,
            outcome="DENIED",
            details=f"username={normalize_username(payload.username)}",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait a minute before trying again.",
        )

    auth_result = authenticate_user_and_create_session(
        conn,
        username=payload.username,
        password=payload.password,
        ttl_hours=SESSION_TTL_HOURS,
    )
    if not auth_result:
        login_rate_limiter.record_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    login_rate_limiter.clear(rate_key)
    user, raw_session_token, expires_at = auth_result
    csrf_token = generate_opaque_token()
    _set_auth_cookies(response, raw_session_token, csrf_token)

    return {
        "user": user,
        "csrf_token": csrf_token,
        "expires_at": expires_at,
    }


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(
    request: Request,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Revoke server-side session and clear authentication cookies."""
    raw_token = request.cookies.get(SESSION_COOKIE_NAME, "")
    revoke_session_by_raw_token(conn, raw_token, actor_user_id=current_user["user_id"])
    _clear_auth_cookies(response)
    return {"status": "logged_out"}


@router.get("/me", response_model=SessionMeResponse)
def read_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> dict:
    """Return currently authenticated user profile and session expiration."""
    return {
        "user": current_user,
        "session_expires_at": current_user["session_expires_at"],
    }


@router.post("/change-password", dependencies=[Depends(require_csrf)])
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Change current user's password and revoke active sessions."""
    try:
        change_own_password(
            conn,
            user_id=current_user["user_id"],
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except (PasswordPolicyError, AuthRepositoryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    _clear_auth_cookies(response)
    return {"status": "password_changed"}

