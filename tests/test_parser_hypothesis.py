from hypothesis import assume, given, settings
from hypothesis import strategies as st

from lineage.parser import LineageInfo, extract_lineage

_SQL_KEYWORDS = {
    "all", "and", "as", "asc", "between", "by", "case", "create", "cross",
    "desc", "distinct", "else", "end", "except", "exists", "false", "from",
    "full", "group", "having", "in", "inner", "insert", "intersect", "into",
    "is", "join", "left", "like", "limit", "not", "null", "on", "or",
    "order", "outer", "right", "select", "set", "table", "then", "true",
    "union", "update", "values", "when", "where", "with",
}

_TEMPLATES = [
    "SELECT {col} FROM {tbl}",
    "SELECT {col} FROM {tbl} WHERE {col} = 1",
    "SELECT a.{col} FROM {tbl} a JOIN {tbl2} b ON a.id = b.id",
    "INSERT INTO {tbl} SELECT {col} FROM {tbl2}",
    "SELECT {col} FROM {tbl} UNION SELECT {col} FROM {tbl2}",
    "SELECT {col} FROM {tbl} UNION ALL SELECT {col} FROM {tbl2}",
    "WITH cte AS (SELECT {col} FROM {tbl}) SELECT {col} FROM cte",
    "SELECT sub.{col} FROM (SELECT {col} FROM {tbl}) AS sub",
    "CREATE TABLE {tbl} AS SELECT {col} FROM {tbl2}",
]

_ident = st.from_regex(r"[a-z][a-z0-9_]{0,8}", fullmatch=True)


@given(
    col=_ident,
    tbl=_ident,
    tbl2=_ident,
    idx=st.integers(min_value=0, max_value=len(_TEMPLATES) - 1),
)
@settings(max_examples=300)
def test_parser_never_raises(col: str, tbl: str, tbl2: str, idx: int) -> None:
    assume(col not in _SQL_KEYWORDS)
    assume(tbl not in _SQL_KEYWORDS)
    assume(tbl2 not in _SQL_KEYWORDS)

    sql = _TEMPLATES[idx].format(col=col, tbl=tbl, tbl2=tbl2)
    result = extract_lineage(sql)

    assert isinstance(result, LineageInfo)
    assert isinstance(result.source_tables, list)
    assert isinstance(result.columns_read, list)
    assert isinstance(result.joins, list)
    assert isinstance(result.filters, list)
    assert all(isinstance(t, str) for t in result.source_tables)
    assert all(isinstance(f, str) for f in result.filters)
