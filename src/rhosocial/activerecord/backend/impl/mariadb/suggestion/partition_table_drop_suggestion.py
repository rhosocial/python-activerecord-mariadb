# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_table_drop_suggestion.py
"""MariaDB's partition table-drop suggestion.

Dropping the whole table first removes partitioning where the server supports
it, then drops the table. The plan's target table is resolved by the shared
helper; the operation chain is real expression nodes.
"""

from typing import TYPE_CHECKING

from ....expression import DropTableStatement
from ....suggestion import PartitionTableDropSuggestion
from ..expression.partition import MariaDBRemovePartitioningExpression
from ._common import _MariaDBPartitionSuggestionBase, _table

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class MariaDBPartitionTableDropSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Suggest dropping the whole table; unpartition first where possible."""

    def suggest_partition_table_drop(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionTableDropSuggestion:
        """Suggest dropping the whole table; unpartition first where possible."""
        table = _table(self, plan)
        operations = []
        if getattr(self, "supports_remove_partitioning", lambda: True)():
            operations.append(MariaDBRemovePartitioningExpression(self, table))
        operations.append(DropTableStatement(self, table))
        return PartitionTableDropSuggestion(tuple(operations))
