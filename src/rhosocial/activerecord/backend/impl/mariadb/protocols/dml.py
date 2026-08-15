# src/rhosocial/activerecord/backend/impl/mariadb/protocols/dml.py
"""MariaDB-specific DML operations protocol."""

from typing import Any, Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBDMLOperationSupport(Protocol):
    """MariaDB-specific DML operations protocol.

    Feature Source: MariaDB native (not SQL standard)

    MariaDB DML features beyond SQL standard:
    - INSERT IGNORE: Silently ignore rows that would cause duplicate key errors
    - REPLACE INTO: Delete and re-insert on duplicate key (changes AUTO_INCREMENT)
    - LOAD DATA INFILE: High-performance bulk data import
    - INSERT ... RETURNING: Insert and return values (MariaDB 10.5+)

    Official Documentation:
    - INSERT: https://mariadb.com/kb/en/insert/
    - REPLACE: https://mariadb.com/kb/en/replace/
    - LOAD DATA: https://mariadb.com/kb/en/load-data-infile/

    Version Requirements:
    - INSERT IGNORE: All MariaDB versions
    - REPLACE INTO: All MariaDB versions
    - LOAD DATA INFILE: All MariaDB versions
    """

    def supports_insert_ignore(self) -> bool:
        """Whether INSERT IGNORE is supported.

        MariaDB supports INSERT IGNORE to silently ignore rows that would
        cause duplicate key errors instead of raising an error.
        """
        ...

    def supports_replace_into(self) -> bool:
        """Whether REPLACE INTO is supported.

        MariaDB supports REPLACE INTO which deletes and re-inserts on
        duplicate key. Note: AUTO_INCREMENT value changes on replacement.
        """
        ...

    def supports_load_data(self) -> bool:
        """Whether LOAD DATA INFILE is supported.

        MariaDB supports LOAD DATA INFILE for high-performance bulk data
        import from files. LOCAL variant reads files from the client.
        """
        ...

    def format_load_data_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format LOAD DATA INFILE statement.

        Args:
            expr: MariaDBLoadDataExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_on_conflict_clause(self, expr: Any) -> Tuple[str, tuple]:
        """Format ON DUPLICATE KEY UPDATE clause (MariaDB upsert).

        MariaDB uses ON DUPLICATE KEY UPDATE (same as MySQL) instead of
        the SQL-standard ON CONFLICT clause for upsert operations.

        Args:
            expr: OnConflictExpression or equivalent instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def supports_returning_for_insert(self) -> bool:
        """Whether RETURNING is supported for INSERT (MariaDB 10.5+)."""
        ...

    def supports_returning_for_delete(self) -> bool:
        """Whether RETURNING is supported for DELETE (MariaDB 10.5+)."""
        ...

    def supports_returning_for_replace(self) -> bool:
        """Whether RETURNING is supported for REPLACE (MariaDB 10.5+)."""
        ...

    def supports_returning_for_update(self) -> bool:
        """Whether RETURNING is supported for UPDATE.

        MariaDB does NOT support RETURNING for UPDATE.
        """
        ...

    def format_insert_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format INSERT statement with MariaDB-specific options.

        Supports INSERT IGNORE, REPLACE INTO, and RETURNING clause.

        Args:
            expr: InsertExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_replace_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format REPLACE INTO statement.

        Args:
            expr: ReplaceExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
