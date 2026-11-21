# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/__init__.py
"""MariaDB's concrete backend-suggestion implementations.

Suggestion data classes live in ``backend.suggestion`` (core); this package holds
only MariaDB's answers to the suggestion protocols, kept separate from
``backend.impl.mariadb.mixins`` so no core mixin can shadow them in the dialect
MRO. One suggestion per file, mirroring SQLite's suggestion package.
"""

from .data_type_suggestions import MARIADB_DATA_TYPE_SUGGESTIONS, MariaDBDataTypeSuggestionsMixin
from .integer_auto_increment_column_suggestion import (
    MariaDBIntegerAutoIncrementColumnSuggestionMixin,
)
from .partition_add_suggestion import MariaDBPartitionAddSuggestionMixin
from .partition_build_suggestion import MariaDBPartitionBuildSuggestionMixin
from .partition_drop_suggestion import MariaDBPartitionDropSuggestionMixin
from .partition_merge_suggestion import MariaDBPartitionMergeSuggestionMixin
from .partition_retention_suggestion import MariaDBPartitionRetentionSuggestionMixin
from .partition_split_suggestion import MariaDBPartitionSplitSuggestionMixin
from .partition_table_alter_suggestion import MariaDBPartitionTableAlterSuggestionMixin
from .partition_table_drop_suggestion import MariaDBPartitionTableDropSuggestionMixin

__all__ = [
    "MARIADB_DATA_TYPE_SUGGESTIONS",
    "MariaDBDataTypeSuggestionsMixin",
    "MariaDBIntegerAutoIncrementColumnSuggestionMixin",
    "MariaDBPartitionAddSuggestionMixin",
    "MariaDBPartitionBuildSuggestionMixin",
    "MariaDBPartitionDropSuggestionMixin",
    "MariaDBPartitionMergeSuggestionMixin",
    "MariaDBPartitionRetentionSuggestionMixin",
    "MariaDBPartitionSplitSuggestionMixin",
    "MariaDBPartitionTableAlterSuggestionMixin",
    "MariaDBPartitionTableDropSuggestionMixin",
]
