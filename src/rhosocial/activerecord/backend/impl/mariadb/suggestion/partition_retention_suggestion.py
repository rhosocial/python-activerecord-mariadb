# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_retention_suggestion.py
"""MariaDB's partition retention suggestion.

Retention retires partitions *older than a cutoff*. For RANGE strategies the
answer is one ``DROP PARTITION`` per definition whose upper bound is at or below
the plan's cutoff. Without a cutoff the mechanism is declined (``False``): blanket
dropping of every partition carrying a bound would delete live data, so retention
must be bounded. A non-RANGE strategy answers ``False``; a RANGE plan whose
partitions are all newer than the cutoff answers ``None`` (nothing to expire).
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionRetentionSuggestion
from ..expression.operators.partition import MariaDBDropPartitionExpression
from ._common import (
    _RANGE_WORDS,
    _definitions,
    _field,
    _MariaDBPartitionSuggestionBase,
    _table,
    _word,
)


def _upper_bound(definition):
    """The comparable upper bound of a RANGE definition, or ``None``.

    ``less_than`` is a tuple of ``MariaDBPartitionValue`` nodes; the last entry
    is the exclusive upper bound. A non-comparable bound (``MAXVALUE`` or an
    expression) yields ``None`` so it is never mistaken for an expired one.
    """
    less_than = getattr(definition, "less_than", None)
    if not isinstance(less_than, (list, tuple)) or not less_than:
        return None
    return getattr(less_than[-1], "value", None)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause


class MariaDBPartitionRetentionSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest one DROP PARTITION per expired RANGE definition."""

    def suggest_partition_retention(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionRetentionSuggestion:
        """Suggest one DROP PARTITION per RANGE definition expired by the cutoff."""
        word = _word(strategy)
        if word not in _RANGE_WORDS or not getattr(self, "supports_drop_partition", lambda: True)():
            return PartitionRetentionSuggestion(False)
        cutoff = _field(plan, ("cutoff", "cutoff_date", "older_than"))
        if cutoff is None:
            # Retention is cutoff-driven. Dropping every bounded partition when
            # no cutoff is given would retire live data, so refuse instead.
            return PartitionRetentionSuggestion(False)
        candidates = []
        for definition in _definitions(plan):
            bound = _upper_bound(definition)
            if bound is None:
                continue
            try:
                expired = bound <= cutoff
            except TypeError:
                # Incomparable bound (e.g. a MAXVALUE sentinel): not dated.
                continue
            if expired:
                candidates.append(definition)
        if not candidates:
            return PartitionRetentionSuggestion(None)
        table = _table(self, plan)
        return PartitionRetentionSuggestion(
            tuple(
                MariaDBDropPartitionExpression(self, table, (definition.name,))
                for definition in candidates
            )
        )
