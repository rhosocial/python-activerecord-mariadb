# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/_common.py
"""Shared helpers, constants and base class for MariaDB's partition suggestions.

The eight partition suggestion mixins answer "how is each partition operation
done here" with expression nodes rather than SQL text. They all read the same
caller-owned, engine-neutral ``plan`` shape and build the same ``PARTITION BY``
clauses, so that shared knowledge lives here: the normalisation/field helpers,
the supported-strategy words, the clause builder, and a common base class the
eight mixins inherit.

MariaDB mirrors MySQL's partitioning grammar. The clause/statement nodes come
from this backend's ``expression.partition`` module; the suggestion value
objects and the generic ``DROP TABLE`` statement come from core.

Each mixin keeps only its own ``suggest_partition_<x>()`` method plus that
method's dedicated imports. Behaviour is unchanged by the split.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from ....expression import Column
from ....expression.objects import Table
from ..expression.partition import (
    MariaDBPartitionByHash,
    MariaDBPartitionByKey,
    MariaDBPartitionByList,
    MariaDBPartitionByListColumns,
    MariaDBPartitionByRange,
    MariaDBPartitionByRangeColumns,
)

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
    """Return the normalised ``PARTITION BY`` word for a strategy value.

    A strategy is now an expression node (``PartitionByClause``), which carries
    its word in ``.word``/``.method``. A legacy string enum carries it in
    ``.value`` and a bare word is itself; all three spell the same word.
    """
    value = getattr(strategy, "word", None)
    if not isinstance(value, str):
        value = getattr(strategy, "method", None)
    if not isinstance(value, str):
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


class _MariaDBPartitionSuggestionBase:
    """Common base for MariaDB's eight partition suggestion mixins.

    It carries the shared plan-reading helpers above (as module functions,
    used explicitly with the dialect) so every suggestion reads the same plan
    shape; it adds no protocol methods of its own.
    """
