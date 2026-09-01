# mariadb/protocols/system_versioning_generated.py
"""Auto-generated protocol declarations (P7, 2026-09-01).

Functional-group principle: every public format_*/supports_* on a
backend mixin is declared here so dialect users can program against
the capability contract.  Regenerate via scripts/p7_generate_protocols.py
when mixins gain new public rendering methods.
"""

from typing import Any, Dict, List, Optional, Tuple

from typing import Protocol

class MariaDBSystemVersioningSupport(Protocol):
    """Auto-generated capability protocol (P7)."""

    def format_system_versioning_clause(self, table_options: Optional[Dict[str, Any]]=None) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_for_system_time_as_of(self, timestamp: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_for_system_time_between(self, start: Any, end: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_for_system_time_from_to(self, start: Any, end: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_for_system_time_all(self) -> Tuple[str, tuple]:
        ...  # pragma: no cover
    def format_without_system_versioning(self) -> Tuple[str, tuple]:
        ...  # pragma: no cover
