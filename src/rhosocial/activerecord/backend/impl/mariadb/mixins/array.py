# src/rhosocial/activerecord/backend/impl/mariadb/mixins/array.py
"""MariaDB array support mixin."""
from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.advanced_functions import ArrayExpression

_SUGGESTION_ARRAY = "MariaDB does not support native array types. Use JSON arrays instead."


class MariaDBArrayMixin:
    """MariaDB array support — not natively supported."""

    def format_array_expression(self, _expr: "ArrayExpression") -> Tuple[str, Tuple]:
        """Format array expression - not supported."""
        raise UnsupportedFeatureError(self.name, "Array operations", _SUGGESTION_ARRAY)


__all__ = ['MariaDBArrayMixin']
