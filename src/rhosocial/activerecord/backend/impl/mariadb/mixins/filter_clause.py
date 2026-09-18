# src/rhosocial/activerecord/backend/impl/mariadb/mixins/filter_clause.py
"""MariaDB FILTER clause support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBFilterClauseMixin:
    """MariaDB FILTER clause support.

    FILTER clause for aggregate functions is supported since MariaDB 10.2.
    """

    def supports_filter_clause(self) -> bool:
        """FILTER clause is supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']


__all__ = ['MariaDBFilterClauseMixin']
