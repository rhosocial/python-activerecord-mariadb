# src/rhosocial/activerecord/backend/impl/mariadb/mixins/view.py
"""MariaDB view support mixin."""


class MariaDBViewMixin:
    """MariaDB view DDL capability checks."""

    def supports_or_replace_view(self) -> bool:
        return True

    def supports_temporary_view(self) -> bool:
        return True

    def supports_if_exists_view(self) -> bool:
        return True

    def supports_view_check_option(self) -> bool:
        return True

    def supports_cascade_view(self) -> bool:
        return True


__all__ = ['MariaDBViewMixin']
