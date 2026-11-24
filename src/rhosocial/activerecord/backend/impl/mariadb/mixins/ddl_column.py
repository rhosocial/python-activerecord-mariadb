# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl_column.py
"""MariaDB DDL column/table support mixin."""


class MariaDBDDLColumnMixin:
    """MariaDB DDL column and table capability checks.

    ``format_identity_clause`` is deliberately **not** overridden here. The
    old override rewrote every ``IdentityClause`` to `` AUTO_INCREMENT`` and
    dropped the generation mode and the start/increment options; MariaDB
    refuses the standard clause (see ``MariaDBGeneratedColumnMixin``), so the
    core formatter's fail-closed refusal is the correct answer, and
    ``AutoIncrementClause`` is the node that renders `` AUTO_INCREMENT``.
    """

    def supports_if_not_exists_table(self) -> bool:
        return True

    def supports_if_exists_table(self) -> bool:
        return True

    def supports_rename_table(self) -> bool:
        return True

    def supports_rename_column(self) -> bool:
        """Whether ``ALTER TABLE ... RENAME COLUMN`` is supported.

        RENAME COLUMN entered MariaDB in 10.5.2. Older servers rename a
        column by restating its definition under the new name with ``CHANGE
        COLUMN``, which this backend renders through ``ChangeColumnAction``.

        Gated rather than answered True, because the unconditional default
        would have a pre-10.5.2 server receive a statement its grammar does
        not have.
        """
        return self.version_at_least((10, 5, 2))

    def supports_table_partitioning(self) -> bool:
        return True

    def supports_index_if_exists(self) -> bool:
        return True

    def supports_index_if_not_exists(self) -> bool:
        return True

    def supports_functional_index(self) -> bool:
        return True

    def supports_index_type(self) -> bool:
        return True

    def supports_fulltext_index(self) -> bool:
        return True

    def supports_fulltext_parser(self) -> bool:
        return True

    def supports_fulltext_query_expansion(self) -> bool:
        return True


__all__ = ['MariaDBDDLColumnMixin']
