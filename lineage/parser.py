from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import sqlglot
import sqlglot.expressions as exp

if TYPE_CHECKING:
    from sqlglot.lineage import Node as _LineageNode


@dataclass
class ColumnEdge:
    source_table: str
    source_col: str
    target_col: str


@dataclass
class LineageInfo:
    source_tables: list[str] = field(default_factory=list)
    target_table: str | None = None
    columns_read: list[str] = field(default_factory=list)
    columns_written: list[str] = field(default_factory=list)
    joins: list[dict[str, str]] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    column_lineage: list[ColumnEdge] = field(default_factory=list)


def extract_lineage(sql: str, dialect: str = "") -> LineageInfo:
    tree: exp.Expression = sqlglot.parse_one(sql, dialect=dialect or None)  # type: ignore[assignment]
    info = LineageInfo()
    cte_names = _cte_names(tree)

    _extract_target(tree, info)
    _extract_sources(tree, info, cte_names)
    _extract_columns(tree, info)
    _extract_joins(tree, info)
    _extract_filters(tree, info)
    info.column_lineage = _extract_column_lineage(sql, dialect)

    return info


def _cte_names(tree: exp.Expression) -> set[str]:
    names: set[str] = set()
    with_clause = tree.find(exp.With)
    if with_clause:
        for cte in with_clause.find_all(exp.CTE):
            names.add(cte.alias)
    return names


def _extract_target(tree: exp.Expression, info: LineageInfo) -> None:
    if isinstance(tree, exp.Insert):
        target = tree.find(exp.Table)
        if target:
            info.target_table = target.name

        # columns listed in INSERT INTO t (col1, col2) ...
        schema = tree.args.get("this")
        if isinstance(schema, exp.Schema):
            info.columns_written = [
                c.name for c in schema.expressions
                if isinstance(c, (exp.Column, exp.Identifier))
            ]

    elif isinstance(tree, exp.Create):
        target = tree.find(exp.Table)
        if target:
            info.target_table = target.name


def _extract_sources(
    tree: exp.Expression, info: LineageInfo, cte_names: set[str] | None = None
) -> None:
    select_scope = _get_select_scope(tree)
    if select_scope is None:
        return

    excluded = (cte_names or set()) | ({info.target_table} if info.target_table else set())
    seen: set[str] = set()
    for table in select_scope.find_all(exp.Table):
        name = table.name
        if name and name not in excluded and name not in seen:
            seen.add(name)
            info.source_tables.append(name)


def _get_select_scope(tree: exp.Expression) -> exp.Expression | None:
    if isinstance(tree, exp.Select):
        return tree
    if isinstance(tree, (exp.Insert, exp.Create)):
        # Prefer Union over a single Select so both branches are traversed
        union = tree.find(exp.Union)
        if union:
            return union
        return tree.find(exp.Select)
    return tree


def _extract_columns(tree: exp.Expression, info: LineageInfo) -> None:
    select_scope = _get_select_scope(tree)
    if select_scope is None:
        return

    seen: set[str] = set()
    for col in select_scope.find_all(exp.Column):
        name = col.name
        if name and name not in seen:
            seen.add(name)
            info.columns_read.append(name)

    # Star expands to a placeholder so the caller knows all columns are read
    for _ in select_scope.find_all(exp.Star):
        if "*" not in seen:
            seen.add("*")
            info.columns_read.append("*")


def _extract_joins(tree: exp.Expression, info: LineageInfo) -> None:
    select_scope = _get_select_scope(tree)
    if select_scope is None:
        return

    for join in select_scope.find_all(exp.Join):
        table = join.find(exp.Table)
        join_type = _join_type(join)
        if table:
            info.joins.append({"type": join_type, "table": table.name})


def _join_type(join: exp.Join) -> str:
    kind = join.args.get("kind")
    if kind:
        return str(kind).upper()
    side = join.args.get("side")
    if side:
        return str(side).upper()
    return "INNER"


def _extract_filters(tree: exp.Expression, info: LineageInfo) -> None:
    select_scope = _get_select_scope(tree)
    if select_scope is None:
        return

    seen: set[str] = set()
    for where in select_scope.find_all(exp.Where):
        for clause in _split_and(where.this):
            text = clause.sql()
            if text not in seen:
                seen.add(text)
                info.filters.append(text)


def _split_and(node: exp.Expression) -> list[exp.Expression]:
    if isinstance(node, exp.And):
        return _split_and(node.left) + _split_and(node.right)  # type: ignore[arg-type]
    return [node]


def _extract_column_lineage(sql: str, dialect: str) -> list[ColumnEdge]:
    try:
        from sqlglot.lineage import lineage as sql_lineage

        tree: exp.Expression = sqlglot.parse_one(sql, dialect=dialect or None)  # type: ignore[assignment]
        select = tree.find(exp.Select)
        if select is None:
            return []

        edges: list[ColumnEdge] = []
        seen: set[tuple[str, str, str]] = set()

        for sel_expr in select.expressions:
            if isinstance(sel_expr, exp.Star):
                continue
            if isinstance(sel_expr, exp.Alias):
                target_col = sel_expr.alias
            elif isinstance(sel_expr, exp.Column):
                target_col = sel_expr.name
            else:
                continue
            if not target_col:
                continue

            try:
                root = sql_lineage(
                    column=target_col,
                    sql=sql,
                    dialect=dialect or None,
                )
            except Exception:
                continue

            for leaf in _walk_leaves(root):
                if not isinstance(leaf.source, exp.Table):
                    continue
                source_table = leaf.source.name
                source_col = leaf.name.split(".")[-1]
                if not (source_table and source_col):
                    continue
                key = (source_table, source_col, target_col)
                if key not in seen:
                    seen.add(key)
                    edges.append(ColumnEdge(
                        source_table=source_table,
                        source_col=source_col,
                        target_col=target_col,
                    ))

    except Exception:
        return []

    return edges


def _walk_leaves(node: _LineageNode) -> list[_LineageNode]:
    if not node.downstream:
        return [node]
    leaves: list[_LineageNode] = []
    for child in node.downstream:
        leaves.extend(_walk_leaves(child))
    return leaves
