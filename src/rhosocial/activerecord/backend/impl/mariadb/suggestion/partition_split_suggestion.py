# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_split_suggestion.py
"""MariaDB's partition split suggestion.

Suggests ``ALTER TABLE ... REORGANIZE PARTITION ... INTO`` for a supported
strategy, deriving the source partition and the new definitions from the plan.
An unsupported strategy (or withdrawn server support) answers explicit
``False``.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionSplitSuggestion
from ..expression.partition import MariaDBReorganizePartitionExpression
from ._common import (
    _SUPPORTED,
    _definitions,
    _field,
    _MariaDBPartitionSuggestionBase,
    _table,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class MariaDBPartitionSplitSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest the ``REORGANIZE PARTITION ... INTO`` statement."""

    def suggest_partition_split(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionSplitSuggestion:
        """Suggest the ``ALTER TABLE ... REORGANIZE PARTITION ... INTO`` statement."""
        word = _word(strategy)
        if (
            word not in _SUPPORTED
            or not getattr(self, "supports_reorganize_partition", lambda: True)()
        ):
            return PartitionSplitSuggestion(False)
        definitions = _definitions(plan)
        target = _field(plan, ("partition", "partition_name", "source", "target"))
        if not isinstance(target, str) or not target.strip():
            target = definitions[-1].name if definitions else "p0"
        into = _field(plan, ("into", "splits", "new_definitions"))
        if not into:
            into = definitions
        return PartitionSplitSuggestion(
            (MariaDBReorganizePartitionExpression(self, _table(self, plan), target, tuple(into)),)
        )
