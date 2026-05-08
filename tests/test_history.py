import pytest

from lineage.history import get_stats, record_run, sql_hash


@pytest.fixture()
def db(tmp_path):
    return tmp_path / "test_history.db"


def test_sql_hash_is_deterministic():
    assert sql_hash("SELECT 1") == sql_hash("SELECT 1")


def test_sql_hash_differs_for_different_sql():
    assert sql_hash("SELECT 1") != sql_hash("SELECT 2")


def test_sql_hash_length():
    assert len(sql_hash("SELECT 1")) == 12


def test_record_and_retrieve(db):
    record_run("SELECT 1", "", llm_used=False, db_path=db)
    stats = get_stats(db_path=db)

    assert stats["total_runs"] == 1
    assert stats["llm_calls"] == 0
    assert stats["no_llm_runs"] == 1
    assert stats["errors"] == 0


def test_record_llm_run(db):
    record_run("SELECT 1", "bigquery", llm_used=True, latency_ms=420, db_path=db)
    stats = get_stats(db_path=db)

    assert stats["llm_calls"] == 1
    assert stats["avg_latency_ms"] == 420


def test_record_error_run(db):
    record_run("BAD SQL", "", llm_used=False, error="parse error", db_path=db)
    stats = get_stats(db_path=db)

    assert stats["errors"] == 1


def test_empty_db_returns_zeros(db):
    stats = get_stats(db_path=db)

    assert stats["total_runs"] == 0
    assert stats["llm_calls"] == 0
    assert stats["avg_latency_ms"] is None
    assert stats["estimated_cost_usd"] == 0.0


def test_multiple_runs_avg_latency(db):
    record_run("SELECT 1", "", llm_used=True, latency_ms=200, db_path=db)
    record_run("SELECT 2", "", llm_used=True, latency_ms=400, db_path=db)
    stats = get_stats(db_path=db)

    assert stats["avg_latency_ms"] == 300


def test_recent_runs_limit(db):
    for i in range(15):
        record_run(f"SELECT {i}", "", llm_used=False, db_path=db)
    stats = get_stats(db_path=db)

    assert len(stats["recent"]) == 10  # type: ignore[arg-type]


def test_estimated_cost_positive_for_llm_calls(db):
    record_run("SELECT 1", "", llm_used=True, latency_ms=300, db_path=db)
    stats = get_stats(db_path=db)

    assert stats["estimated_cost_usd"] > 0
