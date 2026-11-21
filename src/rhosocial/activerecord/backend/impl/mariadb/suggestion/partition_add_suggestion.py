# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_add_suggestion.py
"""MariaDB's partition add suggestion.

Suggests ``ALTER TABLE ... ADD PARTITION`` for a supported strategy, as a real
expression node. The strategy and the new definitions are read from the
caller-owned plan; an unsupported strategy (or withdrawn server support)
answers explicit ``False``.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionAddSuggestion
from ..expression.partition import MariaDBAddPartitionExpression
from ._common import (
    _SUPPORTED,
    _definitions,
    _MariaDBPartitionSuggestionBase,
    _table,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class MariaDBPartitionAddSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest the ``ALTER TABLE ... ADD PARTITION`` statement."""

    def suggest_partition_add(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionAddSuggestion:
        """Suggest the ``ALTER TABLE ... ADD PARTITION`` statement."""
        word = _word(strategy)
        if word not in _SUPPORTED or not getattr(self, "supports_add_partition", lambda: True)():
            return PartitionAddSuggestion(False)
        return PartitionAddSuggestion(
            (MariaDBAddPartitionExpression(self, _table(self, plan), _definitions(plan)),)
        )
