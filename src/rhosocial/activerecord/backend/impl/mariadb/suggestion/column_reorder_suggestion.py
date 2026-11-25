# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/column_reorder_suggestion.py
"""MariaDB's answer to the column-reorder change point.

MariaDB reorders a column in place with ``ALTER TABLE ... MODIFY COLUMN
<name> <full definition> FIRST|AFTER <other>``. The existing
``ModifyColumnAction`` node carries exactly that clause, including its
``first`` / ``after_column`` positioning, and this dialect renders the
``FIRST`` / ``AFTER`` tail.

The point now carries the model's full ``ColumnDefinition`` objects in
``new_fields`` (keyed by database column name). Those are the very definitions
of the columns being reordered, so a non-destructive chain can be built from
them: no type is invented and no column is dropped or re-added. Columns that
keep their relative position (a longest common subsequence of the old and new
order) are left untouched; every column that actually moves gets one
``ALTER TABLE`` statement holding one ``ModifyColumnAction``.

A point that does not carry a complete definition for a moved column (an older
caller that supplies only names), or a dialect that cannot spell MODIFY COLUMN,
is still refused explicitly rather than guessed.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple

from ....expression.statements import AlterTableStatement
from ....expression.statements.ddl_alter import ModifyColumnAction
from ....suggestion import ColumnReorderSuggestion
from ._change_plan_common import one_statement, table_for

#: Why a name-only point (or a dialect without MODIFY COLUMN) is unaddressable.
#: Kept as one statement so callers and tests can quote the evidence directly.
UNSUPPORTED_REASON = (
    "MODIFY COLUMN ... FIRST|AFTER needs a complete ColumnDefinition with a "
    "DataType; a point that carries only column names cannot build the node, "
    "and Drop + add would destroy data, so such a point is refused."
)


def _anchors(old_order: Sequence[str], new_order: Sequence[str]) -> FrozenSet[str]:
    """Columns whose relative position is unchanged (a longest common subsequence).

    Only these columns may stay put. Ties are resolved toward keeping the
    earlier old-order column, which is deterministic and never affects the
    correctness of the resulting chain.
    """
    n, m = len(old_order), len(new_order)
    dp: List[List[int]] = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if old_order[i] == new_order[j]:
                dp[i][j] = dp[i + 1][j + 1] + 1
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    kept = set()
    i = j = 0
    while i < n and j < m:
        if old_order[i] == new_order[j]:
            kept.add(new_order[j])
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return frozenset(kept)


class MariaDBColumnReorderSuggestionMixin:
    """Answer a reorder with one in-place MODIFY COLUMN statement per moved column."""

    def suggest_column_reorder(self, point: ColumnReorderSuggestion) -> ColumnReorderSuggestion:
        """Reuse the point's full column definitions in a non-destructive chain.

        Each moved column is placed after its immediate predecessor in the new
        order (or ``FIRST`` when it becomes the first column). Statements are
        emitted in target order, so a predecessor that also moved has already
        been placed by the time it is referenced.
        """
        old_order: Tuple[str, ...] = tuple(point.old_order or ())
        new_order: Tuple[str, ...] = tuple(point.new_order or ())
        if not new_order or new_order == old_order:
            return ColumnReorderSuggestion(operations=None)

        table = table_for(self, point.table_name)
        if table is None or not getattr(self, "supports_modify_column", lambda: False)():
            return ColumnReorderSuggestion(operations=False)

        fields: Dict[str, Any] = dict(point.new_fields or {})
        old_names = set(old_order)
        anchors = _anchors(old_order, new_order)
        operations: List[AlterTableStatement] = []
        for index, name in enumerate(new_order):
            # Brand-new columns are added by a separate statement, not moved.
            if name not in old_names or name in anchors:
                continue
            column = fields.get(name)
            if column is None or getattr(column, "data_type", None) is None:
                return ColumnReorderSuggestion(operations=False)
            previous: Optional[str] = new_order[index - 1] if index else None
            action = ModifyColumnAction(self, column, first=previous is None, after_column=previous)
            operations.append(one_statement(self, table, action))

        if not operations:
            return ColumnReorderSuggestion(operations=None)
        return ColumnReorderSuggestion(operations=tuple(operations))


__all__ = ["MariaDBColumnReorderSuggestionMixin", "UNSUPPORTED_REASON"]
