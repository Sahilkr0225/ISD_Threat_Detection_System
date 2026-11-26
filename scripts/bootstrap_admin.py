"""Interactive CLI script to bootstrap an initial ADMINISTRATOR account.

Uses hidden password input (getpass), Argon2id hashing, and additive schema
initialization without modifying any existing operational records.
"""

from __future__ import annotations

import getpass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import DATABASE_PATH
from backend.app.core.security import PasswordPolicyError
from backend.app.database.auth_repository import (
    AuthRepositoryError,
    DuplicateUsernameError,
    create_user,
)
from backend.app.database.connection import get_db_connection
from backend.app.database.schema import init_database


def main() -> None:
    print("=== ISD Threat Detection System — Initial Administrator Bootstrap ===")
    init_database(DATABASE_PATH)

    username = input("Administrator username (3-64 chars): ").strip()
    display_name = input("Administrator display name: ").strip()
    password = getpass.getpass("Password (min 12 chars, hidden): ")
    confirm = getpass.getpass("Confirm password (hidden): ")

    if password != confirm:
        print("Error: Passwords do not match.")
        sys.exit(1)

    try:
        with get_db_connection(DATABASE_PATH) as conn:
            user = create_user(
                conn,
                username=username,
                display_name=display_name,
                password=password,
                role="ADMINISTRATOR",
                actor_user_id=None,
                audit_action="ADMIN_BOOTSTRAPPED",
            )
    except (PasswordPolicyError, DuplicateUsernameError, AuthRepositoryError) as exc:
        print(f"Bootstrap failed: {exc}")
        sys.exit(1)

    print(f"Created ADMINISTRATOR account: username='{user['username']}', user_id={user['user_id']}")
    print("Operational records and existing investigation history were not modified.")


if __name__ == "__main__":
    main()

