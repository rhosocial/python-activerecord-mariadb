# src/rhosocial/activerecord/backend/impl/mariadb/mixins/partition_suggestion.py
"""MariaDB partition lifecycle suggestion mixin.

This is the backend's own answer to "how is each partition operation done
here", stored as expression nodes rather than SQL text. It is the single
source of that knowledge for the eight suggestion points; it does not replace
or edit the maintenance helpers, which remain in place for the retirement
phase.

MariaDB mirrors MySQL's partitioning grammar. The clause/statement nodes come
from this backend's ``expression.partition`` module; the suggestion value
objects and the generic ``DROP TABLE`` statement come from core.

The ``plan`` argument is caller-owned and intentionally opaque (the protocol
keeps it engine-neutral). This mixin reads the fields a MariaDB plan naturally
carries -- ``table``, ``definitions``, ``keys``, ``count``, ``partition``,
``into`` and ``partitions`` -- by attribute or by mapping key, and falls back
to the smallest meaningful expression when a field is absent, so a supported
strategy always has a real answer.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, TYPE_CHECKING

from ....expression import (
    Column,
    DropTableStatement,
    PartitionAddSuggestion,
    PartitionBuildSuggestion,
    PartitionDropSuggestion,
    PartitionMergeSuggestion,
    PartitionRetentionSuggestion,
    PartitionSplitSuggestion,
    PartitionTableAlterSuggestion,
    PartitionTableDropSuggestion,
)
from ....expression.objects import Table
from ..expression.partition import (
    MariaDBAddPartitionExpression,
    MariaDBCoalescePartitionExpression,
    MariaDBDropPartitionExpression,
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
    MariaDBRemovePartitioningExpression,
    MariaDBReorganizePartitionExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

#: The eight words MariaDB spells in ``PARTITION BY``.
_SUPPORTED = frozenset(
    {
        "RANGE",
        "RANGE COLUMNS",
        "LIST",
        "LIST COLUMNS",
        "HASH",
        "LINEAR HASH",
        "KEY",
        "LINEAR KEY",
    }
)

_RANGE_WORDS = frozenset({"RANGE", "RANGE COLUMNS"})
_HASH_WORDS = frozenset({"HASH", "LINEAR HASH", "KEY", "LINEAR KEY"})

#: A harmless default key for strategies that require one but get no plan key.
#: KEY() is legal with an empty list in MariaDB, so it needs no fallback.
_DEFAULT_KEY_NAME = "id"


def _word(strategy: object) -> Optional[str]:
    """Return the normalised ``PARTITION BY`` word for a strategy value."""
    value = getattr(strategy, "value", strategy)
    if not isinstance(value, str):
        return None
    word = " ".join(value.strip().upper().split())
    return word or None


def _field(plan: object, names: Sequence[str], default: Any = None) -> Any:
    """Read the first present field of ``plan``, by attribute or by key."""
    if plan is None:
        return default
    if isinstance(plan, dict):
        for name in names:
            if name in plan:
                return plan[name]
        return default
    for name in names:
        value = getattr(plan, name, None)
        if value is not None:
            return value
    return default


def _table(dialect: Any, plan: object) -> Table:
    """Resolve the plan's target table to a MariaDB-owned ``Table`` object."""
    table = _field(plan, ("table", "table_name"))
    if isinstance(table, Table):
        return table
    if isinstance(table, str) and table.strip():
        return Table(dialect, table)
    # A suggestion still has to name a table; a neutral placeholder keeps the
    # expression constructible when the caller supplies no plan at all.
    return Table(dialect, "partitioned_table")


def _definitions(plan: object) -> tuple:
    """Return the plan's partition definitions in declaration order."""
    definitions = _field(plan, ("definitions", "partitions"), ())
    if definitions is None:
        return ()
    if isinstance(definitions, (str, bytes)):
        return ()
    return tuple(definitions)


def _keys(dialect: Any, plan: object) -> tuple:
    """Return the plan's partition keys as renderable expression nodes."""
    keys = _field(plan, ("keys", "partition_keys", "expression"), ())
    if keys is None:
        return ()
    if isinstance(keys, (str, bytes)) or hasattr(keys, "to_sql"):
        keys = (keys,)
    result = []
    for key in keys:
        if hasattr(key, "to_sql"):
            result.append(key)
        elif isinstance(key, str):
            result.append(Column(dialect, key))
    return tuple(result)


def _count(plan: object, default: int = 1) -> int:
    """Return a positive partition count for COALESCE/HASH clauses."""
    count = _field(plan, ("count", "partitions_count"))
    if isinstance(count, int) and not isinstance(count, bool) and count > 0:
        return count
    return default


def _names(plan: object, definitions: tuple) -> tuple:
    """Return partition names for DROP, from the plan or its definitions."""
    names = _field(plan, ("partition_names", "partitions", "names", "partition"), ())
    if isinstance(names, str) or not isinstance(names, (list, tuple)):
        names = (names,)
    result = []
    for name in names:
        if isinstance(name, str):
            result.append(name)
        elif getattr(name, "name", None):
            result.append(name.name)
    if not result:
        result = [
            definition.name for definition in definitions if getattr(definition, "name", None)
        ]
    return tuple(result)


