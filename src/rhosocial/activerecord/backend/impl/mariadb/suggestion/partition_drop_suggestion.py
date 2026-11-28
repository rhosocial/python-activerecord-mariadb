# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_drop_suggestion.py
"""MariaDB's partition drop suggestion.

Suggests ``ALTER TABLE ... DROP PARTITION`` for a supported strategy, naming
the partitions from the plan or its definitions. An unsupported strategy (or
withdrawn server support) answers explicit ``False``.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionDropSuggestion
from ..expression.operators.partition import MariaDBDropPartitionExpression
from ._common import (
    _SUPPORTED,
    _definitions,
    _MariaDBPartitionSuggestionBase,
    _names,
    _table,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause


class MariaDBPartitionDropSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest the ``ALTER TABLE ... DROP PARTITION`` statement."""

    def suggest_partition_drop(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionDropSuggestion:
        """Suggest the ``ALTER TABLE ... DROP PARTITION`` statement."""
        word = _word(strategy)
        if word not in _SUPPORTED or not getattr(self, "supports_drop_partition", lambda: True)():
            return PartitionDropSuggestion(False)
        names = _names(plan, _definitions(plan))
        return PartitionDropSuggestion(
            (MariaDBDropPartitionExpression(self, _table(self, plan), names),)
        )
