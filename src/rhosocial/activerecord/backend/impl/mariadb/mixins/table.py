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
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        ColumnDefinition,
        IndexDefinition,
        TableConstraint,
    )


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

    def supports_create_table_like(self) -> bool:
        """MariaDB supports CREATE TABLE ... LIKE syntax."""
        return True

    def format_create_table_like_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE by delegating to the generic renderer.

        MariaDB uses the generic vendor form
        ``CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <t> LIKE <src>`` provided by
        the core ``TableMixin``; this override only forwards to it so that the
        MariaDB-specific mixin satisfies the protocol it advertises.
        """
        return super().format_create_table_like_statement(expr)

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

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement for MariaDB.

        Handles MariaDB-specific syntax including:
        - Inline index definitions
        - Storage options (ENGINE, CHARSET, COLLATE)
        - Table-level comments
        - AUTO_INCREMENT in column definitions
        """
        all_params: List[Any] = []

        options_part = ""
        table_options = getattr(expr, "table_options", None)
        if table_options is not None:
            options_sql, options_params = table_options.to_sql()
            if options_sql:
                options_part = options_sql
            all_params.extend(options_params)
        parts = ["CREATE"]
        if options_part:
            parts.append(options_part)
        if expr.temporary:
            parts.append("TEMPORARY")
        parts.append("TABLE")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self.format_column_definition(col_def)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        for t_const in expr.table_constraints:
            const_sql, const_params = self.format_table_constraint(t_const)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        for idx_def in expr.indexes:
            idx_sql, idx_params = self.format_inline_index(idx_def)
            column_parts.append(idx_sql)
            all_params.extend(idx_params)

        parts.append(f"({', '.join(column_parts)})")

        if expr.storage_options:
            storage_sql = self._format_storage_options(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        table_options = getattr(expr, "table_options", None)
        if table_options is not None and getattr(table_options, "comment", None):
            comment_sql, _ = self.format_table_comment(table_options.comment)
            parts.append(comment_sql)
        elif 'comment' in expr.dialect_options:
            comment_sql, _ = self.format_table_comment(expr.dialect_options['comment'])
            parts.append(comment_sql)

        dialect_options = getattr(expr, "dialect_options", {}) or {}
        if "engine" in dialect_options:
            parts.append(f"ENGINE={self.inline_sql_literal(dialect_options['engine'])}")
        if "charset" in dialect_options:
            parts.append(f"DEFAULT CHARSET={self.inline_sql_literal(dialect_options['charset'])}")
        if "collate" in dialect_options:
            parts.append(f"COLLATE={self.inline_sql_literal(dialect_options['collate'])}")

        return ' '.join(parts), tuple(all_params)

    def format_column_definition(
        self,
        col_def: "ColumnDefinition",
    ) -> Tuple[str, tuple]:
        """Format a single column definition with MariaDB-specific syntax."""
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType
        
        type_sql, type_params = col_def.data_type.to_sql()
        parts = [self.format_identifier(col_def.name), type_sql]
        params: List[Any] = list(type_params)

        constraint_parts = []
        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                constraint_parts.append("PRIMARY KEY")
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                constraint_parts.append("NOT NULL")
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                constraint_parts.append("UNIQUE")
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                if constraint.default_value is not None:
                    from rhosocial.activerecord.backend.expression import bases
                    if isinstance(constraint.default_value, bases.BaseExpression):
                        default_sql, default_params = constraint.default_value.to_sql()
                        constraint_parts.append(f"DEFAULT {default_sql}")
                        params.extend(default_params)
                    elif isinstance(constraint.default_value, str):
                        escaped = self._escape_sql_string(constraint.default_value)
                        constraint_parts.append(f"DEFAULT '{escaped}'")
                    else:
                        constraint_parts.append(f"DEFAULT {constraint.default_value}")
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                constraint_parts.append("NULL")

            if constraint.is_auto_increment:
                constraint_parts.append("AUTO_INCREMENT")

        if constraint_parts:
            parts.append(' '.join(constraint_parts))

        if col_def.comment:
            escaped_comment = self._escape_sql_string(col_def.comment)
            parts.append(f"COMMENT '{escaped_comment}'")

        return ' '.join(parts), tuple(params)

    def format_table_constraint(
        self,
        t_const: "TableConstraint",
    ) -> Tuple[str, tuple]:
        """Format a table-level constraint."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraintType
        
        parts = []
        params: List[Any] = []

        if t_const.name:
            parts.append(f"CONSTRAINT {self.format_identifier(t_const.name)}")

        if t_const.constraint_type == TableConstraintType.PRIMARY_KEY:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.UNIQUE:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"UNIQUE ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.FOREIGN_KEY:
            if t_const.columns and t_const.foreign_key_table and t_const.foreign_key_columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                ref_cols_str = ', '.join(
                    self.format_identifier(c) for c in t_const.foreign_key_columns
                )
                ref_table = self.format_identifier(t_const.foreign_key_table)
                parts.append(
                    f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table} ({ref_cols_str})"
                )

        return ' '.join(parts), tuple(params)

    def format_inline_index(self, idx_def: "IndexDefinition") -> Tuple[str, tuple]:
        """Format an inline index definition (MariaDB-specific)."""
        parts = []

        if idx_def.unique:
            parts.append("UNIQUE")

        parts.append("INDEX")
        parts.append(self.format_identifier(idx_def.name))

        cols_str = ', '.join(self.format_identifier(c) for c in idx_def.columns)
        parts.append(f"({cols_str})")

        if idx_def.type:
            parts.append(f"USING {idx_def.type}")

        return ' '.join(parts), ()

    def _format_storage_options(self, storage_options: Dict[str, Any]) -> str:
        parts = []
        for key, value in storage_options.items():
            rendered = self.inline_sql_literal(value)
            parts.append(f"{key}={rendered}")
        return ' '.join(parts)


__all__ = ['MariaDBTableMixin']