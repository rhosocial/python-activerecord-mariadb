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

    def supports_materialized_cte(self) -> bool:
        """Whether the ``MATERIALIZED`` / ``NOT MATERIALIZED`` CTE hint exists.

        Measured False on all 19 configured servers (10.2.44 / 10.3.39 /
        10.4.34 / 10.5.29 / 10.6.28 / 10.11.19 / 11.0.6 / 11.1.6 / 11.2.6 /
        11.3.2 / 11.4.13 / 11.7.2 / 11.8.9 / 12.0.2 / 12.1.2 / 12.2.2 /
        12.3.3 / 13.0.2 / 13.1.1): ``WITH c AS MATERIALIZED (...)`` and
        ``WITH c AS NOT MATERIALIZED (...)`` are syntax errors (errno 1064)
        everywhere while the plain ``WITH c AS (...)`` is accepted (sentinel
        rejected). MariaDB 10.6.28's ``sql_yacc.yy`` has 0 ``MATERIALIZED``
        occurrences. Core's ``format_cte_expression`` consults this probe, so
        a requested hint is refused by name; it never renders it.
        """
        return False


__all__ = ['MariaDBCTEMixin']
