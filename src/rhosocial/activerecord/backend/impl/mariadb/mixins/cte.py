# src/rhosocial/activerecord/backend/impl/mariadb/mixins/cte.py
"""MariaDB CTE support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBCTEMixin:
    """MariaDB CTE (Common Table Expression) support.

    Basic and recursive CTEs are supported since MariaDB 10.2.
    """

    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['CTE']

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['CTE']


__all__ = ['MariaDBCTEMixin']
