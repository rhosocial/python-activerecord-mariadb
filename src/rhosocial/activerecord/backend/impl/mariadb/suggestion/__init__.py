# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/__init__.py
"""MariaDB's concrete backend-suggestion implementations.

Suggestion data classes live in ``backend.suggestion`` (core); this package holds
only MariaDB's answers to the suggestion protocols, kept separate from
``backend.impl.mariadb.mixins`` so no core mixin can shadow them in the dialect
MRO.
"""

from .data_types import MARIADB_DATA_TYPE_SUGGESTIONS, MariaDBDataTypeSuggestionsMixin
from .integer_auto_increment import MariaDBIntegerAutoIncrementColumnSuggestionMixin
from .partition import MariaDBPartitionSuggestionMixin

__all__ = [
    "MARIADB_DATA_TYPE_SUGGESTIONS",
    "MariaDBDataTypeSuggestionsMixin",
    "MariaDBIntegerAutoIncrementColumnSuggestionMixin",
    "MariaDBPartitionSuggestionMixin",
]
