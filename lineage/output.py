from __future__ import annotations

import dataclasses
import json
import re
from collections import defaultdict

from lineage.parser import LineageInfo


def lineage_to_dict(
    lineage: LineageInfo,
    sql: str,
    description: str = "",
    error: str = "",
) -> dict[str, object]:
    d: dict[str, object] = dataclasses.asdict(lineage)
    d["sql"] = sql
    if description:
        d["description"] = description
    if error:
        d["error"] = error
    return d


def render_json(lineage: LineageInfo, sql: str, description: str = "") -> str:
    return json.dumps(lineage_to_dict(lineage, sql, description), indent=2)


def render_json_batch(results: list[dict[str, object]]) -> str:
    return json.dumps(results, indent=2)


def render_openmetadata(lineage: LineageInfo, sql: str) -> str:
    """Serialize lineage as an OpenMetadata-compatible column lineage payload."""
    col_edges: dict[str, list[dict[str, object]]] = defaultdict(list)
    for edge in lineage.column_lineage:
        col_edges[edge.source_table].append({
            "fromColumns": [f"{edge.source_table}.{edge.source_col}"],
            "toColumn": edge.target_col,
        })

    source_tables = list(col_edges.keys()) or lineage.source_tables
    result = []
    for src in source_tables:
        result.append({
            "fromTable": src,
            "toTable": lineage.target_table,
            "lineageDetails": {
                "sql": sql,
                "columnsLineage": col_edges.get(src, []),
            },
        })

    return json.dumps(result, indent=2)


def render_mermaid(lineage: LineageInfo) -> str:
    """Render lineage as a Mermaid graph LR diagram."""
    lines = ["graph LR"]
    target = lineage.target_table or "result"
    seen: set[tuple[str, str]] = set()

    if lineage.column_lineage:
        for edge in lineage.column_lineage:
            tgt_label = (
                f"{lineage.target_table}.{edge.target_col}"
                if lineage.target_table
                else edge.target_col
            )
            src_label = f"{edge.source_table}.{edge.source_col}"
            key = (src_label, tgt_label)
            if key not in seen:
                seen.add(key)
                lines.append(f'  {_mid(src_label)}["{src_label}"] --> {_mid(tgt_label)}["{tgt_label}"]')
    else:
        for src in lineage.source_tables:
            key = (src, target)
            if key not in seen:
                seen.add(key)
                lines.append(f'  {_mid(src)}["{src}"] --> {_mid(target)}["{target}"]')

    if len(lines) == 1:
        lines.append('  empty["(no lineage detected)"]')

    return "\n".join(lines)


def _mid(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", name)
