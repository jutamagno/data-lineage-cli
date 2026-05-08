from __future__ import annotations

from lineage.parser import LineageInfo

_VERSIONS = {"v1"}


def build_prompt(lineage: LineageInfo, sql: str, version: str = "v1") -> str:
    if version not in _VERSIONS:
        raise ValueError(f"Unknown prompt version '{version}'. Available: {sorted(_VERSIONS)}")
    return _v1(lineage, sql)


def _v1(lineage: LineageInfo, sql: str) -> str:
    joins_text = (
        ", ".join(f"{j['type']} JOIN {j['table']}" for j in lineage.joins)
        if lineage.joins
        else "none"
    )
    filters_text = "; ".join(lineage.filters) if lineage.filters else "none"

    return (
        "You are a data governance expert. Analyze the lineage below and write "
        "2-3 sentences describing what this query does, what data it consumes, "
        "and what it produces. Be concise and technical.\n\n"
        f"Original SQL:\n{sql}\n\n"
        "Extracted lineage:\n"
        f"- Source tables: {', '.join(lineage.source_tables) or 'none'}\n"
        f"- Target table: {lineage.target_table or 'direct query'}\n"
        f"- Columns read: {', '.join(lineage.columns_read) or 'none'}\n"
        f"- Joins: {joins_text}\n"
        f"- Filters: {filters_text}\n"
    )
