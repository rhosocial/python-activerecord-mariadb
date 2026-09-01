# mariadb/protocols/partition_generated.py
"""Auto-generated protocol declarations (P7, 2026-09-01).

Functional-group principle: every public format_*/supports_* on a
backend mixin is declared here so dialect users can program against
the capability contract.  Regenerate via scripts/p7_generate_protocols.py
when mixins gain new public rendering methods.
"""

from typing import Any, Dict, List, Optional, Tuple

from typing import Protocol

class MariaDBPartitionSupport(Protocol):
    """Auto-generated capability protocol (P7)."""

    def supports_linear_hash_partitioning(self) -> bool:
        ...  # pragma: no cover
    def supports_linear_key_partitioning(self) -> bool:
        ...  # pragma: no cover
    def supports_partition_definition_options(self) -> bool:
        ...  # pragma: no cover
    def supports_analyze_partition(self) -> bool:
        ...  # pragma: no cover
    def supports_check_partition(self) -> bool:
        ...  # pragma: no cover
    def supports_optimize_partition(self) -> bool:
        ...  # pragma: no cover
    def supports_rebuild_partition(self) -> bool:
        ...  # pragma: no cover
    def supports_repair_partition(self) -> bool:
        ...  # pragma: no cover
    def format_analyze_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_check_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_optimize_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_rebuild_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_repair_partition_statement(self, expr: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_get_partitions_expression(self, expr: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
