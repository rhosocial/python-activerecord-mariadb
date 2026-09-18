# src/rhosocial/activerecord/backend/impl/mariadb/mixins/join.py
"""MariaDB join support mixin."""


class MariaDBJoinMixin:
    """MariaDB LATERAL join support."""

    def supports_lateral_join(self) -> bool:
        """MariaDB supports LATERAL joins."""
        return True


__all__ = ['MariaDBJoinMixin']
