import pytest

from lineage.parser import LineageInfo
from lineage.prompts import build_prompt


def test_v1_contains_sql():
    lineage = LineageInfo(source_tables=["users"])
    prompt = build_prompt(lineage, "SELECT name FROM users", version="v1")
    assert "SELECT name FROM users" in prompt


def test_v1_contains_source_tables():
    lineage = LineageInfo(source_tables=["orders", "users"])
    prompt = build_prompt(lineage, "SELECT 1", version="v1")
    assert "orders" in prompt
    assert "users" in prompt


def test_v1_contains_target_table():
    lineage = LineageInfo(target_table="summary")
    prompt = build_prompt(lineage, "INSERT INTO summary SELECT 1", version="v1")
    assert "summary" in prompt


def test_v1_shows_direct_query_when_no_target():
    lineage = LineageInfo()
    prompt = build_prompt(lineage, "SELECT 1")
    assert "direct query" in prompt


def test_v1_contains_joins():
    lineage = LineageInfo(joins=[{"type": "LEFT", "table": "orders"}])
    prompt = build_prompt(lineage, "SELECT 1")
    assert "LEFT JOIN orders" in prompt


def test_v1_contains_filters():
    lineage = LineageInfo(filters=["status = 'active'"])
    prompt = build_prompt(lineage, "SELECT 1")
    assert "status = 'active'" in prompt


def test_default_version_is_v1():
    lineage = LineageInfo(source_tables=["t"])
    assert build_prompt(lineage, "SELECT 1") == build_prompt(lineage, "SELECT 1", version="v1")


def test_unknown_version_raises():
    with pytest.raises(ValueError, match="Unknown prompt version"):
        build_prompt(LineageInfo(), "SELECT 1", version="v99")
