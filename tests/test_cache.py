import pytest

from lineage.cache import get_cached, set_cached


@pytest.fixture()
def db(tmp_path):
    return tmp_path / "test_cache.db"


def test_miss_on_empty_cache(db):
    assert get_cached("SELECT 1", "", cache_path=db) is None


def test_set_then_get(db):
    set_cached("SELECT 1", "", "This query selects one.", cache_path=db)
    assert get_cached("SELECT 1", "", cache_path=db) == "This query selects one."


def test_different_sql_is_separate_entry(db):
    set_cached("SELECT 1", "", "desc one", cache_path=db)
    set_cached("SELECT 2", "", "desc two", cache_path=db)

    assert get_cached("SELECT 1", "", cache_path=db) == "desc one"
    assert get_cached("SELECT 2", "", cache_path=db) == "desc two"


def test_different_dialect_is_separate_entry(db):
    set_cached("SELECT 1", "", "ansi desc", cache_path=db)
    set_cached("SELECT 1", "bigquery", "bq desc", cache_path=db)

    assert get_cached("SELECT 1", "", cache_path=db) == "ansi desc"
    assert get_cached("SELECT 1", "bigquery", cache_path=db) == "bq desc"


def test_overwrite_on_same_key(db):
    set_cached("SELECT 1", "", "first", cache_path=db)
    set_cached("SELECT 1", "", "second", cache_path=db)

    assert get_cached("SELECT 1", "", cache_path=db) == "second"


def test_miss_returns_none_not_falsy(db):
    result = get_cached("SELECT 999", "", cache_path=db)
    assert result is None
