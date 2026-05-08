from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".lineage-cli" / "history.db"

# Rough token estimates per Bedrock call (used for cost estimate only)
_AVG_INPUT_TOKENS = 300
_AVG_OUTPUT_TOKENS = 100
# claude-haiku-4-5 on Bedrock us-east-1 ($/1M tokens)
_COST_PER_M_INPUT = 0.80
_COST_PER_M_OUTPUT = 4.00
_COST_PER_CALL = (
    _AVG_INPUT_TOKENS / 1_000_000 * _COST_PER_M_INPUT
    + _AVG_OUTPUT_TOKENS / 1_000_000 * _COST_PER_M_OUTPUT
)


def sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.encode()).hexdigest()[:12]


def _connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sql_hash    TEXT    NOT NULL,
            dialect     TEXT    NOT NULL,
            ts          TEXT    NOT NULL,
            llm_used    INTEGER NOT NULL,
            latency_ms  INTEGER,
            error       TEXT
        )
    """)
    conn.commit()
    return conn


def record_run(
    sql: str,
    dialect: str,
    llm_used: bool,
    latency_ms: int | None = None,
    error: str | None = None,
    db_path: Path = DB_PATH,
) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO runs (sql_hash, dialect, ts, llm_used, latency_ms, error)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                sql_hash(sql),
                dialect or "default",
                datetime.now(timezone.utc).isoformat(),
                int(llm_used),
                latency_ms,
                error,
            ),
        )


def get_stats(db_path: Path = DB_PATH) -> dict[str, object]:
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        llm_calls = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE llm_used = 1"
        ).fetchone()[0]
        errors = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE error IS NOT NULL"
        ).fetchone()[0]
        avg_row = conn.execute(
            "SELECT AVG(latency_ms) FROM runs WHERE latency_ms IS NOT NULL"
        ).fetchone()[0]
        recent = conn.execute(
            "SELECT sql_hash, dialect, ts, llm_used, latency_ms"
            " FROM runs ORDER BY id DESC LIMIT 10"
        ).fetchall()

    return {
        "total_runs": total,
        "llm_calls": llm_calls,
        "no_llm_runs": total - llm_calls,
        "errors": errors,
        "avg_latency_ms": round(avg_row) if avg_row is not None else None,
        "estimated_cost_usd": round(llm_calls * _COST_PER_CALL, 4),
        "recent": recent,
    }
