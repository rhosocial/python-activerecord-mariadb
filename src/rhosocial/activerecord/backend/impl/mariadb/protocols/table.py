# src/rhosocial/activerecord/backend/impl/mariadb/protocols/table.py
"""MariaDB table DDL protocol."""

from typing import Any, Dict, Optional, Protocol, Tuple, runtime_checkable

from rhosocial.activerecord.backend.dialect.protocols import TableSupport


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

    def supports_table_like_syntax(self) -> bool:
        """Whether CREATE TABLE ... LIKE is supported.

        MariaDB supports copying table structure with LIKE syntax.
        """
        ...

    def supports_inline_index(self) -> bool:
        """Whether inline index definitions are supported.

        MariaDB allows INDEX/KEY definitions within CREATE TABLE.
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

    def format_create_table_statement(
        self,
        expr,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement.

        Note: Generic TableSupport protocol defines this interface.
        This MariaDB-specific version documents available options.

        Args:
            expr: CreateTableExpression instance
            dialect_options: MariaDB-specific options:
                - 'engine': Storage engine (InnoDB, MyISAM, Aria, etc.)
                - 'charset': Character set
                - 'collate': Collation
                - 'auto_increment': Initial AUTO_INCREMENT value
                - 'row_format': Row format (DYNAMIC, COMPACT, etc.)
                - 'with_system_versioning': Enable system-versioned tables (MariaDB 10.3+)
                Example: dialect_options={'engine': 'InnoDB', 'charset': 'utf8mb4'}
        """
        ...
