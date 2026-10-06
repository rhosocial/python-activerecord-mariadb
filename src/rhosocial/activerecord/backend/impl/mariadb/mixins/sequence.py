# src/rhosocial/activerecord/backend/impl/mariadb/mixins/sequence.py
"""MariaDB SEQUENCE storage engine mixin.

MariaDB 10.3+ supports SEQUENCE objects for generating sequential numbers.
This is a MariaDB-specific feature not available in MySQL.
"""
from typing import Optional, Tuple

from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBSequenceMixin:
    """MariaDB SEQUENCE support mixin.

    **These three statement formatters do not take the expression.** Core's
    ``CreateSequenceExpression.to_sql()`` and its two siblings dispatch on
    ``format_create_sequence_statement`` / ``_drop_`` / ``_alter_`` with
    *themselves* as the single argument, because the sequence they name is a
    :class:`~...expression.objects.Sequence` whose own ``format_method``
    applies the namespace. The formatters below instead take a bare name string
    plus loose option parameters, which is the older core signature.

    So a sequence expression handed to MariaDB cannot render: the dispatch puts
    the expression where a ``str`` is expected. The three methods say so
    explicitly with a ``TypeError`` naming what they wanted, rather than failing
    further in with ``AttributeError`` on ``.replace``. The same divergence is
    recorded in ``_SIGNATURE_MISMATCH_EXCLUSIONS`` in the protocol conformance
    test, and
    ``test_sequence_support_remains_independent`` in the type/DDL tests asserts
    the string form directly. Bringing these onto the object API is a behaviour
    change and is deliberately not done in this pass; this mixin's docstring is
    where a reader should learn it.

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

    Version Requirements:
    - MariaDB 10.3+
    """

    def supports_sequence(self) -> bool:
        """Whether SEQUENCE objects are supported.

        MariaDB 10.3+ supports SEQUENCE storage engine.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_alter_sequence(self) -> bool:
        """Whether ALTER SEQUENCE is supported.

        Returns:
            True if MariaDB version >= 10.3.0.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

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
        sequence_name: str,
        start_with: Optional[int] = None,
        increment_by: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cache: Optional[int] = None,
        cycle: bool = False,
        if_not_exists: bool = False
    ) -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement.

        Syntax:
            CREATE SEQUENCE [IF NOT EXISTS] seq_name
            [START WITH = value]
            [INCREMENT BY = value]
            [MINVALUE = value | NO MINVALUE]
            [MAXVALUE = value | NO MAXVALUE]
            [CACHE = value | NOCACHE]
            [CYCLE | NOCYCLE]

        Args:
            sequence_name: Name of the sequence.
            start_with: Starting value (default: 1).
            increment_by: Increment value (default: 1).
            minvalue: Minimum value (default: 1 for ascending, -9223372036854775807 for descending).
            maxvalue: Maximum value (default: 9223372036854775806 for ascending, -1 for descending).
            cache: Number of values to cache.
            cycle: Whether to cycle when reaching limits.
            if_not_exists: Whether to use IF NOT EXISTS.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            TypeError: ``sequence_name`` is not a string. This formatter takes a
                bare name, while the expression API dispatches with a
                :class:`CreateSequenceExpression`; see the class docstring.
        """
        if not isinstance(sequence_name, str):
            raise TypeError(
                f"format_create_sequence_statement takes a sequence name, "
                f"got {type(sequence_name).__name__}"
            )
        if not self.supports_create_sequence():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "CREATE SEQUENCE",
                "SEQUENCE storage engine requires MariaDB 10.3 or later."
            )

        parts = ["CREATE SEQUENCE"]
        if if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(sequence_name))

        options = []
        if start_with is not None:
            options.append(f"START WITH = {start_with}")
        if increment_by is not None:
            options.append(f"INCREMENT BY = {increment_by}")
        if minvalue is not None:
            options.append(f"MINVALUE = {minvalue}")
        if maxvalue is not None:
            options.append(f"MAXVALUE = {maxvalue}")
        if cache is not None:
            options.append(f"CACHE = {cache}")
        if cycle:
            options.append("CYCLE")

        if options:
            parts.append(" ".join(options))

        return " ".join(parts), ()

    def format_drop_sequence_statement(
        self,
        sequence_name: str,
        if_exists: bool = False
    ) -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement.

        Args:
            sequence_name: Name of the sequence.
            if_exists: Whether to use IF EXISTS.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            TypeError: ``sequence_name`` is not a string. This formatter takes a
                bare name, while the expression API dispatches with a
                :class:`DropSequenceExpression`; see the class docstring.
        """
        if not isinstance(sequence_name, str):
            raise TypeError(
                f"format_drop_sequence_statement takes a sequence name, "
                f"got {type(sequence_name).__name__}"
            )
        if not self.supports_drop_sequence():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "DROP SEQUENCE",
                "SEQUENCE storage engine requires MariaDB 10.3 or later."
            )

        parts = ["DROP SEQUENCE"]
        if if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(sequence_name))

        return " ".join(parts), ()

    def format_alter_sequence_statement(
        self,
        sequence_name: str,
        restart_with: Optional[int] = None,
        increment_by: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cache: Optional[int] = None,
        cycle: Optional[bool] = None
    ) -> Tuple[str, tuple]:
        """Format ALTER SEQUENCE statement.

        Args:
            sequence_name: Name of the sequence.
            restart_with: Value to restart the sequence at.
            increment_by: New increment value.
            minvalue: New minimum value.
            maxvalue: New maximum value.
            cache: New cache size.
            cycle: Whether to cycle.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            TypeError: ``sequence_name`` is not a string. This formatter takes a
                bare name, while the expression API dispatches with an
                :class:`AlterSequenceExpression`; see the class docstring.
        """
        if not isinstance(sequence_name, str):
            raise TypeError(
                f"format_alter_sequence_statement takes a sequence name, "
                f"got {type(sequence_name).__name__}"
            )
        if not self.supports_alter_sequence():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "ALTER SEQUENCE",
                "SEQUENCE storage engine requires MariaDB 10.3 or later."
            )

        parts = ["ALTER SEQUENCE", self.format_identifier(sequence_name)]

        options = []
        if restart_with is not None:
            options.append(f"RESTART WITH {restart_with}")
        if increment_by is not None:
            options.append(f"INCREMENT BY = {increment_by}")
        if minvalue is not None:
            options.append(f"MINVALUE = {minvalue}")
        if maxvalue is not None:
            options.append(f"MAXVALUE = {maxvalue}")
        if cache is not None:
            options.append(f"CACHE = {cache}")
        if cycle is not None:
            options.append("CYCLE" if cycle else "NOCYCLE")

        if options:
            parts.append(" ".join(options))

        return " ".join(parts), ()


__all__ = ['MariaDBSequenceMixin']
