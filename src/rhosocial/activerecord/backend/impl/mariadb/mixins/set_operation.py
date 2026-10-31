# src/rhosocial/activerecord/backend/impl/mariadb/mixins/set_operation.py
"""MariaDB set operation support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBSetOperationMixin:
    """MariaDB INTERSECT/EXCEPT support.

    INTERSECT and EXCEPT are supported since MariaDB 10.3.
    """

    def supports_union(self) -> bool:
        """``UNION`` is accepted on every MariaDB release, including the
        oldest this backend supports: measured on 10.2.44, 10.3.39, 10.4.34,
        10.5.29, 10.6.28, 10.11.19, 11.4.13, 11.7.2, 11.8.9, 12.0.2, 12.1.2,
        12.2.2, 12.3.3, 13.0.2 and 13.1.1, ``SELECT 1 UNION SELECT 2``
        returns ``[(1,), (2,)]`` on each of them. No version gate therefore
        applies, and the core renders the keyword as-is, so no formatter
        override is needed either.
        """
        return True

    def supports_union_all(self) -> bool:
        """``UNION ALL`` keeps the rows a plain ``UNION`` de-duplicates, which
        is what the extra keyword means. Measured beside ``supports_union``
        on the same servers -- 10.2.44 through 13.1.1 -- it is accepted on
        every one of them, so it carries no gate either.
        """
        return True

    def supports_intersect(self) -> bool:
        """INTERSECT is supported since MariaDB 10.3.

        Measured: 10.2.44 refuses ``SELECT 1 INTERSECT SELECT 2`` with errno
        1064 (syntax error), while 10.3.39, 10.4.34, 10.5.29, 10.6.28,
        10.11.19, 11.4.13, 11.7.2, 11.8.9, 12.0.2, 12.1.2, 12.2.2, 12.3.3,
        13.0.2 and 13.1.1 all accept it and return ``[]`` -- 1 and 2 share
        no row, which is exactly an empty intersection.
        """
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT'])

    def supports_except(self) -> bool:
        """EXCEPT is supported since MariaDB 10.3.

        Measured: 10.2.44 refuses ``SELECT 1 EXCEPT SELECT 2`` with errno
        1064 (syntax error), while 10.3.39, 10.4.34, 10.5.29, 10.6.28,
        10.11.19, 11.4.13, 11.7.2, 11.8.9, 12.0.2, 12.1.2, 12.2.2, 12.3.3,
        13.0.2 and 13.1.1 all accept it and return ``[(1,)]`` -- the row the
        first side alone owns, which is what EXCEPT keeps.
        """
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT'])

    def supports_set_operation_order_by(self) -> bool:
        """Set operations support ORDER BY."""
        return True

    def supports_set_operation_limit_offset(self) -> bool:
        """Set operations support LIMIT and OFFSET."""
        return True

    def supports_set_operation_for_update(self) -> bool:
        """Set operations support FOR UPDATE."""
        return True


__all__ = ['MariaDBSetOperationMixin']
