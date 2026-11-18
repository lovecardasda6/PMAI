"""Automatic left-to-right arrangement of tables based on links."""

from __future__ import annotations

from .cardmetrics import card_size
from .models import Project

X_MARGIN = 60
Y_MARGIN = 60
COL_GAP = 80
ROW_GAP = 46


def _levels(project: Project) -> dict[str, int]:
    tables = {table.id: table for table in project.tables}
    parents: dict[str, set[str]] = {table.id: set() for table in project.tables}
    for table in project.tables:
        for row in table.rows:
            target = row.link_table_id
            if target in tables and target != table.id:
                parents[target].add(table.id)

    memo: dict[str, int] = {}

    def depth(table_id: str, stack: frozenset[str]) -> int:
        if table_id in memo:
            return memo[table_id]
        if table_id in stack:
            return 0
        parent_ids = parents.get(table_id, set())
        if not parent_ids:
            value = 0
        else:
            value = 1 + max(
                depth(parent, stack | {table_id}) for parent in parent_ids
            )
        memo[table_id] = value
        return value

    for table in project.tables:
        depth(table.id, frozenset())
    return memo


def auto_layout(project: Project) -> None:
    """Position tables in columns following the link graph."""
    if not project.tables:
        return

    levels = _levels(project)
    groups: dict[int, list] = {}
    for table in project.tables:
        groups.setdefault(levels.get(table.id, 0), []).append(table)

    max_level = max(groups)
    column_widths: dict[int, int] = {}
    for level in range(max_level + 1):
        tables = groups.get(level, [])
        column_widths[level] = max(
            (card_size(table)[0] for table in tables),
            default=0,
        )

    x = X_MARGIN
    for level in range(max_level + 1):
        tables = groups.get(level, [])
        tables.sort(key=lambda t: (t.y, t.x, t.name.lower()))
        y = Y_MARGIN
        for table in tables:
            table.x = float(x)
            table.y = float(y)
            y += card_size(table)[1] + ROW_GAP
        x += column_widths.get(level, 0) + COL_GAP
