# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/partition_merge_suggestion.py
"""MariaDB's partition merge suggestion.

MariaDB has no ``MERGE PARTITION`` DDL, so the answer is unconditional
``False``. Core's ``MergeSupport`` is the unrelated SQL MERGE DML statement;
the only MariaDB operation that folds partitions is COALESCE (HASH/KEY), which
is already the table-alter suggestion, not a merge of adjacent RANGE/LIST
partitions.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionMergeSuggestion
from ._common import _MariaDBPartitionSuggestionBase

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause


class MariaDBPartitionMergeSuggestionMixin(_MariaDBPartitionSuggestionBase):
    """Answer MariaDB's lack of ``MERGE PARTITION`` DDL explicitly."""

    def suggest_partition_merge(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionMergeSuggestion:
        """MariaDB has no ``MERGE PARTITION`` DDL; answer explicit unsupported.

        Core's ``MergeSupport`` is the unrelated SQL MERGE DML statement. The
        only MariaDB operation that folds partitions is COALESCE (HASH/KEY),
        which is already the table-alter suggestion -- it is not a merge of two
        adjacent RANGE/LIST partitions, so merge is unconditionally false.
        """
        return PartitionMergeSuggestion(False)
