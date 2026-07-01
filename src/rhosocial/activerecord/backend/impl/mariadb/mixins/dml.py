# src/rhosocial/activerecord/backend/impl/mariadb/mixins/dml.py
"""MariaDB DML operations mixin.

MariaDB-specific DML operations including INSERT IGNORE, REPLACE INTO,
LOAD DATA INFILE, and RETURNING clause support.
"""
from typing import Any, List, Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        InsertExpression,
    )


class MariaDBDMLOperationMixin:
    """MariaDB-specific DML operations mixin.

    MariaDB DML features beyond SQL standard:
    - INSERT IGNORE: Silently ignore rows that would cause errors
    - REPLACE INTO: Delete and re-insert on duplicate key
    - LOAD DATA INFILE: High-performance bulk data import
    - RETURNING clause: Return data from affected rows (10.5+)

    Version Requirements:
    - INSERT IGNORE: All MariaDB versions
    - REPLACE INTO: All MariaDB versions
    - LOAD DATA INFILE: All MariaDB versions
    - RETURNING: MariaDB 10.5+
    """

    def supports_insert_ignore(self) -> bool:
        """Whether INSERT IGNORE is supported.

        MariaDB supports INSERT IGNORE in all versions.

        Returns:
            True.
        """
        return True

    def supports_replace_into(self) -> bool:
        """Whether REPLACE INTO is supported.

        MariaDB supports REPLACE INTO in all versions.

        Returns:
            True.
        """
        return True

    def supports_load_data(self) -> bool:
        """Whether LOAD DATA INFILE is supported.

        MariaDB supports LOAD DATA INFILE in all versions.

        Returns:
            True.
        """
        return True

    def supports_returning_for_insert(self) -> bool:
        """Whether RETURNING is supported for INSERT.

        MariaDB 10.5+ supports RETURNING for INSERT.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_for_delete(self) -> bool:
        """Whether RETURNING is supported for DELETE.

        MariaDB 10.5+ supports RETURNING for DELETE.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_for_replace(self) -> bool:
        """Whether RETURNING is supported for REPLACE.

        MariaDB 10.5+ supports RETURNING for REPLACE.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_for_update(self) -> bool:
        """Whether RETURNING is supported for UPDATE.

        MariaDB does NOT support RETURNING for UPDATE.

        Returns:
            False.
        """
        return False

    def format_insert_statement(
        self,
        expr: "InsertExpression"
    ) -> Tuple[str, tuple]:
        """Format INSERT statement with MariaDB-specific options.

        Extends the base implementation to support:
        - INSERT IGNORE via dialect_options={'ignore': True}
        - REPLACE INTO via dialect_options={'replace': True}
        - RETURNING clause (10.5+)

        Args:
            expr: InsertExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            ValueError: If both 'ignore' and 'replace' are specified,
                       or if 'replace' is used with 'on_conflict'.
        """
        if self.strict_validation:
            expr.validate(strict=True)

        is_replace = expr.dialect_options.get('replace', False)
        is_ignore = expr.dialect_options.get('ignore', False)

        if is_replace and is_ignore:
            raise ValueError("Cannot use both 'replace' and 'ignore' options together")

        if is_replace and expr.on_conflict:
            raise ValueError("REPLACE INTO does not support ON CONFLICT clause")

        all_params: List[Any] = []
        table_sql, table_params = expr.into.to_sql()
        all_params.extend(table_params)

        if is_replace:
            parts = ["REPLACE INTO"]
        else:
            parts = ["INSERT"]
            if is_ignore:
                parts.append("IGNORE")
            parts.append("INTO")
        parts.append(table_sql)

        columns_sql = ""
        if expr.columns:
            columns_sql = "(" + ", ".join([self.format_identifier(c) for c in expr.columns]) + ")"
            parts.append(columns_sql)

        from rhosocial.activerecord.backend.expression.statements import (
            DefaultValuesSource, ValuesSource, SelectSource
        )

        if isinstance(expr.source, DefaultValuesSource):
            parts.append("DEFAULT VALUES")
        elif isinstance(expr.source, ValuesSource):
            all_rows_sql = []
            for row in expr.source.values_list:
                row_sql, row_params = [], []
                for val in row:
                    s, p = val.to_sql()
                    row_sql.append(s)
                    row_params.extend(p)
                all_rows_sql.append(f"({', '.join(row_sql)})")
                all_params.extend(row_params)
            parts.append("VALUES " + ", ".join(all_rows_sql))
        elif isinstance(expr.source, SelectSource):
            s_sql, s_params = expr.source.select_query.to_sql()
            parts.append(s_sql)
            all_params.extend(s_params)

        sql = ' '.join(parts)

        if expr.on_conflict:
            conflict_sql, conflict_params = expr.on_conflict.to_sql()
            sql += f" {conflict_sql}"
            all_params.extend(conflict_params)

        if expr.returning:
            if not self.supports_returning_for_insert():
                from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name,
                    "RETURNING clause",
                    "RETURNING clause for INSERT requires MariaDB 10.5 or later."
                )
            returning_sql, returning_params = self.format_returning_clause_from_obj(expr.returning)
            sql += f" {returning_sql}"
            all_params.extend(returning_params)

        return sql, tuple(all_params)

    def format_on_conflict_clause(self, expr: Any) -> Tuple[str, tuple]:
        """Format ON DUPLICATE KEY UPDATE clause (MariaDB upsert).

        Args:
            expr: OnConflictExpression or equivalent instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return expr.to_sql()

    def format_load_data_statement(self, expr) -> Tuple[str, tuple]:
        """Format LOAD DATA INFILE statement.

        Args:
            expr: LoadDataExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr.validate(strict=self.strict_validation)

        parts = ["LOAD DATA"]

        if expr.options.local:
            parts.append("LOCAL")

        parts.append("INFILE")

        file_path_escaped = expr.file_path.replace("\\", "\\\\").replace("'", "\\'")
        parts.append(f"'{file_path_escaped}'")

        if expr.options.replace:
            parts.append("REPLACE")
        elif expr.options.ignore:
            parts.append("IGNORE")

        parts.append("INTO TABLE")
        parts.append(self.format_identifier(expr.table))

        if expr.options.character_set:
            parts.append(f"CHARACTER SET {expr.options.character_set}")

        field_parts = []
        if expr.options.fields_terminated_by is not None:
            field_parts.append(f"TERMINATED BY '{expr.options.fields_terminated_by}'")
        if expr.options.fields_enclosed_by is not None:
            field_parts.append(f"ENCLOSED BY '{expr.options.fields_enclosed_by}'")
        if expr.options.fields_escaped_by is not None:
            field_parts.append(f"ESCAPED BY '{expr.options.fields_escaped_by}'")
        if field_parts:
            parts.append("FIELDS " + " ".join(field_parts))

        line_parts = []
        if expr.options.lines_terminated_by is not None:
            line_parts.append(f"TERMINATED BY '{expr.options.lines_terminated_by}'")
        if expr.options.lines_starting_by is not None:
            line_parts.append(f"STARTING BY '{expr.options.lines_starting_by}'")
        if line_parts:
            parts.append("LINES " + " ".join(line_parts))

        if expr.options.ignore_lines:
            parts.append(f"IGNORE {expr.options.ignore_lines} LINES")

        if expr.options.column_list:
            cols = ", ".join(self.format_identifier(c) for c in expr.options.column_list)
            parts.append(f"({cols})")

        if expr.options.set_assignments:
            set_parts = []
            for col, val in expr.options.set_assignments.items():
                set_parts.append(f"{self.format_identifier(col)} = {val}")
            parts.append("SET " + ", ".join(set_parts))

        return ' '.join(parts), ()

    def format_replace_statement(self, expr) -> Tuple[str, tuple]:
        """Format REPLACE INTO statement.

        REPLACE INTO is a MariaDB/MySQL extension that either:
        - Inserts a new row if the primary key doesn't exist
        - Deletes the existing row and inserts a new one if the primary key exists

        Note: AUTO_INCREMENT value changes on replacement.

        Args:
            expr: ReplaceExpression instance (similar to InsertExpression).

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        all_params: List[Any] = []
        table_sql, table_params = expr.into.to_sql()
        all_params.extend(table_params)

        parts = ["REPLACE INTO", table_sql]

        columns_sql = ""
        if expr.columns:
            columns_sql = "(" + ", ".join([self.format_identifier(c) for c in expr.columns]) + ")"
            parts.append(columns_sql)

        from rhosocial.activerecord.backend.expression.statements import (
            DefaultValuesSource, ValuesSource, SelectSource
        )

        if isinstance(expr.source, DefaultValuesSource):
            parts.append("DEFAULT VALUES")
        elif isinstance(expr.source, ValuesSource):
            all_rows_sql = []
            for row in expr.source.values_list:
                row_sql, row_params = [], []
                for val in row:
                    s, p = val.to_sql()
                    row_sql.append(s)
                    row_params.extend(p)
                all_rows_sql.append(f"({', '.join(row_sql)})")
                all_params.extend(row_params)
            parts.append("VALUES " + ", ".join(all_rows_sql))
        elif isinstance(expr.source, SelectSource):
            s_sql, s_params = expr.source.select_query.to_sql()
            parts.append(s_sql)
            all_params.extend(s_params)

        sql = ' '.join(parts)

        if expr.returning:
            if not self.supports_returning_for_replace():
                from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name,
                    "RETURNING clause",
                    "RETURNING clause for REPLACE requires MariaDB 10.5 or later."
                )
            returning_sql, returning_params = self.format_returning_clause_from_obj(expr.returning)
            sql += f" {returning_sql}"
            all_params.extend(returning_params)

        return sql, tuple(all_params)


__all__ = ['MariaDBDMLOperationMixin']
