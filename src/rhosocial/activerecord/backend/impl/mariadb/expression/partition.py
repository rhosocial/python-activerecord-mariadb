# src/rhosocial/activerecord/backend/impl/mariadb/expression/partition.py
"""MariaDB partition DDL expressions.

MariaDB implements table partitioning natively through the storage engine
interface using the same ``PARTITION BY`` grammar as its sibling engines.
This module defines MariaDB-owned expression types; it does not depend on any
other backend package. The concrete partition definitions derive from the
generic declarations in ``rhosocial.activerecord.backend.expression.statements``.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Any, Optional, Sequence, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.statements import (
    PartitionClause,
    PartitionDefinition,
    SubpartitionDefinition,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


class MariaDBPartitionStrategy(Enum):
    """MariaDB table partitioning strategies supported by MariaDBPartitionMixin."""

    RANGE = "RANGE"
    RANGE_COLUMNS = "RANGE COLUMNS"
    LIST = "LIST"
    LIST_COLUMNS = "LIST COLUMNS"
    HASH = "HASH"
    LINEAR_HASH = "LINEAR HASH"
    KEY = "KEY"
    LINEAR_KEY = "LINEAR KEY"


class MariaDBSubpartitionStrategy(Enum):
    """MariaDB subpartitioning strategies.

    MariaDB restricts subpartitioning to HASH and KEY (and their LINEAR
    variants) only. RANGE and LIST cannot be used for subpartitioning.
    """

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
        return "format_partition_value"


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


class MariaDBSubpartitionDefinition(SubpartitionDefinition):
    """A single named subpartition within a MariaDB partition definition.

    MariaDB subpartitions carry no explicit boundary (the ``SUBPARTITION BY``
    template applies), so this subclass adds nothing beyond the base name and
    options.
    """


class MariaDBPartitionDefinition(PartitionDefinition):
    """A MariaDB ``PARTITION ... VALUES ...`` definition.

    Derives from the generic ``PartitionDefinition`` and tightens validation:
    MariaDB requires exactly one boundary form (``less_than`` or ``in_values``).

    For single-column LIST COLUMNS, ``in_values`` accepts a flat sequence of
    ``BaseExpression``; for multi-column LIST COLUMNS it accepts a sequence of
    row tuples (each a sequence of ``BaseExpression``).

    Raises:
        ValueError: if both boundaries are provided, or neither is provided.
        TypeError: if ``dialect_options`` is not a dict when provided.
    """

    subpartition_definitions: Optional[Sequence["MariaDBSubpartitionDefinition"]] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.less_than is None and self.in_values is None:
            raise ValueError("partition definition requires less_than or in_values")


class MariaDBPartitionClause(PartitionClause):
    """Base MariaDB partition clause with MariaDB-specific strategy enum."""

    strategy_type = MariaDBPartitionStrategy


class MariaDBPartitionByRange(MariaDBPartitionClause):
    """MariaDB PARTITION BY RANGE expression."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MariaDBPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MariaDBPartitionStrategy.RANGE, keys)
        self.partitions = list(partitions or [])


class MariaDBPartitionByRangeColumns(MariaDBPartitionClause):
    """MariaDB PARTITION BY RANGE COLUMNS expression."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MariaDBPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MariaDBPartitionStrategy.RANGE_COLUMNS, keys)
        self.partitions = list(partitions or [])


class MariaDBPartitionByList(MariaDBPartitionClause):
    """MariaDB PARTITION BY LIST expression."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MariaDBPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MariaDBPartitionStrategy.LIST, keys)
        self.partitions = list(partitions or [])


class MariaDBPartitionByListColumns(MariaDBPartitionClause):
    """MariaDB PARTITION BY LIST COLUMNS expression."""

    def __init__(
        self,
        dialect: "MariaDBDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MariaDBPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MariaDBPartitionStrategy.LIST_COLUMNS, keys)
        self.partitions = list(partitions or [])


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
        method = MariaDBPartitionStrategy.LINEAR_HASH if linear else MariaDBPartitionStrategy.HASH
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
        method = MariaDBPartitionStrategy.LINEAR_KEY if linear else MariaDBPartitionStrategy.KEY
        if keys:
            super().__init__(dialect, method, keys)
        else:
            BaseExpression.__init__(self, dialect)
            self.method = method.value
            self.keys = []
        self.partitions_count = partitions_count
        self.linear = linear


__all__ = [
    "MariaDBPartitionStrategy",
    "MariaDBSubpartitionStrategy",
    "MariaDBPartitionMaxValue",
    "MariaDBPartitionValue",
    "MariaDBSubpartitionDefinition",
    "MariaDBPartitionDefinition",
    "MariaDBPartitionClause",
    "MariaDBPartitionByRange",
    "MariaDBPartitionByRangeColumns",
    "MariaDBPartitionByList",
    "MariaDBPartitionByListColumns",
    "MariaDBPartitionByHash",
    "MariaDBPartitionByKey",
]
