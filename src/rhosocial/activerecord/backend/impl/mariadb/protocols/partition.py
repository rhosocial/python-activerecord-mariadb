# src/rhosocial/activerecord/backend/impl/mariadb/protocols/partition.py
"""MariaDB table partitioning protocol."""

from typing import Any, Protocol, Sequence, Tuple, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import PartitionSupport


@runtime_checkable
class MariaDBPartitionSupport(PartitionSupport, Protocol):
    """MariaDB table partitioning protocol.

    MariaDB supports partitioning via the storage engine interface.
    This protocol extends the generic PartitionSupport contract with
    MariaDB-specific strategies.

    Version Requirements:
    - MariaDB 10.0+ (partitioning via InnoDB)
    """

    def supports_range_columns_partitioning(self) -> bool:
        """Whether RANGE COLUMNS partitioning is supported."""
        ...

    def supports_list_columns_partitioning(self) -> bool:
        """Whether LIST COLUMNS partitioning is supported."""
        ...

    def supports_key_table_partitioning(self) -> bool:
        """Whether KEY partitioning is supported."""
        ...

    def supports_partition_value_maxvalue(self) -> bool:
        """Whether MAXVALUE partition boundary token is supported."""
        ...

    def supports_remove_partitioning(self) -> bool:
        """Whether ALTER TABLE ... REMOVE PARTITIONING is supported."""
        ...

    def supports_coalesce_partition(self) -> bool:
        """Whether ALTER TABLE ... COALESCE PARTITION is supported."""
        ...

    def supports_exchange_partition(self) -> bool:
        """Whether ALTER TABLE ... EXCHANGE PARTITION is supported."""
        ...

    def format_partition_definition(self, definition: Any) -> Tuple[str, tuple]:
        """Format a MariaDB PARTITION definition."""
        ...

    def format_partition_value(self, expr: Any) -> Tuple[str, tuple]:
        """Format a MariaDB partition boundary value."""
        ...

    def format_add_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... ADD PARTITION."""
        ...

    def format_drop_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... DROP PARTITION."""
        ...

    def format_truncate_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... TRUNCATE PARTITION."""
        ...

    def format_reorganize_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... REORGANIZE PARTITION."""
        ...

    def format_exchange_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... EXCHANGE PARTITION."""
        ...

    def format_remove_partitioning_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... REMOVE PARTITIONING."""
        ...

    def format_coalesce_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... COALESCE PARTITION."""
        ...

    def format_partition_name_list(self, partitions: Sequence[str]) -> str:
        """Format a list of partition names."""
        ...
