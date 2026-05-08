from __future__ import annotations

import re


def strip_jinja(sql: str) -> str:
    """Strip dbt Jinja2 tags, replacing ref/source with table names."""
    sql = re.sub(r"\{\{\s*ref\(['\"](\w+)['\"]\)\s*\}\}", r"\1", sql)
    sql = re.sub(
        r"\{\{\s*source\(['\"][^'\"]+['\"],\s*['\"](\w+)['\"]\)\s*\}\}",
        r"\1",
        sql,
    )
    sql = re.sub(r"\{%.*?%\}", "", sql, flags=re.DOTALL)
    return sql.strip()
