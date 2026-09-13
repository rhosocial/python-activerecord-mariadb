# src/rhosocial/activerecord/backend/impl/mariadb/mixins/explain.py
"""MariaDB EXPLAIN support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBExplainMixin:
    """MariaDB EXPLAIN support.

    EXPLAIN ANALYZE and FORMAT=JSON/TRADITIONAL are supported since MariaDB 10.6.
    """

    def supports_explain_analyze(self) -> bool:
        """EXPLAIN ANALYZE is supported since MariaDB 10.6."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT']

    def supports_explain_format(self, format_type: str) -> bool:
        """Check if specific EXPLAIN format is supported since MariaDB 10.6.

        MariaDB supports FORMAT=JSON and FORMAT=TRADITIONAL.
        FORMAT=TREE is MySQL 8.0+ only and not supported by MariaDB.
        """
        if self.version >= MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT']:
            return format_type.upper() in ["JSON", "TRADITIONAL"]
        return False


__all__ = ['MariaDBExplainMixin']
