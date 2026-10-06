# src/rhosocial/activerecord/backend/impl/mariadb/protocols/sequence.py
"""MariaDB SEQUENCE protocol.

MariaDB 10.3+ supports SEQUENCE objects. This protocol restates every
capability switch core declares for sequences, so the dialect's answers are
declared in one place:

- ``START WITH`` / ``INCREMENT BY`` / ``MINVALUE`` / ``MAXVALUE`` / ``CACHE`` /
  ``CYCLE`` are supported, together with their MariaDB spellings (the ``=``
  sign, ``NOCACHE`` and ``NOCYCLE``).
- ``IF NOT EXISTS`` / ``IF EXISTS`` are supported.
- ``ORDER`` and ``OWNED BY`` are Oracle/SQL Server forms with no MariaDB
  clause, so those probes answer ``False``.

The three statement formatters take the expression core dispatches with, so a
core ``CreateSequenceExpression`` / ``DropSequenceExpression`` /
``AlterSequenceExpression`` renders through this backend.
"""

from typing import Protocol, Tuple, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements import (
        AlterSequenceExpression,
        CreateSequenceExpression,
        DropSequenceExpression,
    )


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
    - https://mariadb.com/kb/en/alter-sequence/

    Version Requirements:
    - MariaDB 10.3+
    """

    def supports_sequence(self) -> bool:
        """Whether SEQUENCE objects are supported.

        MariaDB 10.3+ supports SEQUENCE storage engine.
        """
        ...

    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported."""
        ...

    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported."""
        ...

    def supports_alter_sequence(self) -> bool:
        """Whether ALTER SEQUENCE is supported."""
        ...

    def supports_sequence_if_not_exists(self) -> bool:
        """Whether CREATE SEQUENCE IF NOT EXISTS is supported."""
        ...

    def supports_sequence_if_exists(self) -> bool:
        """Whether DROP SEQUENCE IF EXISTS is supported."""
        ...

    def supports_sequence_start(self) -> bool:
        """Whether the START WITH sequence option is supported."""
        ...

    def supports_sequence_increment(self) -> bool:
        """Whether the INCREMENT BY sequence option is supported."""
        ...

    def supports_sequence_minvalue(self) -> bool:
        """Whether the MINVALUE sequence option is supported."""
        ...

    def supports_sequence_maxvalue(self) -> bool:
        """Whether the MAXVALUE sequence option is supported."""
        ...

    def supports_sequence_cycle(self) -> bool:
        """Whether the CYCLE option is supported."""
        ...

    def supports_sequence_cache(self) -> bool:
        """Whether the CACHE option is supported."""
        ...

    def supports_sequence_order(self) -> bool:
        """Whether the ORDER option is supported.

        MariaDB has no ``ORDER`` / ``NO ORDER`` clause on sequences.
        """
        ...

    def supports_sequence_owned_by(self) -> bool:
        """Whether the OWNED BY clause is supported.

        MariaDB has no ``OWNED BY`` clause on sequences.
        """
        ...

    def format_create_sequence_statement(
        self, expr: "CreateSequenceExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement (MariaDB syntax)."""
        ...

    def format_drop_sequence_statement(
        self, expr: "DropSequenceExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement (MariaDB syntax)."""
        ...

    def format_alter_sequence_statement(
        self, expr: "AlterSequenceExpression"
    ) -> Tuple[str, tuple]:
        """Format ALTER SEQUENCE statement (MariaDB syntax)."""
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
