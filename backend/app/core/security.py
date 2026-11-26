"""Password hashing (Argon2id), opaque token generation, and login rate limiting."""

from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import secrets
import threading
import time
from typing import Deque, Dict, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from backend.app.core.config import (
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    LOGIN_RATE_LIMIT_WINDOW_SEC,
)

VALID_ROLES: Tuple[str, ...] = (
    "ADMINISTRATOR",
    "SECURITY_ANALYST",
    "AUDITOR",
)

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

_password_hasher = PasswordHasher()


class PasswordPolicyError(ValueError):
    """Raised when a password fails minimum complexity/length policy."""


def normalize_username(username: str) -> str:
    """Normalize usernames consistently (trimmed, lowercase)."""
    return username.strip().lower()


def validate_password_policy(password: str) -> None:
    """Enforce minimum password length (12 chars) and non-blank content."""
    if not isinstance(password, str) or not password.strip():
        raise PasswordPolicyError("Password must not be empty.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must not exceed {MAX_PASSWORD_LENGTH} characters."
        )


def hash_password(password: str) -> str:
    """Hash a password using Argon2id with a library-generated salt."""
    validate_password_policy(password)
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    if not password or not password_hash:
        return False
    try:
        return bool(_password_hasher.verify(password_hash, password))
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_opaque_token() -> str:
    """Generate a cryptographically secure random URL-safe token."""
    return secrets.token_urlsafe(32)


def hash_session_token(raw_token: str) -> str:
    """Hash a raw session token with SHA-256 before database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class LoginRateLimiter:
    """Process-local sliding-window rate limiter for failed login attempts.

    Limitation: State is held in process memory; in multi-worker deployments
    each worker maintains an independent counter.
    """

    def __init__(
        self,
        max_attempts: int = LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds: int = LOGIN_RATE_LIMIT_WINDOW_SEC,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> Deque[float]:
        q = self._failures[key]
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def is_throttled(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            return len(q) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            q.append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_rate_limiter = LoginRateLimiter()

