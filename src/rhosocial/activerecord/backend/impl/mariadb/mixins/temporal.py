# src/rhosocial/activerecord/backend/impl/mariadb/mixins/temporal.py
"""MariaDB temporal table support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBTemporalMixin:
    """MariaDB system-versioned temporal table support."""

    def supports_temporal_tables(self) -> bool:
        """MariaDB supports system-versioned tables since 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['SYSTEM_VERSIONING']


__all__ = ['MariaDBTemporalMixin']
