# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_build_suggestion.py
"""MariaDB's partition build suggestion.

Suggests the inline ``CREATE TABLE`` ``PARTITION BY`` clause for a strategy.
MariaDB spells eight partition words; each one is a real expression node built
by the shared clause builder. An unsupported strategy answers explicit
``False``.
"""

from typing import TYPE_CHECKING

from ....expression import Column
from ....suggestion import PartitionBuildSuggestion
from ._common import (
    _DEFAULT_KEY_NAME,
    _SUPPORTED,
    _clause,
    _count,
    _definitions,
    _keys,
    _MariaDBPartitionSuggestionBase,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class MariaDBPartitionBuildSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest the inline ``CREATE TABLE`` partition clause."""

    def suggest_partition_build(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionBuildSuggestion:
        """Suggest the inline ``CREATE TABLE`` partition clause for ``strategy``."""
        word = _word(strategy)
        if word not in _SUPPORTED:
            return PartitionBuildSuggestion(False)
        keys = _keys(self, plan)
        if not keys and word not in ("KEY", "LINEAR KEY"):
            keys = (Column(self, _DEFAULT_KEY_NAME),)
        clause = _clause(self, word, keys, _definitions(plan), _count(plan))
        if clause is None:
            return PartitionBuildSuggestion(False)
        return PartitionBuildSuggestion((clause,))
