from lineage.parser import extract_lineage


def test_simple_select():
    sql = "SELECT name, email FROM users WHERE active = true"
    result = extract_lineage(sql)

    assert result.source_tables == ["users"]
    assert set(result.columns_read) >= {"name", "email", "active"}
    assert result.target_table is None
    assert result.joins == []
    assert len(result.filters) == 1


def test_inner_join():
    sql = "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
    result = extract_lineage(sql)

    assert set(result.source_tables) == {"users", "orders"}
    assert len(result.joins) == 1
    assert result.joins[0]["type"] == "INNER"
    assert result.joins[0]["table"] == "orders"
    assert set(result.columns_read) >= {"name", "total", "id", "user_id"}


def test_insert_into_select():
    sql = "INSERT INTO summary SELECT region, sum(amount) FROM sales GROUP BY region"
    result = extract_lineage(sql)

    assert result.target_table == "summary"
    assert result.source_tables == ["sales"]
    assert set(result.columns_read) >= {"region", "amount"}


def test_create_table_as_select():
    sql = "CREATE TABLE report AS SELECT * FROM transactions WHERE year = 2024"
    result = extract_lineage(sql)

    assert result.target_table == "report"
    assert result.source_tables == ["transactions"]
    assert "*" in result.columns_read


def test_left_join_multiple_filters():
    sql = """
    SELECT a.id, b.value
    FROM table_a a
    LEFT JOIN table_b b ON a.key = b.key
    WHERE a.status = 'active' AND b.created_at > '2024-01-01'
    """
    result = extract_lineage(sql)

    assert set(result.source_tables) == {"table_a", "table_b"}
    assert len(result.joins) == 1
    assert result.joins[0]["type"] == "LEFT"
    assert result.joins[0]["table"] == "table_b"
    assert len(result.filters) == 2


def test_no_filters():
    sql = "SELECT id, name FROM products"
    result = extract_lineage(sql)

    assert result.source_tables == ["products"]
    assert result.filters == []


def test_multiple_joins():
    sql = """
    SELECT a.x, b.y, c.z
    FROM a
    INNER JOIN b ON a.id = b.a_id
    LEFT JOIN c ON b.id = c.b_id
    """
    result = extract_lineage(sql)

    assert set(result.source_tables) == {"a", "b", "c"}
    assert len(result.joins) == 2
    join_types = {j["type"] for j in result.joins}
    assert "INNER" in join_types
    assert "LEFT" in join_types


def test_columns_written_in_insert():
    sql = "INSERT INTO dest (col1, col2) SELECT col1, col2 FROM src"
    result = extract_lineage(sql)

    assert result.target_table == "dest"
    assert result.source_tables == ["src"]
    assert set(result.columns_written) == {"col1", "col2"}


def test_bigquery_dialect():
    sql = "SELECT user_id, amount FROM `project.dataset.orders` WHERE status = 'paid'"
    result = extract_lineage(sql, dialect="bigquery")

    assert "orders" in result.source_tables
    assert set(result.columns_read) >= {"user_id", "amount", "status"}