def _clause(dialect: Any, word: str, keys: tuple, definitions: tuple, count: int) -> Any:
    """Build the MariaDB ``PARTITION BY`` clause node for ``word``."""
    if word == "RANGE":
        return MariaDBPartitionByRange(dialect, keys, partitions=definitions)
    if word == "RANGE COLUMNS":
        return MariaDBPartitionByRangeColumns(dialect, keys, partitions=definitions)
    if word == "LIST":
        return MariaDBPartitionByList(dialect, keys, partitions=definitions)
    if word == "LIST COLUMNS":
        return MariaDBPartitionByListColumns(dialect, keys, partitions=definitions)
    if word == "HASH":
        return MariaDBPartitionByHash(dialect, keys, partitions_count=count)
    if word == "LINEAR HASH":
        return MariaDBPartitionByHash(dialect, keys, partitions_count=count, linear=True)
    if word == "KEY":
        return MariaDBPartitionByKey(dialect, keys, partitions_count=count)
    if word == "LINEAR KEY":
        return MariaDBPartitionByKey(dialect, keys, partitions_count=count, linear=True)
    return None


class MariaDBPartitionSuggestionMixin:
    """MariaDB's eight partition lifecycle suggestions.

    Placed first in the dialect bases so no core mixin can shadow these
    answers. Every operation is a tuple of real expression nodes; ``False``
    means MariaDB has no such mechanism for the strategy, and ``None`` means
    there is nothing to do.
    """

    def suggest_partition_build(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionBuildSuggestion:
        """Suggest the inline ``CREATE TABLE`` partition clause for ``strategy``."""
        word = _word(strategy)
        if word not in _SUPPORTED:
            return PartitionBuildSuggestion(False)
        keys = _keys(self, plan)
        if not keys and word not in ("KEY", "LINEAR KEY"):
            keys = (Column(self, _DEFAULT_KEY_NAME),)
        clause = _clause(self, word, keys, _definitions(plan), _count(plan))
        if clause is None:
            return PartitionBuildSuggestion(False)
        return PartitionBuildSuggestion((clause,))

    def suggest_partition_table_drop(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionTableDropSuggestion:
        """Suggest dropping the whole table; unpartition first where possible."""
        table = _table(self, plan)
        operations = []
        if getattr(self, "supports_remove_partitioning", lambda: True)():
            operations.append(MariaDBRemovePartitioningExpression(self, table))
        operations.append(DropTableStatement(self, table))
        return PartitionTableDropSuggestion(tuple(operations))

    def suggest_partition_table_alter(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionTableAlterSuggestion:
        """Suggest COALESCE for HASH/KEY, REMOVE PARTITIONING for RANGE/LIST."""
        word = _word(strategy)
        table = _table(self, plan)
        if word in _HASH_WORDS:
            if not getattr(self, "supports_coalesce_partition", lambda: True)():
                return PartitionTableAlterSuggestion(False)
            return PartitionTableAlterSuggestion(
                (MariaDBCoalescePartitionExpression(self, table, _count(plan)),)
            )
        if word in ("RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"):
            if not getattr(self, "supports_remove_partitioning", lambda: True)():
                return PartitionTableAlterSuggestion(False)
            return PartitionTableAlterSuggestion(
                (MariaDBRemovePartitioningExpression(self, table),)
            )
        return PartitionTableAlterSuggestion(False)

    def suggest_partition_add(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionAddSuggestion:
        """Suggest the ``ALTER TABLE ... ADD PARTITION`` statement."""
        word = _word(strategy)
        if word not in _SUPPORTED or not getattr(self, "supports_add_partition", lambda: True)():
            return PartitionAddSuggestion(False)
        return PartitionAddSuggestion(
            (MariaDBAddPartitionExpression(self, _table(self, plan), _definitions(plan)),)
        )

    def suggest_partition_drop(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionDropSuggestion:
        """Suggest the ``ALTER TABLE ... DROP PARTITION`` statement."""
        word = _word(strategy)
        if word not in _SUPPORTED or not getattr(self, "supports_drop_partition", lambda: True)():
            return PartitionDropSuggestion(False)
        names = _names(plan, _definitions(plan))
        return PartitionDropSuggestion(
            (MariaDBDropPartitionExpression(self, _table(self, plan), names),)
        )

    def suggest_partition_split(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionSplitSuggestion:
        """Suggest the ``ALTER TABLE ... REORGANIZE PARTITION ... INTO`` statement."""
        word = _word(strategy)
        if (
            word not in _SUPPORTED
            or not getattr(self, "supports_reorganize_partition", lambda: True)()
        ):
            return PartitionSplitSuggestion(False)
        definitions = _definitions(plan)
        target = _field(plan, ("partition", "partition_name", "source", "target"))
        if not isinstance(target, str) or not target.strip():
            target = definitions[-1].name if definitions else "p0"
        into = _field(plan, ("into", "splits", "new_definitions"))
        if not into:
            into = definitions
        return PartitionSplitSuggestion(
            (MariaDBReorganizePartitionExpression(self, _table(self, plan), target, tuple(into)),)
        )

    def suggest_partition_merge(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionMergeSuggestion:
        """MariaDB has no ``MERGE PARTITION`` DDL; answer explicit unsupported.

        Core's ``MergeSupport`` is the unrelated SQL MERGE DML statement. The
        only MariaDB operation that folds partitions is COALESCE (HASH/KEY),
        which is already the table-alter suggestion -- it is not a merge of two
        adjacent RANGE/LIST partitions, so merge is unconditionally false.
        """
        return PartitionMergeSuggestion(False)

    def suggest_partition_retention(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionRetentionSuggestion:
        """Suggest one DROP PARTITION per RANGE definition carrying ``less_than``."""
        word = _word(strategy)
        if word not in _RANGE_WORDS or not getattr(self, "supports_drop_partition", lambda: True)():
            return PartitionRetentionSuggestion(False)
        candidates = [
            definition
            for definition in _definitions(plan)
            if getattr(definition, "less_than", None)
        ]
        if not candidates:
            return PartitionRetentionSuggestion(None)
        table = _table(self, plan)
        return PartitionRetentionSuggestion(
            tuple(
                MariaDBDropPartitionExpression(self, table, (definition.name,))
                for definition in candidates
            )
        )
