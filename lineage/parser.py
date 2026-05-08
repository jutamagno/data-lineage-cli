from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
import sqlglot.expressions as exp


@dataclass
class LineageInfo:
    source_tables: list[str] = field(default_factory=list)
    target_table: str | None = None
    columns_read: list[str] = field(default_factory=list)
    columns_written: list[str] = field(default_factory=list)
    joins: list[dict] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)


def extract_lineage(sql: str, dialect: str = "") -> LineageInfo:
    tree = sqlglot.parse_one(sql, dialect=dialect or None)
    info = LineageInfo()

    _extract_target(tree, info)
    _extract_sources(tree, info)
    _extract_columns(tree, info)
    _extract_joins(tree, info)
    _extract_filters(tree, info)

    return info


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


def _extract_sources(tree: exp.Expression, info: LineageInfo) -> None:
    # For INSERT, the SELECT sub-tree holds FROM/JOIN tables; the very first
    # Table node is the target, so we collect from the SELECT downward.
    select_scope = _get_select_scope(tree)
    if select_scope is None:
        return

    seen: set[str] = set()
    for table in select_scope.find_all(exp.Table):
        name = table.name
        if name and name != info.target_table and name not in seen:
            seen.add(name)
            info.source_tables.append(name)


def _get_select_scope(tree: exp.Expression) -> exp.Expression | None:
    if isinstance(tree, exp.Select):
        return tree
    if isinstance(tree, (exp.Insert, exp.Create)):
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
    if join.args.get("kind"):
        return join.args["kind"].upper()
    if join.args.get("side"):
        return join.args["side"].upper()
    return "INNER"


def _extract_filters(tree: exp.Expression, info: LineageInfo) -> None:
    select_scope = _get_select_scope(tree)
    if select_scope is None:
        return

    where = select_scope.find(exp.Where)
    if where is None:
        return

    condition = where.this
    # Split AND-chained predicates into individual filter strings
    clauses = _split_and(condition)
    for clause in clauses:
        info.filters.append(clause.sql())


def _split_and(node: exp.Expression) -> list[exp.Expression]:
    if isinstance(node, exp.And):
        return _split_and(node.left) + _split_and(node.right)
    return [node]
