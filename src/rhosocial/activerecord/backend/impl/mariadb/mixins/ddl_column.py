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
