# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/column_reorder_suggestion.py
"""MariaDB's answer to the column-reorder change point.

MariaDB does reorder a column in place with ``ALTER TABLE ... MODIFY COLUMN
<name> <full definition> FIRST|AFTER <other>``. The existing
``ModifyColumnAction`` node carries exactly that clause, including its
``first`` / ``after_column`` positioning, and MariaDB's formatter renders the
``FIRST`` / ``AFTER`` tail.

The decision point, however, carries only column *names* (``old_order``,
``new_order``, ``reordered_columns``). ``ModifyColumnAction`` needs a complete
``ColumnDefinition`` with a real ``DataType``; there is no name-only reorder
node. Manufacturing a type would silently redefine the column, and a drop +
add pair would destroy its data, so the honest answer from this point is an
explicit unsupported rather than an invented chain.
"""

from ....suggestion import ColumnReorderSuggestion

#: Why this point is unaddressable, stated once for callers and tests.
UNSUPPORTED_REASON = (
    "MODIFY COLUMN ... FIRST|AFTER needs a complete ColumnDefinition with a "
    "DataType; the reorder point carries only column names, and no name-only "
    "reorder node exists. Drop + add would destroy data."
)


class MariaDBColumnReorderSuggestionMixin:
    """Refuse a name-only column reorder explicitly."""

    def suggest_column_reorder(self, point: ColumnReorderSuggestion) -> ColumnReorderSuggestion:
        """Answer explicit unsupported: the node needs a column definition.

        A caller that knows the full column specification can build a
        ``ModifyColumnAction`` with ``first``/``after_column`` itself; this
        protocol only has the names in ``point`` to work from.
        """
        return ColumnReorderSuggestion(operations=False)


__all__ = ["MariaDBColumnReorderSuggestionMixin", "UNSUPPORTED_REASON"]
