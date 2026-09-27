# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl_column.py
"""MariaDB DDL column/table support mixin."""

from typing import Tuple


class MariaDBDDLColumnMixin:
    """MariaDB DDL column and table capability checks."""

    def format_identity_clause(self, expr) -> Tuple[str, Tuple]:
        """MariaDB renders an identity column as ``AUTO_INCREMENT``.

        MariaDB has no ``GENERATED ... AS IDENTITY`` column syntax; seed and
        increment are table-level options, so only the marker is emitted.
        """
        return " AUTO_INCREMENT", ()

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
