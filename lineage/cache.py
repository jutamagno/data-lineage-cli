from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

CACHE_PATH = Path.home() / ".lineage-cli" / "cache.db"


def _key(sql: str, dialect: str) -> str:
    return hashlib.sha256(f"{sql}::{dialect}".encode()).hexdigest()[:16]


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS descriptions (
            cache_key   TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            ts          TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def get_cached(sql: str, dialect: str, cache_path: Path = CACHE_PATH) -> str | None:
    with _connect(cache_path) as conn:
        row = conn.execute(
            "SELECT description FROM descriptions WHERE cache_key = ?",
            (_key(sql, dialect),),
        ).fetchone()
    return row[0] if row else None


def set_cached(
    sql: str, dialect: str, description: str, cache_path: Path = CACHE_PATH
) -> None:
    with _connect(cache_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO descriptions (cache_key, description, ts) VALUES (?, ?, ?)",
            (_key(sql, dialect), description, datetime.now(timezone.utc).isoformat()),
        )
