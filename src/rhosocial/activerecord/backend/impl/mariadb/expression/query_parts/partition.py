# src/rhosocial/activerecord/backend/impl/mariadb/expression/query_parts/partition.py
"""MariaDB ``PARTITION BY`` query parts.

The clause nodes that spell the partition strategy and its boundaries.
The ``ALTER TABLE`` partition operations live in ``..operators.partition``.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Any, Optional, Sequence, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases.bases import BaseExpression
from rhosocial.activerecord.backend.expression.statements import (
    PartitionClause,
    PartitionDefinitionExpression,
    SubpartitionDefinitionExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


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
    """A boundary value used in MariaDB partition definitions."""

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


def _subpartition_strategy_word(strategy: Any) -> str:
    """The normalized word a subpartition strategy spelling carries.

    A member of the strategy enum carries its word in ``.value``; a bare word
    is itself. The two are told apart by type, not by probing attribute names,
    so a word that happens to look like an attribute name is still just a word.
    Nothing is judged here. An unrecognised word is carried as a word, and
    ``RANGE`` / ``LIST`` name a capability MariaDB does not have; both are
    refused where the answer belongs, by the formatter, so a constructor
    always collects.
    """
    word = strategy.value if isinstance(strategy, Enum) else strategy
    return " ".join(str(word).strip().upper().split())


class MariaDBSubpartitionClause(BaseExpression):
    """MariaDB ``SUBPARTITION BY {HASH|KEY}(...) SUBPARTITIONS N`` clause.

    Appears after ``PARTITION BY ...`` and before the partition definitions.
    When ``definitions`` is provided, those explicit subpartition names
    override the template for each parent partition.

    The constructor only collects. Which strategies MariaDB accepts is a
    capability question answered by the formatter: ``RANGE`` / ``LIST``
    subpartitioning is refused there with ``UnsupportedFeatureError``, and a
    missing column list or a non-positive count is refused by
    :meth:`check_renderable` with ``TypeError``.
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
        word = _subpartition_strategy_word(strategy)
        try:
            self.strategy = MariaDBSubpartitionStrategy(word)
        except ValueError:
            # Collect only: an unrecognised word is carried as the word it is,
            # and the formatter refuses it by name at render time.
            self.strategy = word
        self.expression = expression
        self.count = count
        self.definitions = list(definitions) if definitions else None

    def check_renderable(self) -> None:
        """The clause needs a column list and a positive subpartition count."""
        if not isinstance(self.expression, BaseExpression):
            raise TypeError(
                f"{type(self).__name__} requires an expression (column list), got "
                f"{type(self.expression).__name__}"
            )
        if self.count is not None and (not isinstance(self.count, int) or self.count <= 0):
            raise TypeError(
                f"{type(self).__name__}.count must be a positive integer when provided, "
                f"got {self.count!r}"
            )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_subpartition_clause"


def _partition_word(method: Any) -> Optional[str]:
    """The normalized ``PARTITION BY`` word a strategy value carries.

    A core clause node -- including MariaDB's own, which mirrors the word in
    ``.word`` -- carries it in ``.method``; a legacy string enum carries it in
    ``.value``; a bare word is itself. Which of these a value is follows from
    its type, so no attribute name is probed at run time.
    """
    if isinstance(method, Enum):
        value = method.value
    elif isinstance(method, PartitionClause):
        value = method.method
    elif isinstance(method, str):
        value = method
    else:
        return None
    if not isinstance(value, str):
        return None
    return " ".join(value.strip().upper().split()) or None


class MariaDBPartitionClause(PartitionClause):
    """Base MariaDB partition clause, carrying a plain strategy word.

    MariaDB spells eight ``PARTITION BY`` words, so the clause validates the
    word against :data:`_MARIADB_PARTITION_WORDS` instead of a strategy enum.
    A core strategy clause (``PartitionByRangeClause`` and friends) carries its
    word in ``.method``; a legacy string enum in ``.value``; and a bare word is
    itself. All three spell the same ``PARTITION BY`` word.

    The constructor only collects. Whether the word is one MariaDB spells,
    and whether the key list can carry the clause, is answered by
    :meth:`check_renderable` when SQL is asked for.
    """

    #: Whether an empty key list is a legal payload. ``PARTITION BY KEY()``
    #: means "use all primary-key columns", so only the KEY forms allow it.
    ALLOWS_EMPTY_KEYS = False

    #: Declared once here so every form has the attribute; the RANGE and LIST
    #: forms override it with the clause their caller supplied.
    subpartition_by: Optional["MariaDBSubpartitionClause"] = None

    def __init__(self, dialect: "MariaDBDialect", method: Any, keys: Sequence[BaseExpression]):
        word = _partition_word(method)
        BaseExpression.__init__(self, dialect)
        self.word = word
        self.method = word
        self.keys = list(keys or [])

    def check_renderable(self) -> None:
        """The clause needs a word this dialect spells and its key expressions."""
        if not isinstance(self.method, str) or self.method not in _MARIADB_PARTITION_WORDS:
            raise TypeError(
                "method must be one of %s, got %r" % (sorted(_MARIADB_PARTITION_WORDS), self.method)
            )
        if not self.keys and not type(self).ALLOWS_EMPTY_KEYS:
            raise TypeError("keys are required")
        for key in self.keys:
            if not isinstance(key, BaseExpression):
                raise TypeError(
                    "keys must contain BaseExpression instances, " f"got {type(key).__name__}"
                )
        subpartition_by = self.subpartition_by
        if subpartition_by is not None and not isinstance(
            subpartition_by, MariaDBSubpartitionClause
        ):
            raise TypeError(
                "subpartition_by must be a MariaDBSubpartitionClause, got "
                f"{type(subpartition_by).__name__}"
            )


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

    #: ``KEY()`` is the one partition form whose key list may be empty.
    ALLOWS_EMPTY_KEYS = True

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
]
