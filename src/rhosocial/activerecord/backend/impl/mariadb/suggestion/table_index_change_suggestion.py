# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/table_index_change_suggestion.py
"""MariaDB's answer to the table-index change point.

``supports_alter_table_index_actions()`` is True on every MariaDB release, and
core owns both nodes this backend needs: ``DropIndexAction`` renders
``DROP INDEX <name>`` and ``AddIndexAction`` renders
``ADD INDEX <name> (<columns>)``. Each action goes into its own
``AlterTableStatement`` so one returned operation is one executable statement.

The answer is conservative about what those nodes can render. ``AddIndexAction``
has no slot for UNIQUE, USING, partial or included columns; silently omitting
any of them would change the index's meaning, so such an addition is refused
rather than downgraded. ``DROP INDEX IF EXISTS`` is likewise only used when the
dialect's probe allows it.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from ....expression import Column
from ....expression.objects import Index
from ....expression.statements import AddIndexAction, DropIndexAction, IndexDefinition
from ....suggestion import TableIndexChangeSuggestion
from ._change_plan_common import canonical, name_of, one_statement, params_of, table_for

#: Fields whose meaning ``AddIndexAction`` cannot carry into its clause.
_UNRENDERABLE_ADD_FIELDS = (
    "unique",
    "type",
    "partial_condition",
    "include_columns",
    "tablespace",
    "concurrent",
    "if_not_exists",
)

#: The exact parameter set of a plain ``Column`` in a frozen projection.
_COLUMN_FIELDS = frozenset(
    {
        "alias",
        "alias_need_quote",
        "name",
        "name_need_quote",
        "schema_name",
        "schema_need_quote",
        "table",
        "table_need_quote",
    }
)


def _columns(value: Any) -> Optional[List[str]]:
    """Read an index's columns as plain names, as ``AddIndexAction`` needs."""
    params = params_of(value)
    if params is None:
        return None
    columns = params.get("columns")
    if not isinstance(columns, (list, tuple)) or not columns:
        return None
    result: List[str] = []
    for column in columns:
        if isinstance(column, str) and column.strip():
            result.append(column)
            continue
        column_params = params_of(column)
        if isinstance(column, Column):
            name: Any = column.name
        else:
            # Only a plain Column can be reduced to a name without losing the
            # expression a functional index would carry.
            if column_params is None or not _COLUMN_FIELDS.issubset(column_params):
                return None
            name = column_params.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        result.append(name)
    return result


def _add_action(dialect: Any, value: Any) -> Optional[AddIndexAction]:
    params = params_of(value)
    if params is None or any(params.get(field) for field in _UNRENDERABLE_ADD_FIELDS):
        return None
    name = name_of(value)
    columns = _columns(value)
    if not name or columns is None:
        return None
    return AddIndexAction(dialect, IndexDefinition(dialect, name, columns))


def _drop_action(dialect: Any, value: Any) -> Optional[DropIndexAction]:
    params = params_of(value)
    if params is None:
        return None
    if (
        params.get("if_exists")
        and not getattr(dialect, "supports_index_if_exists", lambda: False)()
    ):
        return None
    name = name_of(value)
    if not name:
        return None
    return DropIndexAction(dialect, Index(dialect, name), if_exists=bool(params.get("if_exists")))


def _diff(old: Tuple[Any, ...], new: Tuple[Any, ...]) -> Tuple[List[Any], List[Any]]:
    old_by_key = {canonical(item): item for item in old}
    new_by_key = {canonical(item): item for item in new}
    dropped = [item for key, item in old_by_key.items() if key not in new_by_key]
    added = [item for key, item in new_by_key.items() if key not in old_by_key]
    return dropped, added


class MariaDBTableIndexChangeSuggestionMixin:
    """Answer an index change with real ADD/DROP INDEX action chains."""

    def suggest_table_index_change(
        self, point: TableIndexChangeSuggestion
    ) -> TableIndexChangeSuggestion:
        """Return one ALTER TABLE statement per dropped then added index."""
        if not getattr(self, "supports_alter_table_index_actions", lambda: False)():
            return TableIndexChangeSuggestion(operations=False)
        table = table_for(self, point.table_name)
        if table is None:
            return TableIndexChangeSuggestion(operations=False)
        dropped, added = _diff(tuple(point.old_indexes or ()), tuple(point.new_indexes or ()))
        if not dropped and not added:
            return TableIndexChangeSuggestion(operations=None)

        operations = []
        for value in dropped:
            action = _drop_action(self, value)
            if action is None:
                return TableIndexChangeSuggestion(operations=False)
            operations.append(one_statement(self, table, action))
        for value in added:
            action = _add_action(self, value)
            if action is None:
                return TableIndexChangeSuggestion(operations=False)
            operations.append(one_statement(self, table, action))
        return TableIndexChangeSuggestion(operations=tuple(operations))


__all__ = ["MariaDBTableIndexChangeSuggestionMixin"]
