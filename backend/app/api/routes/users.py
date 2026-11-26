"""Administrator-only user management endpoints."""

from __future__ import annotations

import math
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_db, require_csrf, require_roles
from backend.app.core.security import PasswordPolicyError
from backend.app.database.auth_repository import (
    AuthRepositoryError,
    DuplicateUsernameError,
    LastAdminProtectionError,
    create_user,
    get_user_by_id,
    list_users,
    reset_user_password,
    update_user,
)
from backend.app.schemas.api_schemas import (
    CreateUserRequest,
    ResetPasswordRequest,
    RoleLiteral,
    UpdateUserRequest,
    UserListResponse,
    UserPublic,
)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=UserListResponse)
def read_users(
    role: Optional[RoleLiteral] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(require_roles("ADMINISTRATOR")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """List user accounts (ADMINISTRATOR only)."""
    items, total = list_users(conn, role=role, is_active=is_active, page=page, page_size=page_size)
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, math.ceil(total / page_size)),
        },
    }


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_user_account(
    payload: CreateUserRequest,
    admin: Dict[str, Any] = Depends(require_roles("ADMINISTRATOR")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Create a new user account (ADMINISTRATOR only)."""
    try:
        return create_user(
            conn,
            username=payload.username,
            display_name=payload.display_name,
            password=payload.password,
            role=payload.role,
            actor_user_id=admin["user_id"],
        )
    except DuplicateUsernameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (PasswordPolicyError, AuthRepositoryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/{user_id}", response_model=UserPublic)
def read_user_detail(
    user_id: int,
    _admin: Dict[str, Any] = Depends(require_roles("ADMINISTRATOR")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Retrieve user details (ADMINISTRATOR only)."""
    user = get_user_by_id(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.patch("/{user_id}", response_model=UserPublic, dependencies=[Depends(require_csrf)])
def patch_user_account(
    user_id: int,
    payload: UpdateUserRequest,
    admin: Dict[str, Any] = Depends(require_roles("ADMINISTRATOR")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Update display name, role, or active status (ADMINISTRATOR only)."""
    try:
        updated = update_user(
            conn,
            target_user_id=user_id,
            actor_user_id=admin["user_id"],
            display_name=payload.display_name,
            role=payload.role,
            is_active=payload.is_active,
        )
    except LastAdminProtectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except AuthRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return updated


@router.post("/{user_id}/reset-password", response_model=UserPublic, dependencies=[Depends(require_csrf)])
def admin_reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    admin: Dict[str, Any] = Depends(require_roles("ADMINISTRATOR")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Reset a user's password and revoke their active sessions (ADMINISTRATOR only)."""
    try:
        updated = reset_user_password(
            conn,
            target_user_id=user_id,
            new_password=payload.new_password,
            actor_user_id=admin["user_id"],
        )
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return updated

