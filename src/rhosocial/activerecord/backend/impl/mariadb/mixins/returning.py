# src/rhosocial/activerecord/backend/impl/mariadb/mixins/returning.py
"""MariaDB RETURNING clause mixin.

MariaDB 10.5+ supports RETURNING clause for INSERT, DELETE, and REPLACE statements.
This is a MariaDB-specific feature not available in MySQL.
"""
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import ReturningClause


class MariaDBReturningMixin:
    """MariaDB RETURNING clause support mixin.

    MariaDB 10.5+ supports RETURNING clause for INSERT, DELETE, and
    REPLACE statements, returning data from affected rows.

    Features:
    - RETURNING *: Return all columns
    - RETURNING col1, col2: Return specific columns
    - RETURNING expr AS alias: Return expressions with aliases

    Official Documentation:
    - https://mariadb.com/kb/en/insert-on-duplicate/
    - https://mariadb.com/kb/en/delete/
    - https://mariadb.com/kb/en/replace/

    Version Requirements:
    - MariaDB 10.5.0+

    Comparison with PostgreSQL:
    - PostgreSQL supports RETURNING for INSERT, UPDATE, DELETE, MERGE
    - MariaDB supports RETURNING for INSERT, DELETE, REPLACE (not UPDATE)
    - MariaDB supports RETURNING with ON DUPLICATE KEY UPDATE

    Example:
        INSERT INTO users (name) VALUES ('John') RETURNING id, name;
        DELETE FROM users WHERE id = 1 RETURNING *;
        REPLACE INTO users (id, name) VALUES (1, 'Jane') RETURNING id;
    """

    def supports_returning(self) -> bool:
        """Whether RETURNING clause is supported.

        MariaDB 10.5+ supports RETURNING.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_expression(self) -> bool:
        """Whether expressions are supported in RETURNING.

        MariaDB 10.5+ supports expressions and aliases in RETURNING.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_for_insert(self) -> bool:
        """Whether RETURNING is supported for INSERT.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_for_delete(self) -> bool:
        """Whether RETURNING is supported for DELETE.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_for_replace(self) -> bool:
        """Whether RETURNING is supported for REPLACE.

        Note: REPLACE is a MariaDB/MySQL-specific statement that
        DELETEs and INSERTs on duplicate key.

        Returns:
            True if MariaDB version >= 10.5.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_for_update(self) -> bool:
        """Whether RETURNING is supported for UPDATE.

        Note: MariaDB does NOT support RETURNING for UPDATE statements.
        Only PostgreSQL supports this.

        Returns:
            False (MariaDB does not support RETURNING for UPDATE).
        """
        return False

    def format_returning_clause(
        self,
        columns: Optional[List[str]] = None,
        expressions: Optional[List[Dict[str, Any]]] = None,
        aliases: Optional[Dict[str, str]] = None
    ) -> Tuple[str, tuple]:
        """Format RETURNING clause for MariaDB.

        Args:
            columns: Column names to return.
            expressions: Expressions with optional aliases.
                        Each dict should have 'expression' and optionally 'alias'.
            aliases: Column/expression to alias mappings.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Example:
            >>> dialect.format_returning_clause(columns=['id', 'name'])
            ('RETURNING `id`, `name`', ())
            >>> dialect.format_returning_clause()
            ('RETURNING *', ())
        """
        if not self.supports_returning():
            return "", ()

        items = []

        if columns:
            for col in columns:
                alias = aliases.get(col) if aliases else None
                if alias:
                    items.append(f"{self.format_identifier(col)} AS {self.format_identifier(alias)}")
                else:
                    items.append(self.format_identifier(col))

        if expressions:
            for expr in expressions:
                expr_text = expr.get("expression", "")
                expr_alias = expr.get("alias")
                if expr_alias:
                    items.append(f"{expr_text} AS {self.format_identifier(expr_alias)}")
                else:
                    items.append(expr_text)

        if not items:
            return "RETURNING *", ()

        return f"RETURNING {', '.join(items)}", ()

    def format_returning_clause_from_obj(
        self,
        clause: "ReturningClause"
    ) -> Tuple[str, tuple]:
        """Format RETURNING clause from ReturningClause object.

        Args:
            clause: ReturningClause instance with expressions.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        if not self.supports_returning():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause",
                "RETURNING clause requires MariaDB 10.5 or later. "
                "Use a separate SELECT statement to retrieve the affected data."
            )

        all_params = []
        expr_parts = []

        for expr in clause.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        returning_sql = f"RETURNING {', '.join(expr_parts)}"

        if clause.alias:
            returning_sql += f" AS {self.format_identifier(clause.alias)}"

        return returning_sql, tuple(all_params)


__all__ = ['MariaDBReturningMixin']
