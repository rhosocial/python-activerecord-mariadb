# src/rhosocial/activerecord/backend/impl/mariadb/mixins/schema.py
"""MariaDB schema DDL mixin."""
from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_schema import (
        CreateSchemaExpression,
        DropSchemaExpression,
    )


class MariaDBSchemaMixin:
    """MariaDB schema DDL support.

    MariaDB's CREATE SCHEMA is synonymous with CREATE DATABASE.
    MariaDB supports IF NOT EXISTS, IF EXISTS, and COMMENT for schemas.
    """

    def supports_schema(self) -> bool:
        """MariaDB treats schema as database (synonym)."""
        return True

    def supports_create_schema(self) -> bool:
        """MariaDB supports CREATE SCHEMA."""
        return True

    def supports_drop_schema(self) -> bool:
        """MariaDB supports DROP SCHEMA."""
        return True

    def supports_schema_if_not_exists(self) -> bool:
        """MariaDB supports CREATE SCHEMA IF NOT EXISTS."""
        return True

    def supports_schema_if_exists(self) -> bool:
        """MariaDB supports DROP SCHEMA IF EXISTS."""
        return True

    def supports_schema_cascade(self) -> bool:
        """MariaDB does not support DROP SCHEMA CASCADE."""
        return False

    def supports_schema_authorization(self) -> bool:
        """MariaDB does not support AUTHORIZATION clause."""
        return False

    def format_create_schema_statement(self, expr: CreateSchemaExpression) -> Tuple[str, tuple]:
        if expr.if_not_exists and not self.supports_schema_if_not_exists():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA IF NOT EXISTS",
                f"{self.name} does not support CREATE SCHEMA IF NOT EXISTS."
            )
        if expr.authorization and not self.supports_schema_authorization():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA AUTHORIZATION",
                f"{self.name} does not support CREATE SCHEMA AUTHORIZATION."
            )
        parts = ["CREATE SCHEMA"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.schema_name))
        return " ".join(parts), ()

    def format_drop_schema_statement(self, expr: DropSchemaExpression) -> Tuple[str, tuple]:
        if expr.if_exists and not self.supports_schema_if_exists():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA IF EXISTS",
                f"{self.name} does not support DROP SCHEMA IF EXISTS."
            )
        if expr.cascade and not self.supports_schema_cascade():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA CASCADE",
                f"{self.name} does not support DROP SCHEMA CASCADE."
            )
        parts = ["DROP SCHEMA"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.schema_name))
        return " ".join(parts), ()


__all__ = ['MariaDBSchemaMixin']
