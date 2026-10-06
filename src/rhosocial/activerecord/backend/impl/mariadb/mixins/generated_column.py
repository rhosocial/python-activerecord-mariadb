# src/rhosocial/activerecord/backend/impl/mariadb/mixins/generated_column.py
"""MariaDB generated column, identity and auto-increment support mixin."""


class MariaDBGeneratedColumnMixin:
    """MariaDB generated column, identity and auto-increment support.

    Identity and ``AUTO_INCREMENT`` are two mechanisms, not two spellings of
    one. ``GENERATED ... AS IDENTITY`` is a *parameterised* column clause;
    ``AUTO_INCREMENT`` is a *parameterless* marker whose seed is the
    table-level ``AUTO_INCREMENT=`` option. MariaDB implements the marker and
    not the clause, and the probes below say exactly that -- measured by
    execution on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc, not copied from another
    dialect's table.
    """

    def supports_generated_columns(self) -> bool:
        return True

    def supports_stored_generated_columns(self) -> bool:
        return True

    def supports_virtual_generated_columns(self) -> bool:
        return True

    def supports_auto_increment_column(self) -> bool:
        """Whether the bare ``AUTO_INCREMENT`` column marker is accepted.

        Measured on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version accepts
        ``AUTO_INCREMENT`` (the column must be a key, which the caller models).
        The marker carries no parameters, so there is no per-option probe.
        """
        return True

    def supports_identity_column(self) -> bool:
        """Whether ``GENERATED ... AS IDENTITY`` is accepted.

        Measured ``False`` on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every
        version refuses ``GENERATED {ALWAYS|BY DEFAULT} AS IDENTITY`` with a
        syntax error (errno 1064) -- in a column definition and in
        ``ALTER TABLE ... ADD COLUMN``, with a key and without one, in default
        and ``ORACLE`` sql_mode. MariaDB's identity mechanism is
        ``AUTO_INCREMENT``; it is a different node, so the formatter refuses
        the standard clause instead of rewriting it to the other mechanism.
        """
        return False

    # The six option probes answer for options of a clause MariaDB refuses
    # outright, so no option can be accepted either. They are declared rather
    # than left to core's ``False`` default so the measurement is recorded
    # where the next reader will look; a future MariaDB that grows the clause
    # has one place to revisit per option.

    def supports_identity_generation_always(self) -> bool:
        """``GENERATED ALWAYS``; measured False (the whole clause is refused)."""
        return False

    def supports_identity_start(self) -> bool:
        """``START WITH``; measured False (the whole clause is refused)."""
        return False

    def supports_identity_increment(self) -> bool:
        """``INCREMENT BY``; measured False (the whole clause is refused)."""
        return False

    def supports_identity_minvalue(self) -> bool:
        """``MINVALUE``; measured False (the whole clause is refused)."""
        return False

    def supports_identity_maxvalue(self) -> bool:
        """``MAXVALUE``; measured False (the whole clause is refused)."""
        return False

    def supports_identity_cycle(self) -> bool:
        """``CYCLE`` / ``NO CYCLE``; measured False (the clause is refused)."""
        return False


__all__ = ['MariaDBGeneratedColumnMixin']
