# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_retention_suggestion.py
"""MariaDB's partition retention suggestion.

For RANGE strategies, suggests one ``DROP PARTITION`` per definition carrying
a ``less_than`` bound. A non-RANGE strategy answers ``False``; a RANGE plan with
nothing to expire answers ``None`` (nothing to do).
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionRetentionSuggestion
from ..expression.partition import MariaDBDropPartitionExpression
from ._common import (
    _RANGE_WORDS,
    _definitions,
    _MariaDBPartitionSuggestionBase,
    _table,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class MariaDBPartitionRetentionSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest one DROP PARTITION per expired RANGE definition."""

    def suggest_partition_retention(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionRetentionSuggestion:
        """Suggest one DROP PARTITION per RANGE definition carrying ``less_than``."""
        word = _word(strategy)
        if word not in _RANGE_WORDS or not getattr(self, "supports_drop_partition", lambda: True)():
            return PartitionRetentionSuggestion(False)
        candidates = [
            definition
            for definition in _definitions(plan)
            if getattr(definition, "less_than", None)
        ]
        if not candidates:
            return PartitionRetentionSuggestion(None)
        table = _table(self, plan)
        return PartitionRetentionSuggestion(
            tuple(
                MariaDBDropPartitionExpression(self, table, (definition.name,))
                for definition in candidates
            )
        )
