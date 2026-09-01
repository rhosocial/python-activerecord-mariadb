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








__all__ = ['MariaDBTableMixin']