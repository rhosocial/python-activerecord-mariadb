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

    def supports_with_data_clause(self) -> bool:
        """Whether ``WITH [NO] DATA`` exists as a clause.

        Measured False on all 19 configured servers: ``CREATE TABLE t AS
        SELECT 1 AS x WITH DATA`` and ``... WITH NO DATA`` are syntax errors
        (errno 1064) everywhere while the plain ``CREATE TABLE ... AS
        SELECT`` is accepted (the control that isolates the clause as the
        rejected part; sentinel rejected). Core's CTAS renderer consults this
        probe -- and so do the materialized-view create and refresh renderers,
        which MariaDB refuses earlier because it has no materialized views --
        so a requested spelling is refused by name; it never renders it.
        """
        return False


__all__ = ['MariaDBViewMixin']
