# src/rhosocial/activerecord/backend/impl/mariadb/mixins/generated_column.py
"""MariaDB generated column support mixin."""


class MariaDBGeneratedColumnMixin:
    """MariaDB generated column and auto-increment support."""

    def supports_generated_columns(self) -> bool:
        return True

    def supports_stored_generated_columns(self) -> bool:
        return True

    def supports_virtual_generated_columns(self) -> bool:
        return True

    def supports_auto_increment(self) -> bool:
        return True


__all__ = ['MariaDBGeneratedColumnMixin']
