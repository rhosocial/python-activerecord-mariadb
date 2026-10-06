# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl_view.py
"""MariaDB view support mixin."""


class MariaDBViewMixin:
    """MariaDB view DDL capability checks."""

    def supports_or_replace_view(self) -> bool:
        return True

    def supports_create_or_replace_view(self) -> bool:
        """MariaDB spells the form ``CREATE OR REPLACE VIEW``.

        Core keeps this apart from :meth:`supports_or_replace_view` and gates
        ``CreateViewExpression.replace`` on it, so answering only the former
        leaves the flag refused as unsupported.
        """
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
