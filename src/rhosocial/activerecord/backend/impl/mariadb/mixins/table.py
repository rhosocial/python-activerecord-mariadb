# src/rhosocial/activerecord/backend/impl/mariadb/mixins/table.py
"""MariaDB table DDL mixin.

MariaDB-specific features:
- ENGINE storage engine selection
- CHARSET/COLLATE character set options
- AUTO_INCREMENT column attribute
- Inline index definitions in CREATE TABLE
- Table-level COMMENT
- CREATE TABLE ... LIKE syntax
"""
from typing import Any, Dict, List, Tuple


class MariaDBTableMixin:
    """MariaDB table DDL implementation.

    MariaDB-specific features:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    """

    def supports_table_like_syntax(self) -> bool:
        """MariaDB supports CREATE TABLE ... LIKE syntax."""
        return True

    def supports_inline_index(self) -> bool:
        """MariaDB allows inline INDEX/KEY definitions."""
        return True

    def supports_storage_engine_option(self) -> bool:
        """MariaDB supports multiple storage engines."""
        return True

    def supports_charset_option(self) -> bool:
        """MariaDB supports CHARSET/COLLATE at table level."""
        return True

    def supports_create_or_replace_table(self) -> bool:
        """Whether CREATE OR REPLACE TABLE is supported.

        MariaDB 10.1+ supports CREATE OR REPLACE TABLE.

        Returns:
            True if MariaDB version >= 10.1.0.
        """
        return self.version >= (10, 1, 0)

    def format_create_table_statement(
        self, expr: "CreateTableExpression"
    ) -> Tuple[str, tuple]:
        """
        Format CREATE TABLE statement for MariaDB.

        This method handles MariaDB-specific syntax including:
        - LIKE syntax (copying table structure)
        - Storage options (ENGINE, CHARSET, COLLATE)
        - Table-level comments

        Args:
            expr: CreateTableExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        # Check for LIKE syntax in dialect_options (highest priority)
        if 'like_table' in expr.dialect_options:
            return self.format_create_table_like(expr)

        # Build standard CREATE TABLE statement
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnConstraintType, TableConstraintType
        )

        all_params: List[Any] = []

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self.format_column_definition_mariadb(col_def, ColumnConstraintType)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        for t_const in expr.table_constraints:
            const_sql, const_params = self.format_table_constraint_mariadb(t_const, TableConstraintType)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        for idx_def in expr.indexes:
            idx_sql = self.format_inline_index_mariadb(idx_def)
            column_parts.append(idx_sql)

        parts.append(f"({', '.join(column_parts)})")

        # Structured TableOptions take precedence over the raw storage_options
        # dict, then the legacy dialect_options["comment"].
        table_opts_sql = self.format_table_options(expr)
        if table_opts_sql:
            parts.append(table_opts_sql)

        if 'comment' in expr.dialect_options and not (
            expr.table_options is not None and expr.table_options.comment
        ):
            escaped_comment = self._escape_sql_string(expr.dialect_options['comment'])
            parts.append(f"COMMENT '{escaped_comment}'")

        return ' '.join(parts), tuple(all_params)








__all__ = ['MariaDBTableMixin']