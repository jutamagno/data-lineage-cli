import pytest

pytest.importorskip("fastapi", reason="fastapi not installed — skipping server tests")

from fastapi.testclient import TestClient  # noqa: E402

from lineage.server import app  # noqa: E402

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_parses_simple_select() -> None:
    response = client.post("/analyze", json={"sql": "SELECT id FROM users", "no_llm": True})
    assert response.status_code == 200
    data = response.json()
    assert "users" in data["source_tables"]
    assert data["sql"] == "SELECT id FROM users"


def test_analyze_returns_column_lineage_key() -> None:
    response = client.post(
        "/analyze",
        json={"sql": "SELECT u.id FROM users u", "no_llm": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert "column_lineage" in data


def test_analyze_with_dialect() -> None:
    response = client.post(
        "/analyze",
        json={"sql": "SELECT id FROM `project.dataset.orders`", "dialect": "bigquery", "no_llm": True},
    )
    assert response.status_code == 200
    assert "source_tables" in response.json()


def test_batch_returns_list() -> None:
    response = client.post(
        "/batch",
        json={
            "queries": ["SELECT id FROM users", "SELECT name FROM orders"],
            "no_llm": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_batch_empty_queries() -> None:
    response = client.post("/batch", json={"queries": [], "no_llm": True})
    assert response.status_code == 200
    assert response.json() == []


def test_batch_isolates_errors() -> None:
    response = client.post(
        "/batch",
        json={"queries": ["SELECT id FROM users", ""], "no_llm": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
