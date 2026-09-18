# src/rhosocial/activerecord/backend/impl/mariadb/mixins/upsert.py
"""MariaDB upsert support mixin."""


class MariaDBUpsertMixin:
    """MariaDB UPSERT (ON DUPLICATE KEY UPDATE) support."""

    def supports_upsert(self) -> bool:
        """UPSERT (ON DUPLICATE KEY UPDATE) is supported."""
        return True

    def get_upsert_syntax_type(self) -> str:
        """MariaDB uses ON DUPLICATE KEY UPDATE syntax."""
        return "ON DUPLICATE KEY"


__all__ = ['MariaDBUpsertMixin']
