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

    def supports_restrict_view(self) -> bool:
        """Whether ``DROP VIEW ... RESTRICT`` is supported.

        Measured True on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version
        accepts ``DROP VIEW v RESTRICT`` (sentinel ``... BOGUS`` rejected with
        errno 1064). Core's ``format_drop_view_statement`` consults this probe;
        before this declaration the default ``False`` refused a spelling the
        server accepts.
        """
        return True


__all__ = ['MariaDBViewMixin']
