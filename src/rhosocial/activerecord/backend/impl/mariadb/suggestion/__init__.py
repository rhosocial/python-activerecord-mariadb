# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/__init__.py
"""MariaDB's concrete backend-suggestion implementations.

Suggestion data classes live in ``backend.suggestion`` (core); this package holds
only MariaDB's answers to the suggestion protocols, kept separate from
``backend.impl.mariadb.mixins`` so no core mixin can shadow them in the dialect
MRO. One suggestion per file, mirroring SQLite's suggestion package.
"""

from .column_reorder_suggestion import MariaDBColumnReorderSuggestionMixin
from .create_table_layout_suggestion import MariaDBCreateTableLayoutSuggestionMixin
from .data_type_suggestions import MARIADB_DATA_TYPE_SUGGESTIONS, MariaDBDataTypeSuggestionsMixin
from .generated_value_suggestion import MariaDBGeneratedValueSuggestionMixin
from .partition_add_suggestion import MariaDBPartitionAddSuggestionMixin
from .partition_build_suggestion import MariaDBPartitionBuildSuggestionMixin
from .partition_drop_suggestion import MariaDBPartitionDropSuggestionMixin
from .partition_merge_suggestion import MariaDBPartitionMergeSuggestionMixin
from .partition_retention_suggestion import MariaDBPartitionRetentionSuggestionMixin
from .partition_scheme_change_suggestion import MariaDBPartitionSchemeChangeSuggestionMixin
from .partition_split_suggestion import MariaDBPartitionSplitSuggestionMixin
from .partition_table_alter_suggestion import MariaDBPartitionTableAlterSuggestionMixin
from .partition_table_drop_suggestion import MariaDBPartitionTableDropSuggestionMixin
from .string_concatenation_suggestion import MariaDBStringConcatenationSuggestionMixin
from .table_constraint_change_suggestion import MariaDBTableConstraintChangeSuggestionMixin
from .table_index_change_suggestion import MariaDBTableIndexChangeSuggestionMixin

__all__ = [
    "MARIADB_DATA_TYPE_SUGGESTIONS",
    "MariaDBColumnReorderSuggestionMixin",
    "MariaDBCreateTableLayoutSuggestionMixin",
    "MariaDBDataTypeSuggestionsMixin",
    "MariaDBGeneratedValueSuggestionMixin",
    "MariaDBPartitionAddSuggestionMixin",
    "MariaDBPartitionBuildSuggestionMixin",
    "MariaDBPartitionDropSuggestionMixin",
    "MariaDBPartitionMergeSuggestionMixin",
    "MariaDBPartitionRetentionSuggestionMixin",
    "MariaDBPartitionSchemeChangeSuggestionMixin",
    "MariaDBPartitionSplitSuggestionMixin",
    "MariaDBPartitionTableAlterSuggestionMixin",
    "MariaDBPartitionTableDropSuggestionMixin",
    "MariaDBStringConcatenationSuggestionMixin",
    "MariaDBTableConstraintChangeSuggestionMixin",
    "MariaDBTableIndexChangeSuggestionMixin",
]
