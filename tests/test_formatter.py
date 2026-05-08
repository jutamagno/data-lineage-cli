import pytest
from rich.console import Console

import lineage.formatter as fmt
from lineage.parser import LineageInfo


@pytest.fixture(autouse=True)
def patch_console(monkeypatch: pytest.MonkeyPatch) -> Console:
    test_console = Console(record=True, width=120)
    monkeypatch.setattr(fmt, "console", test_console)
    return test_console


def _output(patch_console: Console) -> str:
    return patch_console.export_text()


def test_sources_displayed(patch_console: Console) -> None:
    fmt.print_lineage(LineageInfo(source_tables=["users", "orders"]), "")
    output = _output(patch_console)
    assert "users" in output
    assert "orders" in output


def test_direct_query_when_no_target(patch_console: Console) -> None:
    fmt.print_lineage(LineageInfo(source_tables=["users"]), "")
    assert "(direct query)" in _output(patch_console)


def test_target_table_displayed(patch_console: Console) -> None:
    fmt.print_lineage(LineageInfo(target_table="summary"), "")
    assert "summary" in _output(patch_console)


def test_columns_read_displayed(patch_console: Console) -> None:
    fmt.print_lineage(LineageInfo(columns_read=["id", "name", "email"]), "")
    output = _output(patch_console)
    assert "id" in output
    assert "name" in output
    assert "email" in output


def test_columns_written_displayed(patch_console: Console) -> None:
    fmt.print_lineage(LineageInfo(columns_written=["region", "total"]), "")
    output = _output(patch_console)
    assert "region" in output
    assert "total" in output


def test_joins_displayed(patch_console: Console) -> None:
    lineage = LineageInfo(
        source_tables=["a", "b"],
        joins=[{"type": "LEFT", "table": "b"}],
    )
    fmt.print_lineage(lineage, "")
    output = _output(patch_console)
    assert "LEFT" in output
    assert "b" in output


def test_filters_displayed(patch_console: Console) -> None:
    lineage = LineageInfo(filters=["status = 'active'", "year > 2023"])
    fmt.print_lineage(lineage, "")
    output = _output(patch_console)
    assert "status" in output
    assert "year" in output


def test_llm_panel_shown_when_description_provided(patch_console: Console) -> None:
    fmt.print_lineage(LineageInfo(), "This query reads all active users.")
    output = _output(patch_console)
    assert "LLM-generated description" in output
    assert "This query reads all active users." in output


def test_llm_panel_hidden_when_no_description(patch_console: Console) -> None:
    fmt.print_lineage(LineageInfo(), "")
    assert "LLM-generated description" not in _output(patch_console)
