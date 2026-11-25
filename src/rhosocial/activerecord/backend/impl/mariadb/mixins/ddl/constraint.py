# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/constraint.py
"""MariaDB ALTER TABLE DROP CONSTRAINT qualifier formatting."""

from typing import Tuple, cast

from ..backend import MARIADB_VERSION_BOUNDARIES


class MariaDBAlterConstraintModifierMixin:
    """MariaDB ``DROP CONSTRAINT [IF EXISTS]`` formatting.

    MariaDB supports ``DROP CONSTRAINT IF EXISTS`` for named UNIQUE,
    FOREIGN KEY, and CHECK constraints from 10.2.1, the release that
    introduced ``DROP CONSTRAINT`` itself together with the ``IF EXISTS``
    qualifier. Before 10.2.1 the older per-kind spellings carry the same
    capability -- ``DROP FOREIGN KEY``, ``DROP PRIMARY KEY`` and ``DROP
    INDEX`` / ``DROP KEY`` all exist in the 10.0.15 grammar; CHECK
    constraints are absent too, so there is nothing the older spellings
    cannot reach. The special ``DROP PRIMARY KEY`` form never takes
    ``IF EXISTS`` (MariaDB has a separate ``DROP PRIMARY KEY`` clause), so
    that path is preserved and emits the bare form even when
    ``if_exists=True``.

    Measured on **13.1.1** (scenario ``mariadb_131rc``, TLSv1.2)::

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

    **A declaration is not a by-kind drop here.** Core's
    ``DropTableConstraintAction`` may carry the constraint's *declaration*
    instead of a name, which lets a dialect spell the drop by kind. MariaDB
    does not advertise that: ``supports_drop_constraint_by_kind()`` is
    inherited ``False``, because the kind spellings this mixin keeps
    (``DROP PRIMARY KEY``, and the pre-10.2.1 ``DROP FOREIGN KEY`` / ``DROP
    INDEX`` capability) are internal to it and a declaration cannot decide
    between them -- a primary key symbol is not in the name space. A
    declaration-only action is therefore refused by feature name
    (``UnsupportedFeatureError`` naming ``DROP CONSTRAINT by kind``). An
    action carrying both addresses renders by the **name** only when the
    declaration carries that same name -- an unequal or unnamed declaration is
    an **ambiguous address** and is refused, never resolved by preference.

    The addressing rule is core's, not restated here: this formatter calls
    ``ConstraintMixin._resolve_drop_constraint_address`` first and spells
    only the answer ``"name"``. A kind answer (a subclass that advertises
    ``supports_drop_constraint_by_kind()``) has no name to render here, so it
    raises ``NotImplementedError`` naming the override requirement instead of
    inventing a spelling.
    """

    def supports_drop_constraint_if_exists(self) -> bool:
        """``DROP CONSTRAINT IF EXISTS`` is supported from MariaDB 10.2.1.

        The qualifier shares ``MARIADB_VERSION_BOUNDARIES['DROP_CONSTRAINT']``
        with the statement itself: the whole ``DROP CONSTRAINT`` clause
        arrives in 10.2.1 already carrying ``IF EXISTS``, so there is no
        version that has the statement without the qualifier. 10.2.0 and every
        10.1 version have no ``DROP CONSTRAINT`` rule at all.

        Exception: ``DROP PRIMARY KEY`` does not accept ``IF EXISTS``.

        Verified live on 10.2.44 / 10.4.34 / 10.5.29 / 10.6.28 / 10.11.19 /
        11.4.13 / 12.0.2 / 13.1.1: the form is accepted on all eight,
        **including for a constraint that does not exist**, where it is a
        silent no-op (warning 1091; the bare spelling of the same absent name
        is errno 1091).

        This is the shape MySQL has no answer for at all -- see the class
        docstring.
        """
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['DROP_CONSTRAINT'])

    def format_drop_table_constraint_action(self, expr) -> Tuple[str, tuple]:
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        # The addressing decision is core's, made once for every backend by
        # ``_resolve_drop_constraint_address``: name-only is an address, a
        # declaration-only action is a kind address (refused by feature name
        # here, because ``supports_drop_constraint_by_kind()`` is inherited
        # ``False`` and stays that way -- the kind spellings this mixin keeps
        # are its internals, not a service it offers), a declaration
        # accompanying a name only confirms that name, and an unequal or
        # unnamed declaration is an ambiguous address refused by feature name.
        # Neither address keeps core's ValueError, and a non-TableConstraint
        # declaration its TypeError -- this override used to restate these
        # checks locally, which let it drift from the name-only formatter core
        # applies to every other backend.
        address = self._resolve_drop_constraint_address(expr)
        if address != "name":
            # Reachable only when a subclass advertises
            # ``supports_drop_constraint_by_kind()``; the resolver returned a
            # kind address, and this formatter has no kind spelling to render.
            raise NotImplementedError(
                f"{self.name} advertises supports_drop_constraint_by_kind() "
                f"but does not override format_drop_table_constraint_action; "
                f"a declaration-only drop has no name to render."
            )
        name = cast(str, expr.constraint_name)
        # MariaDB PRIMARY KEY goes through DROP PRIMARY KEY (no IF EXISTS).
        if name.upper() == "PRIMARY":
            return "DROP PRIMARY KEY", ()
        if not self.supports_drop_constraint():
            raise UnsupportedFeatureError(
                self.name,
                "ALTER TABLE DROP CONSTRAINT",
                "DROP CONSTRAINT requires MariaDB 10.2.1 or later. Earlier "
                "releases spell it by kind: DROP FOREIGN KEY for a foreign "
                "key, DROP PRIMARY KEY for the primary key, and "
                "DROP INDEX / DROP KEY for an index."
            )
        if getattr(expr, "if_exists", None) is True:
            if not self.supports_drop_constraint_if_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "DROP CONSTRAINT IF EXISTS",
                    "DROP CONSTRAINT IF EXISTS requires MariaDB 10.2.1 or later."
                )
            result = f"DROP CONSTRAINT IF EXISTS {self.format_identifier(name)}"
        else:
            result = f"DROP CONSTRAINT {self.format_identifier(name)}"
        if getattr(expr, "cascade", None):
            result += " CASCADE"
        return result, ()
