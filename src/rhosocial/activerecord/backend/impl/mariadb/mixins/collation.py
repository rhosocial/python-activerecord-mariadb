# src/rhosocial/activerecord/backend/impl/mariadb/mixins/collation.py
"""MariaDB collation support mixin."""
from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.collation import CollateExpression


class MariaDBCollationMixin:
    """MariaDB COLLATE expression support."""

    def supports_collate_expression(self) -> bool:
        """MariaDB supports expression-level COLLATE."""
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate MariaDB collation names and return their SQL representation."""
        if expr.collation_options:
            unsupported = ", ".join(sorted(expr.collation_options))
            raise UnsupportedFeatureError(self.name, f"COLLATE options: {unsupported}")
        from ..collation import validate_mariadb_collation_name
        return validate_mariadb_collation_name(expr.collation_name, getattr(self, "version", None))


__all__ = ['MariaDBCollationMixin']
