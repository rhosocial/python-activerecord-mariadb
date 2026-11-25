# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_scheme_change_suggestion.py
"""MariaDB's answer to the partition-scheme change point.

The point carries frozen old/new ``PARTITION BY`` projections. Three cases
have an honest answer from the existing MariaDB nodes:

* partitioning is removed (new projection is absent) -> ``REMOVE PARTITIONING``;
* the projections are identical -> ``None``, no action;
* a RANGE/LIST projection changes its definitions -> the existing add/drop
  partition suggestions supply the statements, with retention left to its own
  cutoff-driven rule (never invoked without a cutoff).

A HASH/KEY projection whose partition count shrinks reuses the existing
COALESCE suggestion. Adding partitioning to a table that has none, switching
between methods, and changing partition keys have no ``ALTER TABLE`` node on
this backend: they need a table rebuild that the expression layer does not
model, so the answer is explicit unsupported rather than an invented chain.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ....expression.statements import PartitionDefinitionExpression
from ....suggestion import PartitionSchemeChangeSuggestion
from ..expression.partition import (
    MariaDBDropPartitionExpression,
    MariaDBPartitionMaxValue,
    MariaDBPartitionValue,
    MariaDBRemovePartitioningExpression,
)
from ._change_plan_common import _PartitionPlan, canonical, params_of, table_for
from ._common import _HASH_WORDS, _SUPPORTED, _MariaDBPartitionSuggestionBase, _word

#: Why adding partitioning to an existing table is unaddressable.
ADD_SCHEME_UNSUPPORTED_REASON = (
    "MariaDB's ADD PARTITION adds a partition to an existing scheme; there is "
    "no expression node for ALTER TABLE ... PARTITION BY, which is what "
    "partitioning an already-existing table would require."
)

#: Why changing method or partition keys is unaddressable.
REBUILD_UNSUPPORTED_REASON = (
    "MariaDB cannot convert a partitioning scheme in place; changing the "
    "method or keys needs a table rebuild with no expression-node chain."
)

_RANGE_LIST_WORDS = frozenset({"RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"})


def _key_names(params: Dict[str, Any]) -> Tuple[str, ...]:
    keys = params.get("keys")
    if not isinstance(keys, (list, tuple)):
        return ()
    result = []
    for key in keys:
        key_params = params_of(key)
        name = key_params.get("name") if key_params is not None else getattr(key, "name", None)
        if not isinstance(name, str) or not name.strip():
            return ()
        result.append(name)
    return tuple(result)


def _bound_values(raw: Any, dialect: Any) -> Optional[Tuple[Any, ...]]:
    """Rebuild partition boundary nodes from a frozen ``less_than``/``in_values``."""
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)):
        return None
    result = []
    for item in raw:
        if isinstance(item, (MariaDBPartitionValue, MariaDBPartitionMaxValue)):
            result.append(item)
            continue
        item_params = params_of(item)
        if item_params is None or "value" not in item_params:
            return None
        result.append(MariaDBPartitionValue(dialect, item_params["value"]))
    return tuple(result)


def _definitions(dialect: Any, params: Dict[str, Any]) -> Optional[Tuple[Any, ...]]:
    """Rebuild inline partition definitions, or ``None`` when not possible."""
    raw = params.get("definitions", params.get("partitions"))
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        return None
    result = []
    for item in raw:
        if isinstance(item, PartitionDefinitionExpression):
            result.append(item)
            continue
        item_params = params_of(item)
        if item_params is None:
            return None
        name = item_params.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        less_than = _bound_values(item_params.get("less_than"), dialect)
        in_values = _bound_values(item_params.get("in_values"), dialect)
        if less_than is None or in_values is None:
            return None
        result.append(
            PartitionDefinitionExpression(
                dialect,
                name,
                less_than=less_than,
                in_values=in_values,
            )
        )
    return tuple(result)


def _count(params: Dict[str, Any]) -> Optional[int]:
    value = params.get("partitions_count", params.get("count"))
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


class MariaDBPartitionSchemeChangeSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Answer a partition-scheme change with real MariaDB partition nodes."""

    def suggest_partition_scheme_change(
        self, point: PartitionSchemeChangeSuggestion
    ) -> PartitionSchemeChangeSuggestion:
        """Return the real statements this point can name, or False/None."""
        table = table_for(self, point.table_name)
        if table is None:
            return PartitionSchemeChangeSuggestion(operations=False)
        old = params_of(point.old_partition) if point.old_partition is not None else None
        new = params_of(point.new_partition) if point.new_partition is not None else None
        if old is None and new is None:
            return PartitionSchemeChangeSuggestion(operations=None)
        if new is None:
            if not getattr(self, "supports_remove_partitioning", lambda: False)():
                return PartitionSchemeChangeSuggestion(operations=False)
            return PartitionSchemeChangeSuggestion(
                operations=(MariaDBRemovePartitioningExpression(self, table),)
            )
        if old is None:
            return PartitionSchemeChangeSuggestion(operations=False)

        word = _word(new.get("method"))
        if word not in _SUPPORTED or _word(old.get("method")) != word:
            return PartitionSchemeChangeSuggestion(operations=False)
        if _key_names(old) != _key_names(new):
            return PartitionSchemeChangeSuggestion(operations=False)
        if canonical(point.old_partition) == canonical(point.new_partition):
            return PartitionSchemeChangeSuggestion(operations=None)

        old_definitions = _definitions(self, old)
        new_definitions = _definitions(self, new)
        if old_definitions is None or new_definitions is None:
            return PartitionSchemeChangeSuggestion(operations=False)

        old_by_name = {definition.name: definition for definition in old_definitions}
        new_by_name = {definition.name: definition for definition in new_definitions}
        dropped_names = [name for name in old_by_name if name not in new_by_name]
        added_definitions = [new_by_name[name] for name in new_by_name if name not in old_by_name]
        if not dropped_names and not added_definitions:
            return self._count_change(old, new, word, table)
        if word not in _RANGE_LIST_WORDS:
            # MariaDB has no ADD/DROP PARTITION for HASH/KEY; folding them is
            # COALESCE, handled by the count path above.
            return PartitionSchemeChangeSuggestion(operations=False)

        operations: List[Any] = []
        if dropped_names:
            cutoff = new.get("cutoff", old.get("cutoff"))
            if cutoff is not None:
                plan = _PartitionPlan(table, old_definitions, cutoff)
                retained = self.suggest_partition_retention(word, plan)
                if retained.operations is False or retained.operations is None:
                    return PartitionSchemeChangeSuggestion(operations=False)
                operations.extend(retained.operations)
            else:
                if not getattr(self, "supports_drop_partition", lambda: False)():
                    return PartitionSchemeChangeSuggestion(operations=False)
                operations.append(MariaDBDropPartitionExpression(self, table, dropped_names))
        if added_definitions:
            plan = _PartitionPlan(table, added_definitions)
            added = self.suggest_partition_add(word, plan)
            if added.operations is False or added.operations is None:
                return PartitionSchemeChangeSuggestion(operations=False)
            operations.extend(added.operations)
        if not operations:
            return PartitionSchemeChangeSuggestion(operations=False)
        return PartitionSchemeChangeSuggestion(operations=tuple(operations))

    def _count_change(
        self, old: Dict[str, Any], new: Dict[str, Any], word: str, table: Any
    ) -> PartitionSchemeChangeSuggestion:
        """Reuse COALESCE when a HASH/KEY scheme has fewer partitions."""
        old_count, new_count = _count(old), _count(new)
        if (
            word in _HASH_WORDS
            and old_count is not None
            and new_count is not None
            and new_count < old_count
        ):
            delta = old_count - new_count
            altered = self.suggest_partition_table_alter(
                word, _PartitionPlan(table, (), count=delta)
            )
            if altered.operations is False or altered.operations is None:
                return PartitionSchemeChangeSuggestion(operations=False)
            return PartitionSchemeChangeSuggestion(operations=tuple(altered.operations))
        return PartitionSchemeChangeSuggestion(operations=False)


__all__ = [
    "ADD_SCHEME_UNSUPPORTED_REASON",
    "REBUILD_UNSUPPORTED_REASON",
    "MariaDBPartitionSchemeChangeSuggestionMixin",
]
