# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl_column.py
"""MariaDB DDL column/table support mixin."""


class MariaDBDDLColumnMixin:
    """MariaDB DDL column and table capability checks."""

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
