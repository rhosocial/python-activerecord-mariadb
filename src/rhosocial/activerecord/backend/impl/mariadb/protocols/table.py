# src/rhosocial/activerecord/backend/impl/mariadb/protocols/table.py
"""MariaDB table DDL protocol."""

from typing import Any, Protocol, Tuple, TYPE_CHECKING, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import TableSupport

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        CreateTableLikeExpression,
    )


@runtime_checkable
class MariaDBTableSupport(TableSupport, Protocol):
    """MariaDB table DDL protocol.

    Feature Source: Native support (no extension required)

    MariaDB table features beyond SQL standard:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    - Row format options
    - CREATE OR REPLACE TABLE (MariaDB 10.1+)
    - WITH SYSTEM VERSIONING (MariaDB 10.3+)

    Official Documentation:
    - CREATE TABLE: https://mariadb.com/kb/en/create-table/
    - CREATE TABLE ... LIKE: https://mariadb.com/kb/en/create-table-like/

    Version Requirements:
    - Basic features: All versions
    - Various storage engines: All versions
    - CREATE OR REPLACE TABLE: MariaDB 10.1+
    - System-versioned tables: MariaDB 10.3+
    """

    def supports_create_table_like(self) -> bool:
        """Whether CREATE TABLE ... LIKE is supported.

        MariaDB supports copying table structure with LIKE syntax.
        """
        ...

    def supports_storage_engine_option(self) -> bool:
        """Whether ENGINE option is supported.

        MariaDB supports multiple storage engines (InnoDB, MyISAM, Aria, etc.).
        """
        ...

    def supports_charset_option(self) -> bool:
        """Whether CHARSET/COLLATE options are supported.

        MariaDB supports character set and collation at table level.
        """
        ...

    def supports_create_or_replace_table(self) -> bool:
        """Whether CREATE OR REPLACE TABLE is supported (MariaDB 10.1+)."""
        ...

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement.

        Note: The generic TableSupport protocol defines this interface.
        MariaDB-specific table options (``engine`` / ``charset`` /
        ``collate``) are typed fields on ``MariaDBCreateTableOptions``,
        not a ``dialect_options`` bag.
        """
        ...

    def format_create_table_like_statement(
        self, expr: "CreateTableLikeExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE statement."""
        ...

    def format_column_definition(self, col_def) -> Tuple[str, tuple]:
        """Format a column definition (name, type, constraints, comment)."""
        ...

    def format_table_constraint(self, t_const) -> Tuple[str, tuple]:
        """Format a table-level constraint (PRIMARY KEY / UNIQUE / FOREIGN KEY)."""
        ...

    def format_index_definition(self, idx_def: Any) -> Tuple[str, tuple]:
        """Format an inline index definition inside CREATE TABLE."""
        ...
