# src/rhosocial/activerecord/backend/impl/mariadb/mixins/partition.py
"""MariaDB table partitioning mixin.

MariaDB supports the same partitioning strategies as MySQL (RANGE, LIST,
HASH, KEY, RANGE COLUMNS, LIST COLUMNS, LINEAR variants, and subpartitioning).
"""

from typing import Any, Sequence, Tuple, TYPE_CHECKING


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
        """Format a MariaDB ``PARTITION BY`` clause.

        Dispatches on the normalized strategy name; the key list and optional
        partition definitions are rendered inline.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if not self.supports_table_partitioning():
            raise UnsupportedFeatureError(self.name, "table partitioning")
        if not self.supports_partitioned_table_creation():
            raise UnsupportedFeatureError(self.name, "partitioned table creation")

        method = expr.method.upper()
        if method == "RANGE":
            return self.format_partition_by_range(expr)
        if method == "RANGE COLUMNS":
            return self.format_partition_by_range_columns(expr)
        if method == "LIST":
            return self.format_partition_by_list(expr)
        if method == "LIST COLUMNS":
            return self.format_partition_by_list_columns(expr)
        if method in {"HASH", "LINEAR HASH"}:
            return self.format_partition_by_hash(expr)
        if method in {"KEY", "LINEAR KEY"}:
            return self.format_partition_by_key(expr)
        raise ValueError(f"Invalid MariaDB partition method: {expr.method}")

    def _format_partition_key_list(self, keys: Sequence[Any]) -> Tuple[str, tuple]:
        key_sql_parts = []
        params: list = []
        for key in keys:
            key_sql, key_params = key.to_sql()
            key_sql_parts.append(key_sql)
            params.extend(key_params)
        return ", ".join(key_sql_parts), tuple(params)

    def _append_partition_definitions(
        self, sql: str, params: list, partitions: Sequence[Any]
    ) -> Tuple[str, tuple]:
        if not partitions:
            return sql, tuple(params)
        definition_sql_parts = []
        for partition in partitions:
            definition_sql, definition_params = self.format_partition_definition(partition)
            definition_sql_parts.append(definition_sql)
            params.extend(definition_params)
        return f"{sql} ({', '.join(definition_sql_parts)})", tuple(params)

    def format_partition_by_range(self, expr: Any) -> Tuple[str, tuple]:
        """Format ``PARTITION BY RANGE (...)`` with optional definitions."""
        if not self.supports_range_table_partitioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "RANGE partitioning")
        keys_sql, params = self._format_partition_key_list(expr.keys)
        sql = f" PARTITION BY RANGE ({keys_sql})"
        return self._append_partition_definitions(sql, list(params), getattr(expr, "partitions", []))

    def format_partition_by_range_columns(self, expr: Any) -> Tuple[str, tuple]:
        """Format ``PARTITION BY RANGE COLUMNS (...)`` with optional definitions."""
        if not self.supports_range_columns_partitioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "RANGE COLUMNS partitioning")
        keys_sql, params = self._format_partition_key_list(expr.keys)
        sql = f" PARTITION BY RANGE COLUMNS ({keys_sql})"
        return self._append_partition_definitions(sql, list(params), getattr(expr, "partitions", []))

    def format_partition_by_list(self, expr: Any) -> Tuple[str, tuple]:
        """Format ``PARTITION BY LIST (...)`` with optional definitions."""
        if not self.supports_list_table_partitioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "LIST partitioning")
        keys_sql, params = self._format_partition_key_list(expr.keys)
        sql = f" PARTITION BY LIST ({keys_sql})"
        return self._append_partition_definitions(sql, list(params), getattr(expr, "partitions", []))

    def format_partition_by_list_columns(self, expr: Any) -> Tuple[str, tuple]:
        """Format ``PARTITION BY LIST COLUMNS (...)`` with optional definitions."""
        if not self.supports_list_columns_partitioning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "LIST COLUMNS partitioning")
        keys_sql, params = self._format_partition_key_list(expr.keys)
        sql = f" PARTITION BY LIST COLUMNS ({keys_sql})"
        return self._append_partition_definitions(sql, list(params), getattr(expr, "partitions", []))

    def format_partition_by_hash(self, expr: Any) -> Tuple[str, tuple]:
        """Format ``PARTITION BY [LINEAR] HASH (...) [PARTITIONS n]``."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if not self.supports_hash_table_partitioning():
            raise UnsupportedFeatureError(self.name, "HASH partitioning")
        linear = expr.method.upper() == "LINEAR HASH"
        if linear and not self.supports_linear_hash_partitioning():
            raise UnsupportedFeatureError(self.name, "LINEAR HASH partitioning")
        keyword = "LINEAR HASH" if linear else "HASH"
        keys_sql, params = self._format_partition_key_list(expr.keys)
        sql = f" PARTITION BY {keyword} ({keys_sql})"
        partitions_count = getattr(expr, "partitions_count", None)
        if partitions_count is not None:
            if not isinstance(partitions_count, int) or partitions_count <= 0:
                raise ValueError("partitions_count must be a positive integer")
            sql = f"{sql} PARTITIONS {partitions_count}"
        return sql, tuple(params)

    def format_partition_by_key(self, expr: Any) -> Tuple[str, tuple]:
        """Format ``PARTITION BY [LINEAR] KEY (...) [PARTITIONS n]``."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if not self.supports_key_table_partitioning():
            raise UnsupportedFeatureError(self.name, "KEY partitioning")
        linear = expr.method.upper() == "LINEAR KEY"
        if linear and not self.supports_linear_key_partitioning():
            raise UnsupportedFeatureError(self.name, "LINEAR KEY partitioning")
        keyword = "LINEAR KEY" if linear else "KEY"
        keys_sql, params = self._format_partition_key_list(expr.keys)
        sql = f" PARTITION BY {keyword} ({keys_sql})"
        partitions_count = getattr(expr, "partitions_count", None)
        if partitions_count is not None:
            if not isinstance(partitions_count, int) or partitions_count <= 0:
                raise ValueError("partitions_count must be a positive integer")
            sql = f"{sql} PARTITIONS {partitions_count}"
        return sql, tuple(params)

    def format_partition_definition(self, definition: Any) -> Tuple[str, tuple]:
        """Format a MariaDB ``PARTITION ... VALUES ...`` definition."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        params: list = []
        parts = ["PARTITION", self.format_identifier(definition.name)]
        if definition.dialect_options and not self.supports_partition_definition_options():
            raise UnsupportedFeatureError(self.name, "partition definition options")

        if definition.less_than is not None:
            value_sql_parts = []
            for value in definition.less_than:
                value_sql, value_params = value.to_sql()
                value_sql_parts.append(value_sql)
                params.extend(value_params)
            parts.append(f"VALUES LESS THAN ({', '.join(value_sql_parts)})")
        elif definition.in_values is not None:
            value_sql_parts = []
            for value in definition.in_values:
                from rhosocial.activerecord.backend.expression.bases import BaseExpression

                if isinstance(value, BaseExpression):
                    value_sql, value_params = value.to_sql()
                    value_sql_parts.append(value_sql)
                    params.extend(value_params)
                else:
                    inner_parts = []
                    for inner in value:
                        inner_sql, inner_params = inner.to_sql()
                        inner_parts.append(inner_sql)
                        params.extend(inner_params)
                    value_sql_parts.append(f"({', '.join(inner_parts)})")
            parts.append(f"VALUES IN ({', '.join(value_sql_parts)})")
        else:
            raise ValueError("partition definition requires less_than or in_values")

        if definition.dialect_options:
            options_sql, options_params = self.format_partition_definition_options(
                definition.dialect_options
            )
            if options_sql:
                parts.append(options_sql)
            params.extend(options_params)

        subpartition_defs = getattr(definition, "subpartition_definitions", None)
        if subpartition_defs:
            if not self.supports_subpartitioning():
                raise UnsupportedFeatureError(self.name, "subpartition definitions")
            sub_parts = []
            for sub_def in subpartition_defs:
                sub_sql, sub_params = self.format_subpartition_definition(sub_def)
                sub_parts.append(sub_sql)
                params.extend(sub_params)
            parts.append(f"({', '.join(sub_parts)})")
        return " ".join(parts), tuple(params)

    def format_partition_definition_options(self, options: dict) -> Tuple[str, tuple]:
        """Format MariaDB partition definition options."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if not self.supports_partition_definition_options():
            raise UnsupportedFeatureError(self.name, "partition definition options")

        parts: list = []
        allowed_options = {
            "engine": "ENGINE",
            "comment": "COMMENT",
            "data_directory": "DATA DIRECTORY",
            "index_directory": "INDEX DIRECTORY",
            "max_rows": "MAX_ROWS",
            "min_rows": "MIN_ROWS",
            "tablespace": "TABLESPACE",
        }
        for key, value in options.items():
            normalized = str(key).lower()
            if normalized not in allowed_options:
                raise ValueError(f"Unsupported partition definition option: {key}")
            keyword = allowed_options[normalized]
            if normalized in {"engine", "tablespace"}:
                if not isinstance(value, str) or not value:
                    raise TypeError(f"{key} option must be a non-empty string")
                parts.append(f"{keyword} {self.format_identifier(value)}")
            elif normalized in {"comment", "data_directory", "index_directory"}:
                if not isinstance(value, str):
                    raise TypeError(f"{key} option must be a string")
                escaped = self._escape_sql_string(value)
                parts.append(f"{keyword} '{escaped}'")
            elif normalized in {"max_rows", "min_rows"}:
                if not isinstance(value, int) or value < 0:
                    raise TypeError(f"{key} option must be a non-negative integer")
                parts.append(f"{keyword} {value}")
        return " ".join(parts), ()

    def format_subpartition_definition(self, definition: Any) -> Tuple[str, tuple]:
        """Format a single ``SUBPARTITION name ...`` clause."""
        if not definition.name or not definition.name.strip():
            raise ValueError("subpartition name must not be empty")
        parts = ["SUBPARTITION", self.format_identifier(definition.name)]
        params: list = []
        if definition.dialect_options:
            options_sql, options_params = self.format_partition_definition_options(
                definition.dialect_options
            )
            if options_sql:
                parts.append(options_sql)
            params.extend(options_params)
        return " ".join(parts), tuple(params)

    def format_partition_value(self, expr: Any) -> Tuple[str, tuple]:
        """Format a MariaDB partition boundary value."""
        from datetime import date, datetime
        from decimal import Decimal
        from math import isfinite

        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
            MariaDBPartitionMaxValue,
        )

        if isinstance(expr, MariaDBPartitionMaxValue):
            if not self.supports_partition_value_maxvalue():
                raise UnsupportedFeatureError(self.name, "MAXVALUE partition boundary")
            return "MAXVALUE", ()
        value = expr.value
        if value is None:
            return "NULL", ()
        if isinstance(value, bool):
            raise TypeError("partition value must not be bool")
        if isinstance(value, int):
            return str(value), ()
        if isinstance(value, float):
            if not isfinite(value):
                raise ValueError("partition value float must be finite")
            return repr(value), ()
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("partition value Decimal must be finite")
            return str(value), ()
        if isinstance(value, datetime):
            escaped = self._escape_sql_string(value.isoformat(sep=" "))
            return f"'{escaped}'", ()
        if isinstance(value, date):
            escaped = self._escape_sql_string(value.isoformat())
            return f"'{escaped}'", ()
        if isinstance(value, str):
            escaped = self._escape_sql_string(value)
            return f"'{escaped}'", ()
        raise TypeError(
            "partition value must be str, int, float, Decimal, "
            f"date, datetime, or None, got {type(value).__name__}"
        )

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

    def format_partition_name_list(self, partitions: Sequence[str]) -> Tuple[str, tuple]:
        return ", ".join(self.format_identifier(partition) for partition in partitions), ()

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