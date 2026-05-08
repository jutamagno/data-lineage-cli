from lineage.batch import analyze_batch, split_sql


def test_split_sql_basic():
    queries = split_sql("SELECT 1; SELECT 2; SELECT 3")
    assert len(queries) == 3
    assert queries[0] == "SELECT 1"
    assert queries[2] == "SELECT 3"


def test_split_sql_skips_empty_parts():
    queries = split_sql("SELECT 1;; SELECT 2")
    assert len(queries) == 2


def test_split_sql_strips_whitespace():
    queries = split_sql("  SELECT 1  ;  SELECT 2  ")
    assert queries[0] == "SELECT 1"
    assert queries[1] == "SELECT 2"


def test_split_sql_trailing_semicolon():
    queries = split_sql("SELECT 1; SELECT 2;")
    assert len(queries) == 2


def test_split_sql_single_query():
    queries = split_sql("SELECT id FROM users")
    assert queries == ["SELECT id FROM users"]


def test_analyze_batch_no_llm(tmp_path):
    sql_file = tmp_path / "queries.sql"
    sql_file.write_text("SELECT id FROM users; SELECT name FROM orders")

    results = analyze_batch(sql_file, no_llm=True)

    assert len(results) == 2
    assert results[0]["source_tables"] == ["users"]
    assert results[1]["source_tables"] == ["orders"]


def test_analyze_batch_includes_sql_field(tmp_path):
    sql_file = tmp_path / "queries.sql"
    sql_file.write_text("SELECT id FROM users")

    results = analyze_batch(sql_file, no_llm=True)

    assert results[0]["sql"] == "SELECT id FROM users"


def test_analyze_batch_invalid_sql_produces_error_entry(tmp_path):
    sql_file = tmp_path / "queries.sql"
    sql_file.write_text("NOT VALID SQL @@@@; SELECT 1 FROM t")

    results = analyze_batch(sql_file, no_llm=True)

    assert len(results) == 2
    assert "error" in results[0]
    assert results[1]["source_tables"] == ["t"]


def test_analyze_batch_empty_file(tmp_path):
    sql_file = tmp_path / "queries.sql"
    sql_file.write_text("")

    results = analyze_batch(sql_file, no_llm=True)

    assert results == []


def test_analyze_batch_no_description_when_no_llm(tmp_path):
    sql_file = tmp_path / "queries.sql"
    sql_file.write_text("SELECT id FROM users")

    results = analyze_batch(sql_file, no_llm=True)

    assert "description" not in results[0]
