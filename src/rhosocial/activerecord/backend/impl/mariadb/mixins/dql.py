# src/rhosocial/activerecord/backend/impl/mariadb/mixins/dql.py
"""MariaDB DQL (SELECT) capability overrides."""


class MariaDBDQLMixin:
    """MariaDB DQL feature support."""

    def supports_fetch_with_ties(self) -> bool:
        """MariaDB does not support FETCH ... WITH TIES."""
        return False

    def supports_nulls_first_last(self) -> bool:
        """MariaDB does not support explicit NULLS FIRST/LAST ordering."""
        return False


__all__ = ['MariaDBDQLMixin']
