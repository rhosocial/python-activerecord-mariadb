# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/constraint.py
"""MariaDB ALTER TABLE DROP CONSTRAINT qualifier formatting."""

from typing import Tuple


class MariaDBAlterConstraintModifierMixin:
    """MariaDB ``DROP CONSTRAINT [IF EXISTS]`` formatting.

    MariaDB supports ``DROP CONSTRAINT IF EXISTS`` for named UNIQUE,
    FOREIGN KEY, and CHECK constraints since 10.0.2. The special
    ``DROP PRIMARY KEY`` form never takes ``IF EXISTS`` (MariaDB has a
    separate ``DROP PRIMARY KEY`` clause), so that path is preserved and
    emits the bare form even when ``if_exists=True``.

    Measured on **13.1.1** (192.168.1.3:15694, TLSv1.2)::

        ALTER TABLE t DROP CONSTRAINT fk          -- accepted
        ALTER TABLE t DROP CONSTRAINT `1`         -- accepted (the positional
                                                   -- name a column-level
                                                   -- REFERENCES generates)
        ALTER TABLE t DROP CONSTRAINT IF EXISTS no_such_constraint
                                                   -- accepted, silent no-op
        ALTER TABLE t DROP CONSTRAINT no_such_constraint
                                                   -- 1091 (42000) "Can't DROP
                                                   -- CONSTRAINT `...`; check
                                                   -- that it exists"

    ``IF EXISTS`` is the only idempotent spelling available, and it is worth
    knowing how lopsided that is across the two MySQL-family backends. MariaDB
    has the form and **also** a catchable errno for the absent case (1091);
    MySQL has neither -- its ``DROP CONSTRAINT IF EXISTS`` is errno 1064, a
    syntax error that fails before any errno about a missing constraint can
    exist, and its missing-constraint answer is 3940. So portable code cannot
    rely on catching an error code across the family: on MySQL the statement
    never parses. Use ``IF EXISTS``, which MariaDB honours and MySQL rejects at
    the syntax layer -- the two requirements are mutually exclusive and the
    caller has to pick.

    **MariaDB's ALTER TABLE grammar has no constraint lifecycle clause beyond
    ADD and DROP.** Measured on the same server, each of these is **errno
    1064 / SQLSTATE 42000**::

        DROP CHECK <name>                 near 'CHECK <name>'
        RENAME CONSTRAINT <n> TO <m>      near 'CONSTRAINT <n> TO <m>'
        ALTER CONSTRAINT <n> DEFERRABLE   near 'CONSTRAINT <n> DEFERRABLE'
        ALTER CONSTRAINT <n> NOT ENFORCED near 'CONSTRAINT <n> NOT ENFORCED'
        VALIDATE CONSTRAINT <n>           near 'CONSTRAINT <n>'
        ENABLE CONSTRAINT <n>             near 'CONSTRAINT <n>'
        DISABLE CONSTRAINT <n>            near 'CONSTRAINT <n>'
        NOCHECK CONSTRAINT <n>            near 'CONSTRAINT <n>'
        CHECK CONSTRAINT <n>              near 'CONSTRAINT <n>'
        ADD CONSTRAINT ... NOT VALID      near 'NOT VALID'
        ADD CONSTRAINT ... DEFERRABLE     near 'DEFERRABLE'
        ADD CONSTRAINT ... [NOT] ENFORCED near '[NOT] ENFORCED'

    Four of those nine answer the *same* message text, differing only in the
    constraint name. Error classification cannot separate ``VALIDATE`` from
    ``ENABLE`` from ``NOCHECK`` here, so each one needs its own answered
    switch rather than a shared "lifecycle clause" probe.

    That is why ``MariaDBDialect`` declares
    ``supports_alter_constraint_enforced`` / ``supports_validate_constraint``
    / ``supports_constraint_novalidate`` as ``False`` rather than leaving them
    to an inherited default, and why nothing in this mixin formats them: the
    clauses do not exist to format.

    One MariaDB/MySQL difference worth keeping in view while reading that
    list: MySQL **accepts** both ``ALTER CONSTRAINT ... ENFORCED`` and ``...
    NOT ENFORCED`` (and only for CHECK -- a FOREIGN KEY answers 3941 there).
    MariaDB accepts neither. A value copied between the two backends would be
    wrong in both directions.
    """

    def supports_drop_constraint_if_exists(self) -> bool:
        """``DROP CONSTRAINT IF EXISTS`` is supported since MariaDB 10.0.2.

        Exception: ``DROP PRIMARY KEY`` does not accept ``IF EXISTS``.

        Measured on **13.1.1**, and re-measured on 10.2.44 / 10.4.34 / 10.5.29 /
        12.0.2 / 12.1.2 / 13.1.1: the form is accepted on all six, **including
        for a constraint that does not exist**, where it is a silent no-op
        (against ``1091`` without ``IF EXISTS``). Every measured MariaDB
        therefore accepts it, and none of the six is where the 10.0.2 floor
        would show up.

        This is the shape MySQL has no answer for at all -- see the class
        docstring.
        """
        return True

    def format_drop_table_constraint_action(self, action) -> Tuple[str, tuple]:
        name = action.constraint_name
        # MariaDB PRIMARY KEY goes through DROP PRIMARY KEY (no IF EXISTS).
        if name.upper() == "PRIMARY":
            return "DROP PRIMARY KEY", ()
        if getattr(action, "if_exists", None) is True:
            result = f"DROP CONSTRAINT IF EXISTS {self.format_identifier(name)}"
        else:
            result = f"DROP CONSTRAINT {self.format_identifier(name)}"
        if getattr(action, "cascade", None):
            result += " CASCADE"
        return result, ()
