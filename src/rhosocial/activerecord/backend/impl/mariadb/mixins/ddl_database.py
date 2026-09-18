# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl_database.py
"""MariaDB database DDL mixin."""
from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_database import (
        AlterDatabaseExpression,
        CreateDatabaseExpression,
        DropDatabaseExpression,
    )


class MariaDBDatabaseMixin:
    """MariaDB database DDL support.

    MariaDB's CREATE SCHEMA is synonymous with CREATE DATABASE.
    MariaDB additionally supports OR REPLACE and RENAME.
    """

    def supports_database(self) -> bool:
        return True

    def supports_create_database(self) -> bool:
        return True

    def supports_drop_database(self) -> bool:
        return True

    def supports_alter_database(self) -> bool:
        return True

    def supports_database_if_not_exists(self) -> bool:
        return True

    def supports_database_if_exists(self) -> bool:
        return True

    def supports_database_encoding(self) -> bool:
        """MariaDB supports CHARACTER SET."""
        return True

    def supports_database_collation(self) -> bool:
        """MariaDB supports COLLATE."""
        return True

    def supports_database_or_replace(self) -> bool:
        """MariaDB supports CREATE OR REPLACE DATABASE."""
        return True

    def format_create_database_statement(
        self, expr: CreateDatabaseExpression
    ) -> Tuple[str, tuple]:
        parts = ["CREATE"]
        if expr.or_replace:
            parts.append("OR REPLACE")
        parts.append("DATABASE")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.database_name))
        if expr.encoding:
            parts.append(f"CHARACTER SET {expr.encoding}")
        if expr.collation:
            parts.append(f"COLLATE {expr.collation}")
        return " ".join(parts), ()

    def format_drop_database_statement(
        self, expr: DropDatabaseExpression
    ) -> Tuple[str, tuple]:
        parts = ["DROP DATABASE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.database_name))
        return " ".join(parts), ()

    def format_alter_database_statement(
        self, expr: AlterDatabaseExpression
    ) -> Tuple[str, tuple]:
        from rhosocial.activerecord.backend.expression.statements.ddl_database import AlterDatabaseAction
        parts = ["ALTER DATABASE"]
        parts.append(self.format_identifier(expr.database_name))
        if expr.action == AlterDatabaseAction.RENAME_TO:
            parts.append(f"RENAME TO {self.format_identifier(expr.target)}")
        elif expr.action == AlterDatabaseAction.CHARACTER_SET:
            parts.append(f"CHARACTER SET {expr.target}")
        elif expr.action == AlterDatabaseAction.COLLATION:
            parts.append(f"COLLATE {expr.target}")
        return " ".join(parts), ()


__all__ = ['MariaDBDatabaseMixin']
