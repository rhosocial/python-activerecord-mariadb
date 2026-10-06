# src/rhosocial/activerecord/backend/impl/mariadb/mixins/sequence.py
"""MariaDB SEQUENCE storage engine mixin.

MariaDB 10.3+ supports SEQUENCE objects for generating sequential numbers.
This is a MariaDB-specific feature not available in MySQL.
"""
from typing import Tuple, TYPE_CHECKING

from .backend import MARIADB_VERSION_BOUNDARIES

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements.ddl_sequence import (
        CreateSequenceExpression,
        DropSequenceExpression,
        AlterSequenceExpression,
    )


class MariaDBSequenceMixin:
    """MariaDB SEQUENCE support mixin.

    The three statement formatters below take the expression core dispatches
    with, exactly like ``format_create_table_statement`` does. Core's
    ``CreateSequenceExpression.to_sql()`` and its two siblings pass *themselves*
    to ``format_create_sequence_statement`` / ``_drop_`` / ``_alter_``, because
    the sequence they name is a :class:`~...expression.objects.Sequence` whose
    own ``format_method`` applies the namespace. MariaDB keeps its own
    formatters only because its spelling differs from core's: MariaDB accepts
    ``START =``, ``INCREMENT =``, ``MINVALUE =``, ``MAXVALUE =`` and ``CACHE =``
    (the ``=`` is an alternative to ``WITH`` / ``BY`` in the synopsis, never an
    addition to it), where core emits ``START WITH``, ``INCREMENT BY``,
    ``MINVALUE`` and so on without it. The ``START WITH =`` and
    ``INCREMENT BY =`` forms the synopsis might suggest are rejected by the
    server, so the dialect does not emit them.

    ``ORDER`` and ``OWNED BY`` are Oracle/SQL Server forms that MariaDB's
    ``CREATE SEQUENCE`` / ``ALTER SEQUENCE`` synopsis does not carry, so the
    matching probes answer ``False`` and a requested clause raises rather than
    being silently dropped. ``IF NOT EXISTS`` / ``IF EXISTS`` are supported.

    MariaDB 10.3+ supports SEQUENCE storage engine for generating
    sequential numbers.

    Features:
    - CREATE SEQUENCE: Create sequence object
    - NEXT VALUE FOR: Get next value
    - CURRENT VALUE FOR: Get current value (if sequence was used in session)
    - SET seq_name: Set sequence value
    - ALTER SEQUENCE: Modify sequence
    - DROP SEQUENCE: Remove sequence

    Official Documentation:
    - https://mariadb.com/kb/en/sequence-storage-engine/
    - https://mariadb.com/kb/en/create-sequence/
    - https://mariadb.com/kb/en/alter-sequence/

    Version Requirements:
    - MariaDB 10.3+
    """

    def supports_sequence(self) -> bool:
        """Whether SEQUENCE objects are supported.

        This is the master switch and the one place the version boundary is
        read; the per-statement switches below delegate to it, and the option
        probes answer for a version that has sequences.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.supports_sequence()

    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.supports_sequence()

    def supports_alter_sequence(self) -> bool:
        """Whether ALTER SEQUENCE is supported.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.supports_sequence()

    def supports_sequence_if_not_exists(self) -> bool:
        """Whether CREATE SEQUENCE IF NOT EXISTS is supported.

        MariaDB spells the clause ``IF NOT EXISTS``.
        """
        return True

    def supports_sequence_if_exists(self) -> bool:
        """Whether DROP SEQUENCE IF EXISTS is supported.

        MariaDB spells the clause ``IF EXISTS``.
        """
        return True

    def supports_sequence_start(self) -> bool:
        """Whether the START WITH sequence option is supported.

        MariaDB also accepts the ``START =`` spelling.
        """
        return True

    def supports_sequence_increment(self) -> bool:
        """Whether the INCREMENT BY sequence option is supported.

        MariaDB also accepts the ``INCREMENT =`` spelling.
        """
        return True

    def supports_sequence_minvalue(self) -> bool:
        """Whether the MINVALUE sequence option is supported.

        MariaDB also accepts the ``MINVALUE =`` spelling.
        """
        return True

    def supports_sequence_maxvalue(self) -> bool:
        """Whether the MAXVALUE sequence option is supported.

        MariaDB also accepts the ``MAXVALUE =`` spelling.
        """
        return True

    def supports_sequence_cycle(self) -> bool:
        """Whether the CYCLE option is supported.

        MariaDB spells the negative form ``NOCYCLE``.
        """
        return True

    def supports_sequence_cache(self) -> bool:
        """Whether the CACHE option is supported.

        MariaDB spells the negative form ``NOCACHE``.
        """
        return True

    def supports_sequence_order(self) -> bool:
        """Whether the ORDER option is supported.

        ``ORDER`` / ``NO ORDER`` is Oracle/SQL Server syntax. MariaDB's
        ``CREATE SEQUENCE`` / ``ALTER SEQUENCE`` synopsis has no such clause.
        """
        return False

    def supports_sequence_owned_by(self) -> bool:
        """Whether the OWNED BY clause is supported.

        MariaDB has no ``OWNED BY`` clause; a sequence is owned by its database.
        """
        return False

    def format_nextval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format NEXTVAL expression.

        Args:
            sequence_name: Name of the sequence.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Example:
            >>> dialect.format_nextval('user_seq')
            ('NEXT VALUE FOR `user_seq`', ())
        """
        return f"NEXT VALUE FOR {self.format_identifier(sequence_name)}", ()

    def format_currval(self, sequence_name: str) -> Tuple[str, tuple]:
        """Format CURRVAL expression.

        Note: CURRVAL returns the most recent value obtained by NEXTVAL
        for the sequence in the current session.

        Args:
            sequence_name: Name of the sequence.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Example:
            >>> dialect.format_currval('user_seq')
            ('CURRENT VALUE FOR `user_seq`', ())
        """
        return f"CURRENT VALUE FOR {self.format_identifier(sequence_name)}", ()

    def format_setval(
        self,
        sequence_name: str,
        value: int,
        is_called: bool = True
    ) -> Tuple[str, tuple]:
        """Format SETVAL expression.

        Sets the sequence to a specific value.

        Args:
            sequence_name: Name of the sequence.
            value: Value to set.
            is_called: If True, next NEXTVAL returns value + increment.
                       If False, next NEXTVAL returns value.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Example:
            >>> dialect.format_setval('user_seq', 100)
            ('SET `user_seq` = 100', ())
            >>> dialect.format_setval('user_seq', 100, is_called=False)
            ('SET `user_seq` = 100, 0', ())
        """
        sql = f"SET {self.format_identifier(sequence_name)} = {value}"
        if not is_called:
            sql += ", 0"
        return sql, ()

    def format_create_sequence_statement(
        self,
        expr: "CreateSequenceExpression",
    ) -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement.

        Syntax:
            CREATE SEQUENCE [IF NOT EXISTS] seq_name
            [START = value]
            [INCREMENT = value]
            [MINVALUE = value]
            [MAXVALUE = value]
            [CACHE = value]
            [CYCLE]

        Args:
            expr: CreateSequenceExpression carrying the sequence name and the
                optional start, increment, min/max value, cache, cycle,
                if-not-exists, order and owned-by options.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            TypeError: ``expr.sequence`` is not a Sequence. A table would render
                as a well-formed CREATE SEQUENCE over that table's name.
            UnsupportedFeatureError: The MariaDB version is below 10.3, or the
                expression asked for ``ORDER`` / ``OWNED BY``, which MariaDB has
                no clause for.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.objects import Sequence

        if not isinstance(expr.sequence, Sequence):
            raise TypeError(
                f"CreateSequenceExpression.sequence must be a Sequence, "
                f"got {type(expr.sequence).__name__}"
            )
        if not self.supports_sequence():
            raise UnsupportedFeatureError(
                self.name,
                "CREATE SEQUENCE",
                "SEQUENCE storage engine requires MariaDB 10.3 or later."
            )
        if not self.supports_create_sequence():
            raise UnsupportedFeatureError(
                self.name,
                "CREATE SEQUENCE",
                "CREATE SEQUENCE requires MariaDB 10.3 or later."
            )

        parts = ["CREATE SEQUENCE"]
        if expr.if_not_exists:
            if not self.supports_sequence_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "CREATE SEQUENCE IF NOT EXISTS",
                    f"{self.name} does not support CREATE SEQUENCE IF NOT EXISTS."
                )
            parts.append("IF NOT EXISTS")
        parts.append(expr.sequence.to_sql()[0])

        options = []
        if expr.start is not None:
            if not self.supports_sequence_start():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE START",
                    f"{self.name} does not support the START WITH sequence option."
                )
            options.append(f"START = {expr.start}")
        if expr.increment is not None:
            if not self.supports_sequence_increment():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE INCREMENT",
                    f"{self.name} does not support the INCREMENT BY sequence option."
                )
            options.append(f"INCREMENT = {expr.increment}")
        if expr.minvalue is not None:
            if not self.supports_sequence_minvalue():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE MINVALUE",
                    f"{self.name} does not support the MINVALUE sequence option."
                )
            options.append(f"MINVALUE = {expr.minvalue}")
        if expr.maxvalue is not None:
            if not self.supports_sequence_maxvalue():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE MAXVALUE",
                    f"{self.name} does not support the MAXVALUE sequence option."
                )
            options.append(f"MAXVALUE = {expr.maxvalue}")
        if expr.cache is not None:
            if not self.supports_sequence_cache():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE CACHE",
                    f"{self.name} does not support the CACHE sequence option."
                )
            options.append(f"CACHE = {expr.cache}")
        if expr.cycle:
            if not self.supports_sequence_cycle():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE CYCLE",
                    f"{self.name} does not support the CYCLE sequence option."
                )
            options.append("CYCLE")
        if expr.order:
            if not self.supports_sequence_order():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE ORDER",
                    f"{self.name} does not support the ORDER sequence option."
                )
            options.append("ORDER")
        if expr.owned_by:
            if not self.supports_sequence_owned_by():
                raise UnsupportedFeatureError(
                    self.name,
                    "SEQUENCE OWNED BY",
                    f"{self.name} does not support the OWNED BY sequence option."
                )
            options.append(f"OWNED BY {expr.owned_by}")

        if options:
            parts.append(" ".join(options))

        return " ".join(parts), ()

    def format_drop_sequence_statement(
        self,
        expr: "DropSequenceExpression",
    ) -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement.

        Args:
            expr: DropSequenceExpression carrying the sequence name and the
                optional if-exists flag.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            TypeError: ``expr.sequence`` is not a Sequence. A table would render
                as a well-formed DROP SEQUENCE over that table's name.
            UnsupportedFeatureError: The MariaDB version is below 10.3.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.objects import Sequence

        if not isinstance(expr.sequence, Sequence):
            raise TypeError(
                f"DropSequenceExpression.sequence must be a Sequence, "
                f"got {type(expr.sequence).__name__}"
            )
        if not self.supports_sequence():
            raise UnsupportedFeatureError(
                self.name,
                "DROP SEQUENCE",
                "SEQUENCE storage engine requires MariaDB 10.3 or later."
            )
        if not self.supports_drop_sequence():
            raise UnsupportedFeatureError(
                self.name,
                "DROP SEQUENCE",
                "DROP SEQUENCE requires MariaDB 10.3 or later."
            )

        parts = ["DROP SEQUENCE"]
        if expr.if_exists:
            if not self.supports_sequence_if_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "DROP SEQUENCE IF EXISTS",
                    f"{self.name} does not support DROP SEQUENCE IF EXISTS."
                )
            parts.append("IF EXISTS")
        parts.append(expr.sequence.to_sql()[0])

        return " ".join(parts), ()

    def format_alter_sequence_statement(
        self,
        expr: "AlterSequenceExpression",
    ) -> Tuple[str, tuple]:
        """Format ALTER SEQUENCE statement.

        Args:
            expr: AlterSequenceExpression carrying the sequence name and the
                options to change (restart, start, increment, min/max value,
                cycle, cache, order and owned-by).

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            TypeError: ``expr.sequence`` is not a Sequence. A table would render
                as a well-formed ALTER SEQUENCE over that table's name.
            UnsupportedFeatureError: The MariaDB version is below 10.3, or the
                expression asked for ``ORDER`` / ``OWNED BY``, which MariaDB has
                no clause for.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.objects import Sequence

        if not isinstance(expr.sequence, Sequence):
            raise TypeError(
                f"AlterSequenceExpression.sequence must be a Sequence, "
                f"got {type(expr.sequence).__name__}"
            )
        if not self.supports_sequence():
            raise UnsupportedFeatureError(
                self.name,
                "ALTER SEQUENCE",
                "SEQUENCE storage engine requires MariaDB 10.3 or later."
            )
        if not self.supports_alter_sequence():
            raise UnsupportedFeatureError(
                self.name,
                "ALTER SEQUENCE",
                "ALTER SEQUENCE requires MariaDB 10.3 or later."
            )

        parts = [f"ALTER SEQUENCE {expr.sequence.to_sql()[0]}"]

        options = []
        if expr.restart is not None:
            options.append(f"RESTART WITH {expr.restart}")
        if expr.start is not None:
            if not self.supports_sequence_start():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE START",
                    f"{self.name} does not support the START WITH sequence option."
                )
            options.append(f"START = {expr.start}")
        if expr.increment is not None:
            if not self.supports_sequence_increment():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE INCREMENT",
                    f"{self.name} does not support the INCREMENT BY sequence option."
                )
            options.append(f"INCREMENT = {expr.increment}")
        if expr.minvalue is not None:
            if not self.supports_sequence_minvalue():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE MINVALUE",
                    f"{self.name} does not support the MINVALUE sequence option."
                )
            options.append(f"MINVALUE = {expr.minvalue}")
        if expr.maxvalue is not None:
            if not self.supports_sequence_maxvalue():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE MAXVALUE",
                    f"{self.name} does not support the MAXVALUE sequence option."
                )
            options.append(f"MAXVALUE = {expr.maxvalue}")
        if expr.cache is not None:
            if not self.supports_sequence_cache():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE CACHE",
                    f"{self.name} does not support the CACHE sequence option."
                )
            options.append(f"CACHE = {expr.cache}")
        if expr.cycle is not None:
            if not self.supports_sequence_cycle():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE CYCLE",
                    f"{self.name} does not support the CYCLE sequence option."
                )
            options.append("CYCLE" if expr.cycle else "NOCYCLE")
        if expr.order is not None:
            if not self.supports_sequence_order():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE ORDER",
                    f"{self.name} does not support the ORDER sequence option."
                )
            options.append("ORDER" if expr.order else "NO ORDER")
        if expr.owned_by is not None:
            if not self.supports_sequence_owned_by():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER SEQUENCE OWNED BY",
                    f"{self.name} does not support the OWNED BY sequence option."
                )
            options.append(f"OWNED BY {expr.owned_by}")

        if options:
            parts.append(" ".join(options))

        return " ".join(parts), ()


__all__ = ['MariaDBSequenceMixin']
