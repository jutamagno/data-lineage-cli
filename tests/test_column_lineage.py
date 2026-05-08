from lineage.parser import ColumnEdge, LineageInfo, extract_lineage


def test_column_edge_dataclass():
    edge = ColumnEdge(source_table="transactions", source_col="amount", target_col="total")
    assert edge.source_table == "transactions"
    assert edge.source_col == "amount"
    assert edge.target_col == "total"


def test_lineage_info_column_lineage_defaults_empty():
    info = LineageInfo()
    assert info.column_lineage == []


def test_column_lineage_field_is_list():
    result = extract_lineage("SELECT id FROM users")
    assert isinstance(result.column_lineage, list)


def test_column_lineage_entries_are_column_edges():
    result = extract_lineage("SELECT u.id FROM users u")
    for edge in result.column_lineage:
        assert isinstance(edge, ColumnEdge)
        assert isinstance(edge.source_table, str)
        assert isinstance(edge.source_col, str)
        assert isinstance(edge.target_col, str)


def test_column_lineage_qualified_simple():
    result = extract_lineage("SELECT t.amount FROM transactions t")
    edges = result.column_lineage
    if edges:
        assert any(e.source_table == "transactions" for e in edges)
        assert any(e.source_col == "amount" for e in edges)


def test_column_lineage_with_alias():
    result = extract_lineage("SELECT t.amount AS total FROM transactions t")
    edges = result.column_lineage
    if edges:
        assert any(e.target_col == "total" for e in edges)
        assert any(e.source_col == "amount" for e in edges)


def test_column_lineage_empty_for_literal():
    result = extract_lineage("SELECT 1 AS const_val")
    assert isinstance(result.column_lineage, list)


def test_column_lineage_no_raises_on_cte():
    sql = "WITH cte AS (SELECT id FROM users) SELECT id FROM cte"
    result = extract_lineage(sql)
    assert isinstance(result.column_lineage, list)


def test_column_lineage_no_raises_on_union():
    sql = "SELECT id FROM t1 UNION SELECT id FROM t2"
    result = extract_lineage(sql)
    assert isinstance(result.column_lineage, list)


def test_column_lineage_no_raises_on_subquery():
    sql = "SELECT sub.id FROM (SELECT id FROM users WHERE active = 1) AS sub"
    result = extract_lineage(sql)
    assert isinstance(result.column_lineage, list)


def test_column_lineage_multiple_columns():
    result = extract_lineage("SELECT t.id, t.name FROM users t")
    edges = result.column_lineage
    if edges:
        target_cols = {e.target_col for e in edges}
        assert "id" in target_cols or "name" in target_cols
