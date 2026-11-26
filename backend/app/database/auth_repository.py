"""SQLite repository for users, sessions, and security audit logs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import SESSION_TTL_HOURS
from backend.app.core.security import (
    VALID_ROLES,
    generate_opaque_token,
    hash_password,
    hash_session_token,
    normalize_username,
    verify_password,
)
from backend.app.database.repository import utc_now_iso


class AuthRepositoryError(ValueError):
    """Base error for user management and authentication business rules."""


class DuplicateUsernameError(AuthRepositoryError):
    """Raised when creating a user with an already existing normalized username."""


class LastAdminProtectionError(AuthRepositoryError):
    """Raised when an operation would remove or deactivate the last active administrator."""


def _user_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a users table row into a safe dict (never including password_hash)."""
    return {
        "user_id": int(row["user_id"]),
        "username": str(row["username"]),
        "display_name": str(row["display_name"]),
        "role": str(row["role"]),
        "is_active": bool(row["is_active"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "last_login_at": str(row["last_login_at"]) if row["last_login_at"] else None,
    }


def record_audit_log(
    conn: sqlite3.Connection,
    *,
    actor_user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    outcome: str = "SUCCESS",
    details: Optional[str] = None,
) -> None:
    """Append an immutable security audit log entry."""
    conn.execute(
        """
        INSERT INTO security_audit_logs (
            actor_user_id, action, resource_type, resource_id, outcome, timestamp, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            actor_user_id,
            action,
            resource_type,
            resource_id,
            outcome,
            utc_now_iso(),
            details,
        ),
    )
    conn.commit()


def create_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    display_name: str,
    password: str,
    role: str,
    actor_user_id: Optional[int] = None,
    audit_action: str = "USER_CREATED",
) -> Dict[str, Any]:
    """Create a new user with normalized username, valid role, and Argon2id hash."""
    norm_user = normalize_username(username)
    clean_display = display_name.strip()
    if not norm_user or len(norm_user) < 3 or len(norm_user) > 64:
        raise AuthRepositoryError("Username must be between 3 and 64 characters.")
    if not clean_display:
        raise AuthRepositoryError("Display name must not be empty.")
    if role not in VALID_ROLES:
        raise AuthRepositoryError(f"Invalid role '{role}'. Must be one of: {VALID_ROLES}")

    existing = conn.execute(
        "SELECT 1 FROM users WHERE username = ?", (norm_user,)
    ).fetchone()
    if existing:
        raise DuplicateUsernameError(f"Username '{norm_user}' already exists.")

    pw_hash = hash_password(password)
    now = utc_now_iso()
    cur = conn.execute(
        """
        INSERT INTO users (
            username, display_name, password_hash, role, is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (norm_user, clean_display, pw_hash, role, now, now),
    )
    new_user_id = int(cur.lastrowid)
    record_audit_log(
        conn,
        actor_user_id=actor_user_id,
        action=audit_action,
        resource_type="user",
        resource_id=str(new_user_id),
        outcome="SUCCESS",
        details=f"username={norm_user}, role={role}",
    )
    return get_user_by_id(conn, new_user_id)  # type: ignore[return-value]


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT user_id, username, display_name, role, is_active, created_at, updated_at, last_login_at
        FROM users WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    return _user_row_to_dict(row) if row else None


def list_users(
    conn: sqlite3.Connection,
    *,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    clauses: List[str] = []
    params: List[Any] = []
    if role:
        clauses.append("role = ?")
        params.append(role)
    if is_active is not None:
        clauses.append("is_active = ?")
        params.append(1 if is_active else 0)

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = int(
        conn.execute(f"SELECT COUNT(*) FROM users {where_sql}", params).fetchone()[0]
    )
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"""
        SELECT user_id, username, display_name, role, is_active, created_at, updated_at, last_login_at
        FROM users
        {where_sql}
        ORDER BY user_id ASC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()
    return [_user_row_to_dict(r) for r in rows], total


def revoke_all_user_sessions(conn: sqlite3.Connection, user_id: int) -> int:
    now = utc_now_iso()
    cur = conn.execute(
        "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
        (now, user_id),
    )
    return int(cur.rowcount)


def _count_other_active_admins(conn: sqlite3.Connection, exclude_user_id: int) -> int:
    return int(
        conn.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE role = 'ADMINISTRATOR' AND is_active = 1 AND user_id != ?
            """,
            (exclude_user_id,),
        ).fetchone()[0]
    )


def update_user(
    conn: sqlite3.Connection,
    *,
    target_user_id: int,
    actor_user_id: int,
    display_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Update display_name, role, or is_active with last-admin & self-lockout protection."""
    row = conn.execute(
        "SELECT user_id, username, display_name, role, is_active FROM users WHERE user_id = ?",
        (target_user_id,),
    ).fetchone()
    if not row:
        return None

    curr_role = str(row["role"])
    curr_active = bool(row["is_active"])
    new_display = display_name.strip() if display_name is not None else str(row["display_name"])
    if not new_display:
        raise AuthRepositoryError("Display name must not be empty.")

    new_role = role if role is not None else curr_role
    if new_role not in VALID_ROLES:
        raise AuthRepositoryError(f"Invalid role '{new_role}'.")

    new_active = is_active if is_active is not None else curr_active

    # Self-protection & last-admin protection
    if target_user_id == actor_user_id:
        if not new_active:
            raise LastAdminProtectionError("Administrators cannot deactivate their own account.")
        if new_role != curr_role:
            raise LastAdminProtectionError("Administrators cannot change their own role.")

    if curr_role == "ADMINISTRATOR" and curr_active:
        removing_admin = (new_role != "ADMINISTRATOR") or (not new_active)
        if removing_admin and _count_other_active_admins(conn, target_user_id) == 0:
            raise LastAdminProtectionError(
                "Cannot deactivate or demote the last active administrator."
            )

    now = utc_now_iso()
    conn.execute(
        """
        UPDATE users
        SET display_name = ?, role = ?, is_active = ?, updated_at = ?
        WHERE user_id = ?
        """,
        (new_display, new_role, 1 if new_active else 0, now, target_user_id),
    )

    if new_role != curr_role:
        revoke_all_user_sessions(conn, target_user_id)
        record_audit_log(
            conn,
            actor_user_id=actor_user_id,
            action="USER_ROLE_CHANGED",
            resource_type="user",
            resource_id=str(target_user_id),
            outcome="SUCCESS",
            details=f"role: {curr_role} -> {new_role}",
        )

    if new_active != curr_active:
        if not new_active:
            revoke_all_user_sessions(conn, target_user_id)
        record_audit_log(
            conn,
            actor_user_id=actor_user_id,
            action="USER_ACTIVATED" if new_active else "USER_DEACTIVATED",
            resource_type="user",
            resource_id=str(target_user_id),
            outcome="SUCCESS",
            details=f"username={row['username']}",
        )

    if new_display != str(row["display_name"]) and new_role == curr_role and new_active == curr_active:
        record_audit_log(
            conn,
            actor_user_id=actor_user_id,
            action="USER_UPDATED",
            resource_type="user",
            resource_id=str(target_user_id),
            outcome="SUCCESS",
            details="display_name updated",
        )

    return get_user_by_id(conn, target_user_id)


def reset_user_password(
    conn: sqlite3.Connection,
    *,
    target_user_id: int,
    new_password: str,
    actor_user_id: int,
) -> Optional[Dict[str, Any]]:
    user = get_user_by_id(conn, target_user_id)
    if not user:
        return None
    pw_hash = hash_password(new_password)
    now = utc_now_iso()
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
        (pw_hash, now, target_user_id),
    )
    revoke_all_user_sessions(conn, target_user_id)
    record_audit_log(
        conn,
        actor_user_id=actor_user_id,
        action="USER_PASSWORD_RESET",
        resource_type="user",
        resource_id=str(target_user_id),
        outcome="SUCCESS",
        details=f"username={user['username']}",
    )
    return get_user_by_id(conn, target_user_id)


def change_own_password(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    current_password: str,
    new_password: str,
) -> None:
    row = conn.execute(
        "SELECT password_hash, username FROM users WHERE user_id = ? AND is_active = 1",
        (user_id,),
    ).fetchone()
    if not row or not verify_password(current_password, str(row["password_hash"])):
        record_audit_log(
            conn,
            actor_user_id=user_id,
            action="PASSWORD_CHANGE",
            resource_type="user",
            resource_id=str(user_id),
            outcome="FAILURE",
            details="invalid current password",
        )
        raise AuthRepositoryError("Current password is incorrect.")

    pw_hash = hash_password(new_password)
    now = utc_now_iso()
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
        (pw_hash, now, user_id),
    )
    revoke_all_user_sessions(conn, user_id)
    record_audit_log(
        conn,
        actor_user_id=user_id,
        action="PASSWORD_CHANGE",
        resource_type="user",
        resource_id=str(user_id),
        outcome="SUCCESS",
        details=f"username={row['username']}",
    )


def authenticate_user_and_create_session(
    conn: sqlite3.Connection,
    *,
    username: str,
    password: str,
    ttl_hours: int = SESSION_TTL_HOURS,
) -> Optional[Tuple[Dict[str, Any], str, str]]:
    """Verify credentials and issue a new opaque session token (returns None on failure)."""
    norm_user = normalize_username(username)
    row = conn.execute(
        """
        SELECT user_id, username, display_name, password_hash, role, is_active,
               created_at, updated_at, last_login_at
        FROM users WHERE username = ?
        """,
        (norm_user,),
    ).fetchone()

    if not row:
        record_audit_log(
            conn,
            actor_user_id=None,
            action="LOGIN_FAILED",
            resource_type="session",
            resource_id=None,
            outcome="FAILURE",
            details=f"username={norm_user}, reason=unknown_user",
        )
        return None

    user_id = int(row["user_id"])
    if not bool(row["is_active"]):
        record_audit_log(
            conn,
            actor_user_id=user_id,
            action="LOGIN_FAILED",
            resource_type="session",
            resource_id=None,
            outcome="FAILURE",
            details=f"username={norm_user}, reason=inactive_account",
        )
        return None

    if not verify_password(password, str(row["password_hash"])):
        record_audit_log(
            conn,
            actor_user_id=user_id,
            action="LOGIN_FAILED",
            resource_type="session",
            resource_id=None,
            outcome="FAILURE",
            details=f"username={norm_user}, reason=invalid_password",
        )
        return None

    raw_token = generate_opaque_token()
    token_hash = hash_session_token(raw_token)
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat(timespec="seconds")
    expires_iso = (now_dt + timedelta(hours=ttl_hours)).isoformat(timespec="seconds")

    conn.execute(
        """
        INSERT INTO sessions (user_id, token_hash, created_at, expires_at, revoked_at)
        VALUES (?, ?, ?, ?, NULL)
        """,
        (user_id, token_hash, now_iso, expires_iso),
    )
    conn.execute(
        "UPDATE users SET last_login_at = ? WHERE user_id = ?",
        (now_iso, user_id),
    )
    record_audit_log(
        conn,
        actor_user_id=user_id,
        action="LOGIN_SUCCESS",
        resource_type="session",
        resource_id=None,
        outcome="SUCCESS",
        details=f"username={norm_user}, role={row['role']}",
    )
    return get_user_by_id(conn, user_id), raw_token, expires_iso  # type: ignore[return-value]


def get_active_session_user(
    conn: sqlite3.Connection,
    raw_token: str,
) -> Optional[Dict[str, Any]]:
    """Validate opaque session token against DB (not revoked, not expired, active user)."""
    if not raw_token:
        return None
    token_hash = hash_session_token(raw_token)
    row = conn.execute(
        """
        SELECT
            s.session_id,
            s.expires_at,
            s.revoked_at,
            u.user_id,
            u.username,
            u.display_name,
            u.role,
            u.is_active,
            u.created_at,
            u.updated_at,
            u.last_login_at
        FROM sessions s
        JOIN users u ON u.user_id = s.user_id
        WHERE s.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()

    if not row:
        return None
    if row["revoked_at"] is not None:
        return None
    if not bool(row["is_active"]):
        return None

    now_dt = datetime.now(timezone.utc)
    exp_dt = datetime.fromisoformat(str(row["expires_at"]))
    if exp_dt <= now_dt:
        return None

    user = _user_row_to_dict(row)
    user["session_expires_at"] = str(row["expires_at"])
    return user


def revoke_session_by_raw_token(
    conn: sqlite3.Connection,
    raw_token: str,
    actor_user_id: Optional[int] = None,
) -> bool:
    if not raw_token:
        return False
    token_hash = hash_session_token(raw_token)
    now = utc_now_iso()
    cur = conn.execute(
        "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
        (now, token_hash),
    )
    if actor_user_id is not None:
        record_audit_log(
            conn,
            actor_user_id=actor_user_id,
            action="LOGOUT",
            resource_type="session",
            resource_id=None,
            outcome="SUCCESS",
            details="session revoked",
        )
    return cur.rowcount > 0


def list_audit_logs(
    conn: sqlite3.Connection,
    *,
    action: Optional[str] = None,
    outcome: Optional[str] = None,
    actor_user_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    clauses: List[str] = []
    params: List[Any] = []
    if action:
        clauses.append("l.action = ?")
        params.append(action)
    if outcome:
        clauses.append("l.outcome = ?")
        params.append(outcome)
    if actor_user_id is not None:
        clauses.append("l.actor_user_id = ?")
        params.append(actor_user_id)

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = int(
        conn.execute(
            f"SELECT COUNT(*) FROM security_audit_logs l {where_sql}", params
        ).fetchone()[0]
    )
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"""
        SELECT
            l.audit_id,
            l.actor_user_id,
            u.username AS actor_username,
            u.display_name AS actor_display_name,
            l.action,
            l.resource_type,
            l.resource_id,
            l.outcome,
            l.timestamp,
            l.details
        FROM security_audit_logs l
        LEFT JOIN users u ON u.user_id = l.actor_user_id
        {where_sql}
        ORDER BY l.audit_id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()
    return [dict(r) for r in rows], total
