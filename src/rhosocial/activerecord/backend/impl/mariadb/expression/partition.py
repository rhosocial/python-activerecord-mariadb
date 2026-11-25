# src/rhosocial/activerecord/backend/impl/mariadb/expression/partition.py
"""MariaDB partition DDL expressions.

MariaDB implements table partitioning natively through the storage engine
interface using the same ``PARTITION BY`` grammar as its sibling engines.
This module defines MariaDB-owned expression types; it does not depend on any
other backend package. Partition strategies and definitions are carried by the
expression nodes in ``rhosocial.activerecord.backend.expression.statements``;
MariaDB's clause classes add only the fields its grammar needs (inline
definitions, subpartitioning, partition counts).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Any, Optional, Sequence, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    PartitionClause,
    PartitionDefinitionExpression,
    SubpartitionDefinitionExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


#: The eight words MariaDB spells in ``PARTITION BY``. Strategies are now
#: carried by expression nodes (whose fixed word is one of these) rather than
#: by a strategy enum; this set is the clause layer's closed vocabulary.
_MARIADB_PARTITION_WORDS = frozenset(
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


class MariaDBSubpartitionStrategy(str, Enum):
    """MariaDB subpartitioning strategies.

    MariaDB restricts subpartitioning to HASH and KEY (and their LINEAR
    variants) only. RANGE and LIST cannot be used for subpartitioning.

    A member *is* the word it carries, as in the other partition strategy
    vocabularies; this one stays an enum because subpartitioning is gated by
    name in the formatter.
    """

    #: A member *is* the word it carries (org rules §11.3).
    __str__ = str.__str__

    HASH = "HASH"
    KEY = "KEY"
    LINEAR_HASH = "LINEAR HASH"
    LINEAR_KEY = "LINEAR KEY"


class MariaDBPartitionMaxValue(BaseExpression):
    """MariaDB MAXVALUE partition boundary token."""

    def __init__(self, dialect: "MariaDBDialect"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_max_value"


class MariaDBPartitionValue(BaseExpression):
    """Literal value used in MariaDB partition boundary definitions."""

    def __init__(self, dialect: "MariaDBDialect", value: Any):
        super().__init__(dialect)
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("partition value float must be finite")
        if not isinstance(value, (str, int, float, Decimal, type(None))):
            from datetime import date, datetime

            if not isinstance(value, (date, datetime)):
                raise TypeError(
                    "partition value must be str, int, float, Decimal, "
                    f"date, datetime, or None, got {type(value).__name__}"
                )
        self.value = value

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_value"


def _normalize_subpartition_strategy(
    dialect: "MariaDBDialect",
    strategy: Any,
) -> MariaDBSubpartitionStrategy:
    """Return the strategy member, refusing RANGE/LIST by name.

    MariaDB restricts subpartitioning to HASH and KEY (and their LINEAR
    variants).  ``SUBPARTITION BY RANGE`` is refused with
    ``UnsupportedFeatureError`` rather than silently downgraded to HASH.
    """
    try:
        return MariaDBSubpartitionStrategy(strategy)
    except ValueError as error:
        word = str(strategy).strip().upper()
        if word in {"RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"}:
            raise UnsupportedFeatureError(
                getattr(dialect, "name", "MariaDB"),
                f"SUBPARTITION BY {word}",
                "MariaDB supports only HASH and KEY subpartitioning.",
            ) from error
        raise


class MariaDBSubpartitionClause(BaseExpression):
    """MariaDB ``SUBPARTITION BY {HASH|KEY}(...) SUBPARTITIONS N`` clause.

    Appears after ``PARTITION BY ...`` and before the partition definitions.
    When ``definitions`` is provided, those explicit subpartition names
    override the template for each parent partition.

    Raises:
        ValueError: if strategy is not a MariaDBSubpartitionStrategy word.
        UnsupportedFeatureError: if strategy names RANGE or LIST subpartitioning.
        ValueError: if ``expression`` is missing; MariaDB requires a column
            list for every SUBPARTITION BY HASH/KEY form, including LINEAR.
        ValueError: if count is provided but is not a positive integer.
    """

    def __init__(
        self,
        dialect: "MariaDBDialect",
        strategy: MariaDBSubpartitionStrategy,
        *,
        expression: Optional[BaseExpression] = None,
        count: Optional[int] = None,
        definitions: Optional[Sequence[SubpartitionDefinitionExpression]] = None,
    ):
        super().__init__(dialect)
        self.strategy = _normalize_subpartition_strategy(dialect, strategy)
        if expression is None:
            raise ValueError(
                "SUBPARTITION BY %s requires an expression (column list)" % self.strategy.value
            )
        if count is not None and (not isinstance(count, int) or count <= 0):
            raise ValueError("count must be a positive integer when provided")
        self.expression = expression
        self.count = count
        self.definitions = list(definitions) if definitions else None

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_subpartition_clause"


def _require_subpartition_clause(
    subpartition_by: Optional["MariaDBSubpartitionClause"],
) -> None:
    """Reject a subpartition_by value that is not the MariaDB clause."""
    if subpartition_by is not None and not isinstance(subpartition_by, MariaDBSubpartitionClause):
        raise TypeError("subpartition_by must be a MariaDBSubpartitionClause")


class MariaDBPartitionClause(PartitionClause):
    """Base MariaDB partition clause, carrying a plain strategy word.

    MariaDB spells eight ``PARTITION BY`` words, so the clause validates the
    word against :data:`_MARIADB_PARTITION_WORDS` instead of a strategy enum.
    A core strategy clause (``PartitionByRangeClause`` and friends) carries its
    word in ``.method``/``.word``; a legacy string enum in ``.value``; and a
    bare word is itself. All three spell the same ``PARTITION BY`` word.
    """

    def __init__(self, dialect: "MariaDBDialect", method: Any, keys: Sequence[BaseExpression]):
        word = getattr(method, "word", None)
        if not isinstance(word, str):
            word = getattr(method, "method", None)
        if not isinstance(word, str):
            word = getattr(method, "value", method)
        if not isinstance(word, str):
            word = None
        else:
            word = " ".join(word.strip().upper().split()) or None
        if word not in _MARIADB_PARTITION_WORDS:
            raise TypeError(
                "method must be one of %s, got %r" % (sorted(_MARIADB_PARTITION_WORDS), word)
            )
        if not keys:
            raise ValueError("keys are required")
        for key in keys:
            if not isinstance(key, BaseExpression):
                raise TypeError(
                    "keys must contain BaseExpression instances, " f"got {type(key).__name__}"
                )
        BaseExpression.__init__(self, dialect)
        self.word = word
        self.method = word
        self.keys = list(keys)


class MariaDBPartitionByRange(MariaDBPartitionClause):
    """MariaDB PARTITION BY RANGE expression.

    Supports optional subpartitioning via ``subpartition_by``.
    """

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MariaDBSubpartitionClause] = None,
    ):
        super().__init__(dialect, "RANGE", keys)
        _require_subpartition_clause(subpartition_by)
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


class MariaDBPartitionByRangeColumns(MariaDBPartitionClause):
    """MariaDB PARTITION BY RANGE COLUMNS expression.

    Supports optional subpartitioning via ``subpartition_by``.
    """

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MariaDBSubpartitionClause] = None,
    ):
        super().__init__(dialect, "RANGE COLUMNS", keys)
        _require_subpartition_clause(subpartition_by)
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


class MariaDBPartitionByList(MariaDBPartitionClause):
    """MariaDB PARTITION BY LIST expression.

    Supports optional subpartitioning via ``subpartition_by``.
    """

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MariaDBSubpartitionClause] = None,
    ):
        super().__init__(dialect, "LIST", keys)
        _require_subpartition_clause(subpartition_by)
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


class MariaDBPartitionByListColumns(MariaDBPartitionClause):
    """MariaDB PARTITION BY LIST COLUMNS expression.

    Supports optional subpartitioning via ``subpartition_by``.
    """

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MariaDBSubpartitionClause] = None,
    ):
        super().__init__(dialect, "LIST COLUMNS", keys)
        _require_subpartition_clause(subpartition_by)
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


class MariaDBPartitionByHash(MariaDBPartitionClause):
    """MariaDB PARTITION BY HASH expression."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions_count: Optional[int] = None,
        linear: bool = False,
    ):
        method = "LINEAR HASH" if linear else "HASH"
        super().__init__(dialect, method, keys)
        self.partitions_count = partitions_count
        self.linear = linear


