# src/rhosocial/activerecord/backend/impl/mariadb/protocols/sequence.py
"""MariaDB SEQUENCE protocol."""

from typing import Protocol, Tuple, runtime_checkable


@runtime_checkable
class MariaDBSequenceSupport(Protocol):
    """MariaDB SEQUENCE protocol.

    Feature Source: MariaDB 10.3+ (not available in MySQL)

    MariaDB SEQUENCE features:
    - CREATE SEQUENCE: Create sequence object
    - NEXTVAL: Get next value
    - CURRVAL: Get current value
    - SETVAL: Set sequence value
    - RESTART: Restart sequence
    - CACHE/NOCACHE: Cache options
    - CYCLE/NOCYCLE: Cycle behavior

    Official Documentation:
    - https://mariadb.com/kb/en/sequence-storage-engine/
    - https://mariadb.com/kb/en/create-sequence/

    Version Requirements:
    - MariaDB 10.3+
    """

    def supports_sequence(self) -> bool:
        """Whether SEQUENCE objects are supported.

        MariaDB 10.3+ supports SEQUENCE storage engine.
        """
        ...

    def format_create_sequence_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement (MariaDB syntax)."""
        ...

    def format_drop_sequence_statement(self, expr) -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement (MariaDB syntax)."""
        ...

    def format_nextval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format NEXTVAL expression.

        Args:
            sequence_name: Name of the sequence

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_currval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format CURRVAL expression.

        Args:
            sequence_name: Name of the sequence

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_setval(
        self,
        sequence_name: str,
        value: int,
        is_called: bool = True
    ) -> Tuple[str, tuple]:
        """Format SETVAL expression.

        Args:
            sequence_name: Name of the sequence
            value: Value to set
            is_called: If True, next NEXTVAL returns value + increment

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
