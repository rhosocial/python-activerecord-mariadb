# src/rhosocial/activerecord/backend/impl/mariadb/expression/operators/partition.py
"""MariaDB ``ALTER TABLE`` partition operations.

The ``PARTITION BY`` clause nodes live in ``..query_parts.partition``.
"""

from __future__ import annotations

from typing import Sequence, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import PartitionDefinitionExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MariaDBDialect


class MariaDBPartitionTableExpression(BaseExpression):
    """Base for every ``ALTER TABLE ... <partition action>`` expression.

    A partition statement names one base table, so the target is a
    :class:`Table` rather than a bare string: a string cannot say which
    database it belongs to, and a dropped qualifier would address a different
    table than the caller meant.

    The constructor only collects. That the target is a :class:`Table` is
    checked by :meth:`check_renderable` when SQL is asked for.
    """

    def __init__(self, dialect: "MariaDBDialect", table: Table):
        super().__init__(dialect)
        self.table = table

    def check_renderable(self) -> None:
        """The statement needs a :class:`Table` target."""
        if not isinstance(self.table, Table):
            raise TypeError(
                f"{type(self).__name__} target must be a Table object, got "
                f"{type(self.table).__name__}; pass "
                f"Table(dialect, 'users', catalog_name='app') to name a table "
                f"in another database"
            )



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
        super().__init__(dialect, table)
        self.count = count

    def check_renderable(self) -> None:
        """COALESCE removes partitions, so the count is a positive integer."""
        super().check_renderable()
        if not isinstance(self.count, int) or self.count <= 0:
            raise TypeError("count must be a positive integer")

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
