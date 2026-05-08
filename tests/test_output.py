import json

from lineage.output import lineage_to_dict, render_json, render_json_batch, render_openmetadata
from lineage.parser import ColumnEdge, LineageInfo


def test_lineage_to_dict_contains_sql():
    lineage = LineageInfo(source_tables=["users"])
    d = lineage_to_dict(lineage, "SELECT 1")
    assert d["sql"] == "SELECT 1"
    assert d["source_tables"] == ["users"]


def test_lineage_to_dict_includes_description():
    d = lineage_to_dict(LineageInfo(), "SELECT 1", description="a description")
    assert d["description"] == "a description"


def test_lineage_to_dict_omits_description_key_when_empty():
    d = lineage_to_dict(LineageInfo(), "SELECT 1")
    assert "description" not in d


def test_lineage_to_dict_includes_error():
    d = lineage_to_dict(LineageInfo(), "SELECT 1", error="something failed")
    assert d["error"] == "something failed"


def test_lineage_to_dict_omits_error_key_when_empty():
    d = lineage_to_dict(LineageInfo(), "SELECT 1")
    assert "error" not in d


def test_render_json_is_valid_json():
    lineage = LineageInfo(source_tables=["orders"], target_table="summary")
    output = render_json(lineage, "SELECT 1", description="desc")
    parsed = json.loads(output)
    assert parsed["source_tables"] == ["orders"]
    assert parsed["target_table"] == "summary"
    assert parsed["description"] == "desc"
    assert parsed["sql"] == "SELECT 1"


def test_render_json_contains_all_lineage_fields():
    lineage = LineageInfo(
        source_tables=["t"],
        columns_read=["id"],
        joins=[{"type": "LEFT", "table": "other"}],
        filters=["x = 1"],
    )
    parsed = json.loads(render_json(lineage, "SELECT id FROM t"))
    assert "source_tables" in parsed
    assert "columns_read" in parsed
    assert "joins" in parsed
    assert "filters" in parsed
    assert "columns_written" in parsed
    assert "target_table" in parsed


def test_render_json_batch_returns_array():
    d = lineage_to_dict(LineageInfo(), "SELECT 1")
    output = render_json_batch([d, d])
    parsed = json.loads(output)
    assert isinstance(parsed, list)
    assert len(parsed) == 2


def test_render_json_batch_empty_list():
    output = render_json_batch([])
    assert json.loads(output) == []


def test_lineage_to_dict_includes_column_lineage():
    lineage = LineageInfo(
        column_lineage=[ColumnEdge(source_table="t", source_col="col", target_col="alias")]
    )
    d = lineage_to_dict(lineage, "SELECT 1")
    edges = d["column_lineage"]
    assert isinstance(edges, list)
    assert len(edges) == 1  # type: ignore[arg-type]
    assert edges[0]["source_table"] == "t"  # type: ignore[index]


def test_render_openmetadata_basic():
    lineage = LineageInfo(
        source_tables=["transactions"],
        target_table="summary",
        column_lineage=[ColumnEdge("transactions", "amount", "total")],
    )
    output = render_openmetadata(lineage, "SELECT SUM(t.amount) AS total FROM transactions t")
    parsed = json.loads(output)
    assert isinstance(parsed, list)
    assert parsed[0]["fromTable"] == "transactions"
    assert parsed[0]["toTable"] == "summary"
    cols = parsed[0]["lineageDetails"]["columnsLineage"]
    assert len(cols) == 1
    assert cols[0]["toColumn"] == "total"
    assert "transactions.amount" in cols[0]["fromColumns"]


def test_render_openmetadata_no_column_lineage_uses_source_tables():
    lineage = LineageInfo(source_tables=["orders"], target_table="summary")
    output = render_openmetadata(lineage, "SELECT * FROM orders")
    parsed = json.loads(output)
    assert parsed[0]["fromTable"] == "orders"
    assert parsed[0]["lineageDetails"]["columnsLineage"] == []


def test_render_openmetadata_is_valid_json():
    lineage = LineageInfo()
    output = render_openmetadata(lineage, "SELECT 1")
    assert json.loads(output) == []
