# src/rhosocial/activerecord/backend/impl/mariadb/mixins/set_operation.py
"""MariaDB set operation support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBSetOperationMixin:
    """MariaDB INTERSECT/EXCEPT support.

    INTERSECT and EXCEPT are supported since MariaDB 10.3.
    """

    def supports_intersect(self) -> bool:
        """INTERSECT is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']

    def supports_except(self) -> bool:
        """EXCEPT is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']

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
