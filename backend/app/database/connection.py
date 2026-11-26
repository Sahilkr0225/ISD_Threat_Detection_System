"""SQLite connection management with foreign-key enforcement."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator, Union

from backend.app.core.config import DATABASE_PATH


def connect_sqlite(db_path: Union[str, Path] = DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys and Row factory enabled."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def get_db_connection(db_path: Union[str, Path] = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a SQLite connection that commits/rolls back cleanly."""
    conn = connect_sqlite(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

