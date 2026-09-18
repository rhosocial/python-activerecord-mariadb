# src/rhosocial/activerecord/backend/impl/mariadb/mixins/grouping.py
"""MariaDB advanced grouping support mixin."""


class MariaDBGroupingMixin:
    """MariaDB ROLLUP/GROUPING SETS support."""

    def supports_rollup(self) -> bool:
        """MariaDB supports ROLLUP with GROUP BY."""
        return True


__all__ = ['MariaDBGroupingMixin']
