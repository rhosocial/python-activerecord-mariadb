# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl_table.py
"""MariaDB table DDL mixin.

MariaDB-specific features:
- ENGINE storage engine selection
- CHARSET/COLLATE character set options
- AUTO_INCREMENT column attribute
- Inline index definitions in CREATE TABLE
- Table-level COMMENT
- CREATE TABLE ... LIKE syntax
"""
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        ColumnDefinition,
        IndexDefinition,
        TableConstraint,
        TableForeignKeyConstraint,
    )


class MariaDBTableMixin:
    """MariaDB table DDL implementation.

    MariaDB-specific features:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    """

    def supports_create_table_like(self) -> bool:
        """MariaDB supports CREATE TABLE ... LIKE syntax."""
        return True


    def supports_create_table_as_bind_parameters(self) -> bool:
        """MariaDB accepts bind parameters in a CTAS body.

        Measured on 13.1rc: ``CREATE TABLE t AS SELECT %s FROM s`` is
        accepted and the table is created. MariaDB's "parameters" are
        interpolated client-side, so the value is baked into the text.
        """
        return True
    def format_create_table_like_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE by delegating to the generic renderer.

        MariaDB uses the generic vendor form
        ``CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <t> LIKE <src>`` provided by
        the core ``TableMixin``; this override only forwards to it so that the
        MariaDB-specific mixin satisfies the protocol it advertises.

        No object-kind check here, and that is deliberate rather than an
        oversight: the check belongs to the renderer that reads the slots, and
        this one is core's. Delegating keeps it.
        """
        return super().format_create_table_like_statement(expr)

    def supports_inline_index(self) -> bool:
        """MariaDB allows inline INDEX/KEY definitions."""
        return True

    def supports_table_comment(self) -> bool:
        """Whether inline ``COMMENT 'text'`` on ``CREATE TABLE`` is supported.

        MariaDB renders the table comment as an inline table option (and the
        column comment inside the column definition), so both capabilities
        advertise True and the inline path is the rendering path.
        """
        return True

    def supports_column_comment(self) -> bool:
        """Whether inline ``COMMENT 'text'`` in a column definition is
        supported. MariaDB renders it natively."""
        return True

    def supports_storage_engine_option(self) -> bool:
        """MariaDB supports multiple storage engines."""
        return True

    def supports_charset_option(self) -> bool:
        """MariaDB supports CHARSET/COLLATE at table level."""
        return True

    def supports_create_or_replace_table(self) -> bool:
        """Whether CREATE OR REPLACE TABLE is supported.

        MariaDB 10.1+ supports CREATE OR REPLACE TABLE.

        Returns:
            True if MariaDB version >= 10.1.0.
        """
        return self.version >= (10, 1, 0)

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement for MariaDB.

        Handles MariaDB-specific syntax including:
        - Inline index definitions
        - Storage options (ENGINE, CHARSET, COLLATE)
        - Table-level comments
        - AUTO_INCREMENT in column definitions

        Raises:
            TypeError: ``expr.table`` is not a Table. A view would render as a
                well-formed CREATE TABLE over that view's name.
            UnsupportedFeatureError: If the dialect does not support a
                MariaDB-refused option.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.objects import Table

        if not isinstance(expr.table, Table):
            raise TypeError(
                f"CreateTableStatement.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        if expr.tablespace:
            raise UnsupportedFeatureError(
                self.name, "TABLESPACE",
                "MariaDB does not support table tablespaces.",
            )
        if expr.inherits:
            raise UnsupportedFeatureError(
                self.name, "table INHERITS",
                "MariaDB does not support table inheritance.",
            )
        all_params: List[Any] = []

        options_part = ""
        # ``table_options`` is a declared field of the core statement (the
        # ``CreateTableOptions`` header modifiers), so it is read by name;
        # ``None`` is its declared default, not a probe fallback.
        table_options = expr.table_options
        if table_options is not None:
            options_sql, options_params = table_options.to_sql()
            if options_sql:
                options_part = options_sql
            all_params.extend(options_params)
        parts = ["CREATE"]
        if options_part:
            parts.append(options_part)
        if expr.temporary:
            parts.append("TEMPORARY")
        parts.append("TABLE")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        # ``expr.table`` is the row-source reference the core statement
        # already built; it renders through the dialect's qualified-name
        # path, so a schema-qualified CREATE TABLE keeps its database
        # instead of being flattened to a bare name here.
        table_sql, table_params = expr.table.to_sql()
        parts.append(table_sql)
        all_params.extend(table_params)

        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self.format_column_definition(col_def)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        for t_const in expr.table_constraints:
            const_sql, const_params = self.format_table_constraint(t_const)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        for idx_def in expr.indexes:
            idx_sql, idx_params = self.format_index_definition(idx_def)
            column_parts.append(idx_sql)
            all_params.extend(idx_params)

        parts.append(f"({', '.join(column_parts)})")

        if expr.storage_options:
            storage_sql = self._format_storage_options(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        from rhosocial.activerecord.backend.impl.mariadb.expression.table_options import (
            MariaDBCreateTableOptions,
        )
        # The second read is the same declared field as above: the comment is
        # part of the generic ``CreateTableOptions`` contract, so both reads
        # are by name rather than probes.
        table_options = expr.table_options
        if table_options is not None and table_options.comment is not None:
            comment_sql, _ = self.format_table_comment_clause(table_options.comment)
            parts.append(comment_sql.strip())

        if isinstance(table_options, MariaDBCreateTableOptions):
            if table_options.engine:
                parts.append(f"ENGINE={self.inline_sql_literal(table_options.engine)}")
            if table_options.charset:
                parts.append(f"DEFAULT CHARSET={self.inline_sql_literal(table_options.charset)}")
            if table_options.collate:
                parts.append(f"COLLATE={self.inline_sql_literal(table_options.collate)}")
            if table_options.auto_increment is not None:
                parts.append(f"AUTO_INCREMENT={int(table_options.auto_increment)}")
            if table_options.row_format:
                parts.append(f"ROW_FORMAT={table_options.row_format}")
            if table_options.with_system_versioning:
                if not self.supports_system_versioning():
                    from rhosocial.activerecord.backend.dialect.exceptions import (
                        UnsupportedFeatureError,
                    )
                    raise UnsupportedFeatureError(
                        self.name,
                        "WITH SYSTEM VERSIONING",
                        "System-versioned tables require MariaDB 10.3 or later.",
                    )
                parts.append("WITH SYSTEM VERSIONING")

        return ' '.join(parts), tuple(all_params)

    def format_column_definition(
        self,
        col_def: "ColumnDefinition",
    ) -> Tuple[str, tuple]:
        """Format a single column definition with MariaDB-specific syntax.

        Accepts both the generic ``ColumnDefinition`` and the MariaDB
        ``MariaDBColumnDefinition``; the latter's MariaDB-only attributes
        (``character_set`` / ``column_format`` / ``storage`` / ``invisible``)
        are rendered here.

        The constraint clauses themselves are **not** spelled here any more.
        Each one goes through :meth:`format_column_constraint`, which renders
        the production (the ``CONSTRAINT <name>`` prefix and the traits) and
        dispatches to the branch. Before the two-level nodes this method
        carried its own switch on the fat node's ``constraint_type`` field and
        knew only five kinds -- a column-level CHECK or a column-level
        REFERENCES was constructed, accepted, and then dropped on the floor,
        on a server that enforces both (see
        :meth:`MariaDBDialect.supports_check_constraint` and
        :meth:`MariaDBDialect.supports_foreign_key_constraint`).
        """
        from rhosocial.activerecord.backend.impl.mariadb.expression.column import (
            MariaDBColumnDefinition,
        )

        type_sql, type_params = col_def.data_type.to_sql()
        parts = [self.format_identifier(col_def.name), type_sql]
        params: List[Any] = list(type_params)

        constraint_parts = []
        for constraint in col_def.constraints:
            clause_sql, clause_params = self.format_column_constraint(constraint)
            if clause_sql:
                constraint_parts.append(clause_sql.strip())
                params.extend(clause_params)

        if constraint_parts:
            parts.append(' '.join(constraint_parts))

        attr_sql, attr_params = self.format_column_attributes(col_def)
        if attr_sql:
            parts.append(attr_sql.strip())
        params.extend(attr_params)

        if isinstance(col_def, MariaDBColumnDefinition):
            if col_def.character_set:
                parts.append(f"CHARACTER SET {self.format_identifier(col_def.character_set)}")
            if col_def.column_format is not None:
                parts.append(f"COLUMN_FORMAT {col_def.column_format.value}")
            if col_def.storage is not None:
                parts.append(f"STORAGE {col_def.storage.value}")
            if col_def.invisible:
                parts.append("INVISIBLE")

        if col_def.comment is not None:
            comment_sql, _ = self.format_column_comment_clause(col_def.comment)
            parts.append(comment_sql.strip())

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            parts.append(gen_sql.lstrip())
            params.extend(gen_params)

        return ' '.join(parts), tuple(params)

    def format_table_constraint(
        self,
        t_const: "TableConstraint",
    ) -> Tuple[str, tuple]:
        """Format a table-level constraint clause, narrowing what MariaDB lacks.

        The production-level rendering -- the ``CONSTRAINT <name>`` prefix, the
        branch's own body, and the deferral / enforcement traits -- is core's
        and is delegated to unchanged. What stays here is the part that is
        MariaDB's: the kinds this server cannot state at all, refused by name
        rather than rendered into SQL its parser rejects.
        """
        self._require_table_constraint(t_const)
        return super().format_table_constraint(t_const)

    def _require_table_constraint(self, t_const: "TableConstraint") -> None:
        """Refuse what MariaDB's table-constraint grammar has no slot for.

        Three things, each decided here rather than left to the delegated
        rendering, and each keyed off the **branch class** or the trait rather
        than the removed ``constraint_type`` tag.

        * **CHECK is version-gated** at 10.2.1 (``MARIADB_VERSION_BOUNDARIES
          ['CHECK_CONSTRAINT']``); core's table-level CHECK formatter does not
          ask about that boundary, so a dialect older than it would render a
          clause its server has no token for.
        * **The deferral trait** (``DEFERRABLE`` / ``NOT DEFERRABLE`` /
          ``INITIALLY``) has no grammar here at all -- measured errno 1064 for
          every spelling on 13.1.1 and on 10.2.44 / 10.4.34 / 10.5.29 / 12.0.2 /
          12.1.2 -- so the probe answers ``False`` and the request is refused by
          name rather than dropped.
        * **The enforcement trait** (``ENFORCED`` / ``NOT ENFORCED``) is the
          same on every kind, including CHECK: errno 1064 for both spellings on
          every measured server. The kind is not what decides it, so the
          refusal is stated once here rather than per branch.

        The deferral refusal also happens to be the only way this backend can
        refuse it: core's ``DDLColumnMixin.format_table_constraint`` raises
        ``UnsupportedFeatureError`` in that branch without importing the name
        first (``ddl_column.py``, introduced by core's S3 commit ``8448dfb5``),
        so delegating an unsupported deferral request raises
        ``UnboundLocalError`` instead. Refusing before the delegation is both
        the correct narrowing and a way around that defect. A subclass that
        answers ``True`` for ``supports_deferrable_constraint`` is not refused
        here and reaches core's rendering.

        Refusing ENFORCED here as well is not about that defect -- core's
        refusal would work -- but about the spelling: core's message names the
        trait as ``ENFORCED/NOT ENFORCED constraint``, which does not tell a
        caller which of the two it asked for. The pair is consumed one spelling
        at a time, so each side is refused by its own name.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )
        from rhosocial.activerecord.backend.expression import TableCheckConstraint

        if not self.supports_deferrable_constraint() and (
            t_const.deferrable
            or t_const.not_deferrable
            or t_const.initially_deferred
            or t_const.initially_immediate
        ):
            if t_const.deferrable or t_const.not_deferrable:
                feature = "CONSTRAINT DEFERRABLE" if t_const.deferrable else "CONSTRAINT NOT DEFERRABLE"
            else:
                feature = (
                    "CONSTRAINT INITIALLY DEFERRED"
                    if t_const.initially_deferred
                    else "CONSTRAINT INITIALLY IMMEDIATE"
                )
            raise UnsupportedFeatureError(
                self.name,
                feature,
                f"{self.name} does not support {feature}.",
            )

        if (t_const.enforced or t_const.not_enforced) and not self.supports_constraint_enforced():
            feature = "CONSTRAINT ENFORCED" if t_const.enforced else "CONSTRAINT NOT ENFORCED"
            raise UnsupportedFeatureError(
                self.name,
                feature,
                f"{self.name} does not support {feature}.",
            )

        if not isinstance(t_const.branch, TableCheckConstraint):
            return
        if not self.supports_check_constraint():
            raise UnsupportedFeatureError(
                self.name,
                "CHECK constraint",
                f"{self.name} does not support CHECK constraints.",
            )

    def format_column_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format a column-level constraint clause, refusing what has no slot for it.

        Two narrowings live here, both of them facts about MariaDB's column
        definition grammar rather than about the server's capabilities as a
        whole, and both of them invisible to a probe.

        **A name.** ``CONSTRAINT <symbol>`` in a **column definition** is
        accepted for exactly one kind and refused with **errno 1064 / SQLSTATE
        42000** for the rest. Measured on **13.1.1** (192.168.1.3:15694,
        TLSv1.2), every one of these is a syntax error::

            u  INT CONSTRAINT uq_u UNIQUE                 -- 1064
            u  INT CONSTRAINT uq_u UNIQUE KEY             -- 1064
            u  INT UNIQUE KEY CONSTRAINT uq_u             -- 1064
            id INT CONSTRAINT pk_id PRIMARY KEY           -- 1064
            id INT PRIMARY KEY CONSTRAINT pk_id           -- 1064
            c  INT CONSTRAINT ck_c CHECK (c > 0)          -- 1064
            c  INT CHECK (c > 0) CONSTRAINT ck_c          -- 1064

        and the one that works is the column-level foreign key::

            p  INT CONSTRAINT fk_p REFERENCES parent (id)   -- accepted
                -> CONSTRAINT `fk_p` FOREIGN KEY (`p`) REFERENCES `parent` (`id`)
            p  INT REFERENCES parent (id) CONSTRAINT fk_p   -- 1064

        So the name has to precede the ``REFERENCES``, and it is the *only*
        column-level kind with a slot for it.

        **The enforcement trait.** ``[NOT] ENFORCED`` is refused for every kind
        on every measured server -- errno 1064, ``near 'ENFORCED'`` / ``near
        'NOT ENFORCED'`` -- and the column level is no exception. Core refuses
        it too, through ``_format_constraint_enforcement``, but names the trait
        as ``ENFORCED/NOT ENFORCED constraint``; refusing it here says which of
        the two the caller asked for.

        The refusals happen here rather than in core's
        :meth:`format_column_constraint` because that method is the public seam
        that renders the prefix and the traits, and overriding it is what lets
        this backend keep the family-level answer
        (:meth:`MariaDBDialect.supports_constraint_naming` -- ``True``, from the
        table level) separate from the column-level one, which is narrower than
        any single boolean.

        Both are tightenings: before the two-level nodes the name was accepted
        by the node and then ignored by the formatter, so a caller asking for a
        named column constraint silently got an unnamed one.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )
        from rhosocial.activerecord.backend.expression import ColumnForeignKeyConstraint

        if constraint.name and not isinstance(constraint.branch, ColumnForeignKeyConstraint):
            raise UnsupportedFeatureError(
                self.name,
                "CONSTRAINT name on a column constraint",
                f"{self.name} accepts a CONSTRAINT name on a column constraint "
                f"only before REFERENCES.",
            )

        if (constraint.enforced or constraint.not_enforced) and not self.supports_constraint_enforced():
            feature = "CONSTRAINT ENFORCED" if constraint.enforced else "CONSTRAINT NOT ENFORCED"
            raise UnsupportedFeatureError(
                self.name,
                feature,
                f"{self.name} does not support {feature}.",
            )

        return super().format_column_constraint(constraint)

    def format_column_primary_key_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format the column-level ``PRIMARY KEY`` branch, with MariaDB's ``AUTO_INCREMENT``.

        S3 put the flag where the grammar puts it -- on
        :class:`ColumnPrimaryKeyConstraint` -- so this is where it is spelled.
        MariaDB spells it as a bare marker after ``PRIMARY KEY``, and it is
        routed through :meth:`format_auto_increment_clause` so the marker the
        server sees is the one ``supports_auto_increment_column`` answered for
        rather than a string appended behind the probe's back.

        Measured on **13.1.1**: ``id INT PRIMARY KEY AUTO_INCREMENT NOT NULL``
        is accepted and auto-increments, so the marker does not have to precede
        the key the way the CREATE TABLE reference page spells it
        (``NOT NULL AUTO_INCREMENT PRIMARY KEY``) -- both orders were measured
        accepted, and this is the order the branch puts them in.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )

        if not self.supports_primary_key_constraint():
            raise UnsupportedFeatureError(
                self.name,
                "PRIMARY KEY column constraint",
                f"{self.name} does not support PRIMARY KEY constraints.",
            )
        if not constraint.is_auto_increment:
            return " PRIMARY KEY", ()
        from rhosocial.activerecord.backend.expression.statements import (
            AutoIncrementClause,
        )

        marker_sql, marker_params = self.format_auto_increment_clause(
            AutoIncrementClause(self)
        )
        return f" PRIMARY KEY{marker_sql}", tuple(marker_params)

    def format_table_foreign_key_constraint(
        self, constraint: "TableForeignKeyConstraint"
    ) -> Tuple[str, tuple]:
        """Format a table-level ``FOREIGN KEY`` with MariaDB's spaced column list.

        MariaDB's own DDL -- the spelling ``SHOW CREATE TABLE`` writes back --
        sets the referenced column list off with a space, ``FOREIGN KEY (`d`)
        REFERENCES `p` (`id`)``, and this backend's rendering did the same
        before the two-level nodes: the old ``format_table_constraint`` spelled
        the whole clause itself. Keeping the space is what makes the migration
        byte-preserving rather than a silent re-spelling, so the reference body
        is re-spaced here instead of taking core's ``REFERENCES t(c)``.

        The referential actions and ``MATCH`` still ride the shared
        ``ReferencesClause`` machinery, so the capability probes stay consulted
        (``supports_fk_match`` refuses ``MATCH`` on this server; see
        :meth:`MariaDBDialect.supports_fk_on_update` for the ``ON UPDATE
        CASCADE`` / CHECK conflict measured at 10.5).

        The **column-level** ``REFERENCES`` keeps core's unspaced spelling: it
        went through ``format_references_clause`` before the migration too, and
        the two levels were not alike then either. Changing one of them here
        would be a re-spelling the server was never asked about.

        Raises:
            ValueError: The local columns, the referenced columns or the
                referenced table are missing.
        """
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            ReferencesClause,
        )

        if not constraint.columns:
            raise ValueError(
                "FOREIGN KEY constraint must have at least one local column specified."
            )
        referenced_table, referenced_columns = constraint.references
        if not referenced_columns:
            raise ValueError(
                "FOREIGN KEY constraint must have at least one foreign key column specified."
            )
        if not referenced_table:
            raise ValueError("FOREIGN KEY constraint must have a foreign key table specified.")
        cols_str = ", ".join(self.format_identifier(c) for c in constraint.columns)
        references = ReferencesClause(
            self,
            referenced_table,
            list(referenced_columns),
            on_delete=constraint.on_delete,
            on_update=constraint.on_update,
            match_type=constraint.match_type,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        # The shared clause renders "REFERENCES <table>(<cols>)..."; MariaDB
        # spells the column list with a space: "REFERENCES <table> (<cols>)...".
        head, rest = ref_sql.split("(", 1)
        return f"FOREIGN KEY ({cols_str}) {head} ({rest}", tuple(ref_params)

    def format_index_definition(self, idx_def: "IndexDefinition") -> Tuple[str, tuple]:
        """Format an inline index definition (MariaDB-specific)."""
        parts = []

        if idx_def.unique:
            parts.append("UNIQUE")

        parts.append("INDEX")
        parts.append(self.format_identifier(idx_def.name))

        cols_str = ', '.join(self.format_identifier(c) for c in idx_def.columns)
        parts.append(f"({cols_str})")

        if idx_def.type:
            parts.append(f"USING {idx_def.type}")

        return ' '.join(parts), ()

    def _format_storage_options(self, storage_options: Dict[str, Any]) -> str:
        parts = []
        for key, value in storage_options.items():
            rendered = self.inline_sql_literal(value)
            parts.append(f"{key}={rendered}")
        return ' '.join(parts)


__all__ = ['MariaDBTableMixin']