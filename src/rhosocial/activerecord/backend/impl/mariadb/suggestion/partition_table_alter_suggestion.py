# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_table_alter_suggestion.py
"""MariaDB's partition table-alter suggestion.

For HASH/KEY strategies, suggests COALESCE PARTITION; for RANGE/LIST,
suggests REMOVE PARTITIONING. Each is gated by the corresponding server
support probe and answers explicit ``False`` when withdrawn or unknown.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionTableAlterSuggestion
from ..expression.operators.partition import (
    MariaDBCoalescePartitionExpression,
    MariaDBRemovePartitioningExpression,
)
from ._common import (
    _HASH_WORDS,
    _count,
    _MariaDBPartitionSuggestionBase,
    _table,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause


class MariaDBPartitionTableAlterSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest COALESCE for HASH/KEY, REMOVE PARTITIONING for RANGE/LIST."""

    def suggest_partition_table_alter(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionTableAlterSuggestion:
        """Suggest COALESCE for HASH/KEY, REMOVE PARTITIONING for RANGE/LIST."""
        word = _word(strategy)
        table = _table(self, plan)
        if word in _HASH_WORDS:
            if not getattr(self, "supports_coalesce_partition", lambda: True)():
                return PartitionTableAlterSuggestion(False)
            return PartitionTableAlterSuggestion(
                (MariaDBCoalescePartitionExpression(self, table, _count(plan)),)
            )
        if word in ("RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"):
            if not getattr(self, "supports_remove_partitioning", lambda: True)():
                return PartitionTableAlterSuggestion(False)
            return PartitionTableAlterSuggestion(
                (MariaDBRemovePartitioningExpression(self, table),)
            )
        return PartitionTableAlterSuggestion(False)