class MariaDBPartitionByKey(MariaDBPartitionClause):
    """MariaDB PARTITION BY KEY expression.

    MariaDB allows empty ``KEY()`` to use all primary key columns as the
    partition key. When ``keys`` is empty or ``None``, this expression
    bypasses the base class key validation (which requires at least one key
    expression) and produces ``PARTITION BY KEY()``.
    """

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Optional[Sequence[BaseExpression]] = None,
        *,
        partitions_count: Optional[int] = None,
        linear: bool = False,
    ):
        method = "LINEAR KEY" if linear else "KEY"
        if keys:
            super().__init__(dialect, method, keys)
        else:
            BaseExpression.__init__(self, dialect)
            self.word = method
            self.method = method
            self.keys = []
        self.partitions_count = partitions_count
        self.linear = linear


class MariaDBPartitionTableExpression(BaseExpression):
    """Base for every ``ALTER TABLE ... <partition action>`` expression.

    A partition statement names one base table, so the target is a
    :class:`Table` rather than a bare string: a string cannot say which
    database it belongs to, and a dropped qualifier would address a different
    table than the caller meant.

    Raises:
        TypeError: if ``table`` is not a :class:`Table`.
    """

    def __init__(self, dialect: "MariaDBDialect", table: Table):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"{type(self).__name__} target must be a Table object, got "
                f"{type(table).__name__}; pass "
                f"Table(dialect, 'users', catalog_name='app') to name a table "
                f"in another database"
            )
        self.table = table


class MariaDBAddPartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... ADD PARTITION``."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        table: Table,
        partitions: Sequence[PartitionDefinitionExpression],
    ):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_add_partition_statement"


class MariaDBDropPartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... DROP PARTITION``."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        table: Table,
        partitions: Sequence[str],
    ):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_partition_statement"


class MariaDBTruncatePartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... TRUNCATE PARTITION``."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        table: Table,
        partitions: Sequence[str],
    ):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_truncate_partition_statement"


class MariaDBReorganizePartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REORGANIZE PARTITION``."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        table: Table,
        partition: str,
        into: Sequence[PartitionDefinitionExpression],
    ):
        super().__init__(dialect, table)
        self.partition = partition
        self.into = list(into)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_reorganize_partition_statement"


class MariaDBRemovePartitioningExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REMOVE PARTITIONING``."""

    def __init__(self, dialect: "MariaDBDialect", table: Table):
        super().__init__(dialect, table)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_remove_partitioning_statement"


class MariaDBCoalescePartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... COALESCE PARTITION``."""

    def __init__(self, dialect: "MariaDBDialect", table: Table, count: int):
        if not isinstance(count, int) or count <= 0:
            raise ValueError("count must be a positive integer")
        super().__init__(dialect, table)
        self.count = count

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_coalesce_partition_statement"


class MariaDBAnalyzePartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... ANALYZE PARTITION``."""

    def __init__(self, dialect: "MariaDBDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_analyze_partition_statement"


class MariaDBCheckPartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... CHECK PARTITION``."""

    def __init__(self, dialect: "MariaDBDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_check_partition_statement"


class MariaDBOptimizePartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... OPTIMIZE PARTITION``."""

    def __init__(self, dialect: "MariaDBDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_optimize_partition_statement"


class MariaDBRebuildPartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REBUILD PARTITION``."""

    def __init__(self, dialect: "MariaDBDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_rebuild_partition_statement"


class MariaDBRepairPartitionExpression(MariaDBPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REPAIR PARTITION``."""

    def __init__(self, dialect: "MariaDBDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_repair_partition_statement"


class MariaDBGetPartitionsExpression(BaseExpression):
    """Expression that queries ``information_schema.PARTITIONS`` for a table.

    ``table_name`` stays a plain string: it is matched against the
    ``TABLE_NAME`` column, not used to name a relation.

    Raises:
        ValueError: if table_name is empty.
    """

    def __init__(self, dialect: "MariaDBDialect", table_name: str):
        super().__init__(dialect)
        if not table_name or not table_name.strip():
            raise ValueError("table_name must not be empty")
        self.table_name = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_get_partitions_expression"


class MariaDBExchangePartitionStatement(BaseExpression):
    """Expression for ``ALTER TABLE ... EXCHANGE PARTITION``.

    The validation clause is a two-spelling alternative, so each spelling has
    its own parameter: ``with_validation`` spells ``WITH VALIDATION`` and
    ``without_validation`` spells ``WITHOUT VALIDATION``. Setting neither
    leaves the clause out, which is the round's rule for an unspecified pair
    (MariaDB's bare form validates at runtime, but the caller did not ask for
    either spelling); setting both is API misuse and raises ``ValueError`` at
    construction.

    The two spellings parse from MariaDB 11.4; every measured earlier version
    rejects them as syntax errors, so the dialect refuses a requested spelling
    by name when its configured version is older. The bare statement itself is
    accepted from 10.2 (the oldest measured version).

    Raises:
        ValueError: if both validation spellings are set.
        TypeError: ``table`` or ``exchange_table`` is not a :class:`Table`. A
            bare string is refused rather than wrapped, because it cannot say
            which database it names and a dropped qualifier would address a
            different table than the caller meant.
    """

    def __init__(
        self,
        dialect: "MariaDBDialect",
        table: Table,
        partition: str,
        exchange_table: Table,
        *,
        with_validation: bool = False,
        without_validation: bool = False,
    ):
        super().__init__(dialect)
        if with_validation and without_validation:
            raise ValueError(
                "with_validation and without_validation are mutually exclusive options"
            )
        if not isinstance(table, Table):
            raise TypeError(
                f"{type(self).__name__} target must be a Table object, got "
                f"{type(table).__name__}; pass "
                f"Table(dialect, 'users', catalog_name='app') to name a table "
                f"in another database"
            )
        if not isinstance(exchange_table, Table):
            raise TypeError(
                "exchange_table must be a Table object, got "
                f"{type(exchange_table).__name__}; pass "
                f"Table(dialect, 'users', catalog_name='app') to name a table "
                f"in another database"
            )
        self.table = table
        self.partition = partition
        self.exchange_table = exchange_table
        self.with_validation = with_validation
        self.without_validation = without_validation

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_exchange_partition_statement"


__all__ = [
    "MariaDBSubpartitionStrategy",
    "MariaDBPartitionMaxValue",
    "MariaDBPartitionValue",
    "MariaDBSubpartitionClause",
    "MariaDBPartitionClause",
    "MariaDBPartitionByRange",
    "MariaDBPartitionByRangeColumns",
    "MariaDBPartitionByList",
    "MariaDBPartitionByListColumns",
    "MariaDBPartitionByHash",
    "MariaDBPartitionByKey",
    "MariaDBPartitionTableExpression",
    "MariaDBAddPartitionExpression",
    "MariaDBDropPartitionExpression",
    "MariaDBTruncatePartitionExpression",
    "MariaDBReorganizePartitionExpression",
    "MariaDBRemovePartitioningExpression",
    "MariaDBCoalescePartitionExpression",
    "MariaDBAnalyzePartitionExpression",
    "MariaDBCheckPartitionExpression",
    "MariaDBOptimizePartitionExpression",
    "MariaDBRebuildPartitionExpression",
    "MariaDBRepairPartitionExpression",
    "MariaDBGetPartitionsExpression",
    "MariaDBExchangePartitionStatement",
]
