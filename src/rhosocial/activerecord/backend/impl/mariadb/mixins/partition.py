# src/rhosocial/activerecord/backend/impl/mariadb/mixins/partition.py
"""MariaDB table partitioning mixin.

MariaDB supports the same partitioning strategies as MySQL (RANGE, LIST,
HASH, KEY, RANGE COLUMNS, LIST COLUMNS, LINEAR variants, and subpartitioning).
"""

from typing import Any, List, Sequence, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import PartitionClause


class MariaDBPartitionMixin:
    """MariaDB table partitioning implementation."""

    def supports_table_partitioning(self) -> bool:
        return True

    def supports_partitioned_table_creation(self) -> bool:
        return True

    def supports_range_table_partitioning(self) -> bool:
        return True

    def supports_list_table_partitioning(self) -> bool:
        return True

    def supports_hash_table_partitioning(self) -> bool:
        return True

    def supports_key_table_partitioning(self) -> bool:
        return True

    def supports_subpartitioning(self) -> bool:
        return True

    def supports_range_columns_partitioning(self) -> bool:
        return True

    def supports_list_columns_partitioning(self) -> bool:
        return True

    def supports_linear_hash_partitioning(self) -> bool:
        return True

    def supports_linear_key_partitioning(self) -> bool:
        return True

    def supports_add_partition(self) -> bool:
        return True

    def supports_drop_partition(self) -> bool:
        return True

    def supports_truncate_partition(self) -> bool:
        return True

    def supports_reorganize_partition(self) -> bool:
        return True

    def supports_attach_partition(self) -> bool:
        return False

    def supports_detach_partition(self) -> bool:
        return False

    def supports_partition_metadata_introspection(self) -> bool:
        return True

    def supports_partition_definition_options(self) -> bool:
        return True

    def supports_partition_value_maxvalue(self) -> bool:
        return True

    def supports_remove_partitioning(self) -> bool:
        return True

    def supports_coalesce_partition(self) -> bool:
        return True

    def supports_exchange_partition(self) -> bool:
        return True

    def supports_analyze_partition(self) -> bool:
        return True

    def supports_check_partition(self) -> bool:
        return True

    def supports_optimize_partition(self) -> bool:
        return True

    def supports_rebuild_partition(self) -> bool:
        return True

    def supports_repair_partition(self) -> bool:
        return True

    def format_partition_clause(self, expr: "PartitionClause") -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_partition_definition(self, definition: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_partition_value(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_add_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_drop_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_truncate_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_reorganize_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_exchange_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_partition_name_list(self, partitions: Sequence[str]) -> str:
        return ", ".join(self.format_identifier(partition) for partition in partitions)

    def format_remove_partitioning_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_coalesce_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_analyze_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_check_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_optimize_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_rebuild_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_repair_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        raise NotImplementedError("Partition expression formatting requires MariaDB-specific expression classes")

    def format_get_partitions_expression(self, expr: Any) -> Tuple[str, tuple]:
        from rhosocial.activerecord.backend.expression import (
            Column,
            FunctionCall,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryExpression,
            TableExpression,
        )

        partitions = TableExpression(expr.dialect, "PARTITIONS", schema_name="information_schema")
        query = QueryExpression(
            expr.dialect,
            select=[
                Column(expr.dialect, "PARTITION_NAME", alias="name"),
                Column(expr.dialect, "PARTITION_METHOD", alias="method"),
                Column(expr.dialect, "PARTITION_EXPRESSION", alias="expression"),
                Column(expr.dialect, "PARTITION_DESCRIPTION", alias="description"),
                Column(expr.dialect, "TABLE_ROWS", alias="table_rows"),
                Column(expr.dialect, "DATA_LENGTH", alias="data_length"),
                Column(expr.dialect, "INDEX_LENGTH", alias="index_length"),
            ],
            from_=partitions,
            where=LogicalPredicate(
                expr.dialect,
                "AND",
                Column(expr.dialect, "TABLE_SCHEMA") == FunctionCall(expr.dialect, "DATABASE"),
                Column(expr.dialect, "TABLE_NAME") == Literal(expr.dialect, expr.table_name),
                Column(expr.dialect, "PARTITION_NAME").is_not_null(),
            ),
            order_by=OrderByClause(expr.dialect, [(Column(expr.dialect, "PARTITION_NAME"), "ASC")]),
        )
        return query.to_sql()