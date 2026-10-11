# src/rhosocial/activerecord/backend/impl/mariadb/dialect.py
"""
MariaDB backend SQL dialect implementation.

This dialect implements protocols for features that MariaDB supports,
based on the MariaDB version provided at initialization.

MariaDB version-specific features:
- Window functions (since 10.2)
- CTE (since 10.2)
- INTERSECT/EXCEPT (since 10.3)
- SEQUENCE (since 10.3)
- System-versioned tables (since 10.3)
- RETURNING clause (since 10.5)
- JSON functions (since 10.2.3)
- JSON arrow operators (since 10.2.7)
- EXPLAIN FORMAT (since 10.6)
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import (
    # Named-object protocols: how each kind of catalogue entry is spelled.
    # MariaDB's spelling is core's default -- `catalog`.`name` -- so none of
    # these needs a method of its own here.
    TableObjectSupport,
    ViewObjectSupport,
    IndexObjectSupport,
    SequenceObjectSupport,
    TriggerObjectSupport,
    RoutineObjectSupport,
    TypeObjectSupport,
    NamespaceSupport,
    CollationSupport,
    CTESupport,
    WindowFunctionSupport,
    ReturningSupport,
    SetOperationSupport,
    UpsertSupport,
    ExplainSupport,
    JoinSupport,
    WildcardSupport,
    ILIKESupport,
    FilterClauseSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    LateralJoinSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    OrderedSetAggregationSupport,
    GraphSupport,
    # DDL Protocols (non-overlapping with MariaDB-specific)
    TruncateSupport,
    ConstraintSupport,
    IntrospectionSupport,
    TransactionControlSupport,
    GeneratedColumnSupport,
    # One protocol per mechanism: MariaDB accepts the parameterless
    # AUTO_INCREMENT marker and refuses the parameterised standard identity
    # clause, so both interfaces are declared and the probes carry the answer.
    AutoIncrementColumnSupport,
    IdentityColumnSupport,
    # Additional Protocols
    SQLFunctionSupport,
    DataTypeSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CollationMixin,
    CTEMixin,
    WindowFunctionMixin,
    JSONMixin,
    SetOperationMixin,
    SequenceMixin,
    UpsertMixin,

    ExplainMixin,
    JoinMixin,
    ILIKEMixin,

    ArrayMixin,
    LateralJoinMixin,
    MergeMixin,
    TemporalTableMixin,

    GraphMixin,
    RelationSourceMixin,
    # DDL Mixins
    TableMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    TriggerMixin,
    GeneratedColumnMixin,
    # The formatters for the two identity mechanisms; MariaDB's own answers
    # for their probes live on MariaDBGeneratedColumnMixin, which precedes
    # these in the MRO.
    AutoIncrementMixin,
    IdentityColumnMixin,
    ViewMixin,
    FunctionMixin,
    IntrospectionMixin,
    # Additional Mixins
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    TransactionControlMixin,
    PartitionMixin,
    # TRIM/LPAD/RPAD/REPEAT are nodes with default formatters, and MariaDB
    # spells all four natively -- ``TRIM([BOTH|LEADING|TRAILING] [chars] FROM
    # str)``, ``LPAD``/``RPAD(str, len, padstr)`` and ``REPEAT(str, n)`` -- so
    # the shared defaults are the answer here and no override is needed.
    LpadMixin,
    RepeatMixin,
    RpadMixin,
    TrimMixin,
    # Naming. Each of these is core's default renderer for one kind of
    # object, placed ahead of NamespaceMixin so that C3 keeps the per-kind
    # formatter in front of the shared namespace prefix. MariaDB's spelling
    # differs from none of them, so none of them is overridden here.
    TableNameMixin,
    ViewNameMixin,
    MaterializedViewNameMixin,
    ForeignTableNameMixin,
    IndexNameMixin,
    SequenceNameMixin,
    TriggerNameMixin,
    FunctionNameMixin,
    ProcedureNameMixin,
    TypeNameMixin,
    DomainNameMixin,
    SynonymNameMixin,
    SchemaNameMixin,
    DatabaseNameMixin,
    PropertyGraphNameMixin,
    NamespaceMixin,
)

# Import MariaDB-specific mixins
from .mixins import (
    MariaDBIntrospectionMixin,  # Must be before IntrospectionMixin
    MariaDBSequenceMixin,
    MariaDBReturningMixin,
    MariaDBSystemVersioningMixin,
    MariaDBDMLOperationMixin,
    MariaDBSpatialMixin,
    MariaDBLockingMixin,
    MariaDBTriggerMixin,
    MariaDBJSONMixin,
    MariaDBFullTextSearchMixin,
    MariaDBTableMixin,
    MariaDBDatabaseMixin,
    MariaDBSetTypeMixin,
    MariaDBModifyColumnMixin,
    MariaDBPartitionMixin,
    MariaDBTypeSupportMixin,
    MariaDBAlterColumnModifierMixin,
    MariaDBAlterConstraintModifierMixin,
    MariaDBRenameTableMixin,
    MariaDBTruncateMixin,
    MariaDBAlterTableMixin,
    MariaDBMaintenanceMixin,
    MariaDBRoutineMixin,
    MariaDBAdminMixin,
    MARIADB_VERSION_BOUNDARIES,
    # New mixins from dialect.py split
    MariaDBDateTimeMixin,
    MariaDBCharsetCollationMixin,
    MariaDBCTEMixin,
    MariaDBWindowMixin,
    MariaDBFilterClauseMixin,
    MariaDBSetOperationMixin,
    MariaDBDQLMixin,
    MariaDBUpsertMixin,
    MariaDBExplainMixin,
    MariaDBGroupingMixin,
    MariaDBJoinMixin,
    MariaDBTemporalMixin,
    MariaDBArrayMixin,
    MariaDBDDLColumnMixin,
    MariaDBViewMixin,
    MariaDBGeneratedColumnMixin,
    MariaDBFunctionMixin,
    MariaDBNamespaceMixin,
    MariaDBColumnTypeMixin,
)
from .reserved_words import reserved_words_for_version
from .show.dialect import MariaDBShowDialectMixin

# Import MariaDB-specific protocols
from .protocols import (
    MariaDBDMLOperationSupport,
    MariaDBTriggerSupport,
    MariaDBTableSupport,
    MariaDBSetTypeSupport,
    MariaDBJSONFunctionSupport,
    MariaDBSpatialSupport,
    MariaDBFullTextSearchSupport,
    MariaDBLockingSupport,
    MariaDBModifyColumnSupport,
    MariaDBSequenceSupport,
    MariaDBReturningSupport,
    MariaDBIntersectExceptSupport,
    MariaDBSystemVersioningSupport,
    MariaDBWindowFunctionSupport,
    MariaDBCTESupport,
    MariaDBPartitionSupport,
    MariaDBRenameTableSupport,
    MariaDBAlterTableSupport,
    MariaDBMaintenanceSupport,
    MariaDBRoutineSupport,
    MariaDBAdminSupport,
    MariaDBTypeSupport,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        ReturningClause,
    )

_SUGGESTION_GRAPH_MATCH = "MariaDB does not support graph MATCH clause."
_SUGGESTION_ORDERED_SET_AGG = "MariaDB does not support ordered-set aggregate functions (WITHIN GROUP)."
_SUGGESTION_QUALIFY = "MariaDB does not support QUALIFY clause. Use a subquery or CTE instead."
_SUGGESTION_MERGE = "MariaDB does not support MERGE statement. Use INSERT ... ON DUPLICATE KEY UPDATE instead."
_SUGGESTION_TEMPORAL = "MariaDB system-versioned tables require specific table creation syntax."


class MariaDBDialect(
    SQLDialectBase,
    # Namespaces: MariaDB qualifies by database (the catalog) and has no
    # inner schema, so `MariaDBNamespaceMixin` is the one declaration of which
    # levels a name may carry, and the `*NameMixin` group above it renders
    # each kind through core's default spelling. The inner schema is
    # deliberately absent from the *naming* side:
    # `supports_schema_qualification` stays False because no name here is ever
    # qualified by a schema. `supports_schema` is a different question, owned
    # by core's `SchemaMixin`: MariaDB's `CREATE SCHEMA` is a synonym for
    # `CREATE DATABASE` rather than a second namespace layer, so the DDL
    # switch answers False too.
    TableNameMixin,
    ViewNameMixin,
    MaterializedViewNameMixin,
    ForeignTableNameMixin,
    IndexNameMixin,
    SequenceNameMixin,
    TriggerNameMixin,
    FunctionNameMixin,
    ProcedureNameMixin,
    TypeNameMixin,
    DomainNameMixin,
    SynonymNameMixin,
    SchemaNameMixin,
    DatabaseNameMixin,
    PropertyGraphNameMixin,
    # Ahead of NamespaceMixin, which supplies a default `supports_catalog()`
    # of False: plain mixins are resolved by position rather than by
    # inheritance, so the one that answers for MariaDB has to come first.
    MariaDBNamespaceMixin,
    NamespaceMixin,
    RelationSourceMixin,
    MariaDBIntrospectionMixin,
    MariaDBShowDialectMixin,
    MariaDBSequenceMixin,
    MariaDBReturningMixin,
    MariaDBSystemVersioningMixin,
    MariaDBDMLOperationMixin,
    MariaDBSpatialMixin,
    MariaDBLockingMixin,
    MariaDBTriggerMixin,
    MariaDBJSONMixin,
    MariaDBFullTextSearchMixin,
    MariaDBTableMixin,
    MariaDBDatabaseMixin,
    MariaDBSetTypeMixin,
    MariaDBModifyColumnMixin,
    MariaDBPartitionMixin,
    MariaDBTypeSupportMixin,
    # The column-side type table — which column class each common Python
    # type means on this server. It derives from core's `ColumnTypeMixin`, so
    # it belongs with the MariaDB mixins that own an answer rather than in the
    # group of core mixins that only supply a fallback: core's copy must never
    # sit in the MRO ahead of this one.
    MariaDBColumnTypeMixin,
    MariaDBAlterColumnModifierMixin,
    MariaDBAlterConstraintModifierMixin,
    MariaDBRenameTableMixin,
    MariaDBAlterTableMixin,
    MariaDBMaintenanceMixin,
    MariaDBRoutineMixin,
    MariaDBAdminMixin,
    # New mixins from dialect.py split
    MariaDBDateTimeMixin,
    MariaDBCharsetCollationMixin,
    MariaDBCTEMixin,
    MariaDBWindowMixin,
    MariaDBFilterClauseMixin,
    MariaDBSetOperationMixin,
    MariaDBDQLMixin,
    MariaDBUpsertMixin,
    MariaDBExplainMixin,
    MariaDBGroupingMixin,
    MariaDBJoinMixin,
    MariaDBTemporalMixin,
    MariaDBArrayMixin,
    MariaDBDDLColumnMixin,
    MariaDBViewMixin,
    MariaDBGeneratedColumnMixin,
    MariaDBFunctionMixin,
    CollationMixin,
    CTEMixin,
    WindowFunctionMixin,
    JSONMixin,
    SetOperationMixin,
    SequenceMixin,
    UpsertMixin,

    ExplainMixin,
    JoinMixin,
    ILIKEMixin,

    ArrayMixin,
    LateralJoinMixin,
    MergeMixin,
    TemporalTableMixin,

    GraphMixin,
    TableMixin,
    MariaDBTruncateMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    TriggerMixin,
    GeneratedColumnMixin,
    # The formatters for the two identity mechanisms; MariaDB's own answers
    # for their probes live on MariaDBGeneratedColumnMixin, which precedes
    # these in the MRO.
    AutoIncrementMixin,
    IdentityColumnMixin,
    ViewMixin,
    FunctionMixin,
    IntrospectionMixin,
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    TransactionControlMixin,
    PartitionMixin,
    # TRIM/LPAD/RPAD/REPEAT are nodes with default formatters, and MariaDB
    # spells all four natively -- ``TRIM([BOTH|LEADING|TRAILING] [chars] FROM
    # str)``, ``LPAD``/``RPAD(str, len, padstr)`` and ``REPEAT(str, n)`` -- so
    # the shared defaults are the answer here and no override is needed. (The
    # two-argument ``LPAD(x, n)`` form MariaDB accepts is a separate spelling
    # question the node does not use: it always spells the pad out.)
    LpadMixin,
    RepeatMixin,
    RpadMixin,
    TrimMixin,
    # Protocol support markers
    CollationSupport,
    CTESupport,
    WindowFunctionSupport,
    ReturningSupport,
    SetOperationSupport,
    UpsertSupport,
    ExplainSupport,
    JoinSupport,
    WildcardSupport,
    ILIKESupport,
    FilterClauseSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    LateralJoinSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    OrderedSetAggregationSupport,
    GraphSupport,
    TruncateSupport,
    ConstraintSupport,
    IntrospectionSupport,
    TransactionControlSupport,
    GeneratedColumnSupport,
    # One protocol per mechanism: MariaDB accepts the parameterless
    # AUTO_INCREMENT marker and refuses the parameterised standard identity
    # clause, so both interfaces are declared and the probes carry the answer.
    AutoIncrementColumnSupport,
    IdentityColumnSupport,
    SQLFunctionSupport,
    DataTypeSupport,
    MariaDBDMLOperationSupport,
    MariaDBTriggerSupport,
    MariaDBTableSupport,
    MariaDBSetTypeSupport,
    MariaDBJSONFunctionSupport,
    MariaDBSpatialSupport,
    MariaDBFullTextSearchSupport,
    MariaDBLockingSupport,
    MariaDBModifyColumnSupport,
    MariaDBSequenceSupport,
    MariaDBReturningSupport,
    MariaDBIntersectExceptSupport,
    MariaDBSystemVersioningSupport,
    MariaDBWindowFunctionSupport,
    MariaDBCTESupport,
    MariaDBPartitionSupport,
    MariaDBRenameTableSupport,
    MariaDBAlterTableSupport,
    MariaDBMaintenanceSupport,
    MariaDBRoutineSupport,
    MariaDBAdminSupport,
# Named-object protocols come after the MariaDB-specific ones, and
    # `NamespaceSupport` trails them, on purpose. `MariaDBTableSupport` and
    # `MariaDBTriggerSupport` derive from `TableObjectSupport` and
    # `TriggerObjectSupport`, and every object protocol derives from
    # `NamespaceSupport`: C3 requires a subclass to precede its base, so
    # listing a base ahead of one of its subclasses is an MRO error rather
    # than a precedence question.
    TableObjectSupport,
    ViewObjectSupport,
    IndexObjectSupport,
    SequenceObjectSupport,
    TriggerObjectSupport,
    RoutineObjectSupport,
    TypeObjectSupport,
    NamespaceSupport,
    # MariaDB's own type attributes. Its mixin derives from DataTypeSupport,
    # so it follows the core protocol above for the same C3 reason.
    MariaDBTypeSupport,
):
    """MariaDB dialect implementation that adapts to the MariaDB version.

    MariaDB features and support based on version:
    - Window functions (since 10.2)
    - CTE (since 10.2)
    - JSON functions (since 10.2.3)
    - JSON arrow operators (since 10.2.7)
    - INTERSECT/EXCEPT (since 10.3)
    - SEQUENCE (since 10.3)
    - System-versioned tables (since 10.3)
    - RETURNING clause (since 10.5)
    """

    def __init__(self, version: Optional[Tuple[int, int, int]] = None):
        """Initialize MariaDB dialect with specific version.

        Args:
            version: MariaDB version tuple (major, minor, patch).
                If None, the dialect must be adapted via
                backend.introspect_and_adapt() before version-dependent
                features can be used.
        """
        super().__init__()
        self._reserved_words = reserved_words_for_version(version)
        if version is not None:
            self.version = version

    @property
    def version(self) -> Tuple[int, int, int]:
        return SQLDialectBase.version.fget(self)

    @version.setter
    def version(self, value: Tuple[int, int, int]) -> None:
        # Keep the reserved-word set in step with the version: MariaDB added
        # `conversion` / `to_date` in 12.3 and `deny` in 13.1, and a dialect
        # re-adapted after construction would otherwise keep quoting
        # decisions made for the old version.
        SQLDialectBase.version.fset(self, value)
        self._reserved_words = reserved_words_for_version(value)

    def get_parameter_placeholder(self, position: int = 0) -> str:
        """MariaDB uses positional placeholders like :0, :1 or %s."""
        return "%s"

    def get_server_version(self) -> Tuple[int, int, int]:
        """Return the MariaDB version this dialect is configured for."""
        return self.version

    def create_schema_differ(self):
        """Return the MariaDB schema differ (ordinal-position aware)."""
        from rhosocial.activerecord.backend.impl.mariadb.schema.differ import (
            MariaDBSchemaDiffer,
        )

        return MariaDBSchemaDiffer()

    def format_identifier(self, identifier: str, need_quote: bool = True) -> str:
        """Format identifier using MariaDB's backtick quoting mechanism.

        Args:
            identifier: Raw identifier string

        Returns:
            Quoted identifier with escaped internal backticks
        """
        if not need_quote:
            if self.is_reserved_word(identifier):
                import warnings
                from rhosocial.activerecord.backend.warnings import IdentifierQuotingWarning
                warnings.warn(
                    f"Identifier '{identifier}' is a reserved word in {self.name} "
                    f"and may cause SQL errors without quoting.",
                    IdentifierQuotingWarning,
                    stacklevel=2,
                )
            return identifier
        escaped = identifier.replace('`', '``')
        return f'`{escaped}`'

    # region Type protocol

    def substitute_advice(self, name: str) -> str:
        """State what a MariaDB substitution gives up, in the caller's error.

        ``real`` is the one entry with something to add: MariaDB's ``REAL`` is
        not a storage class but a synonym whose resolution depends on a SQL
        mode this framework does not read, and the catalog never reports the
        word back. The caller has to be told that, or "it suggests DoubleType"
        sounds like a spelling choice rather than the storage the column will
        really have.
        """
        if name == "real":
            return (
                "MariaDB's ``REAL`` is a synonym for ``DOUBLE`` in the default "
                "SQL mode (the DOUBLE page groups ``DOUBLE``, ``DOUBLE "
                "PRECISION`` and ``REAL`` together); only under the "
                "``REAL_AS_FLOAT`` SQL mode does it mean ``FLOAT``. Every wired "
                "server reports a ``REAL`` column as ``double`` (``float`` "
                "under that mode) and never as ``real`` in "
                "``information_schema``, so the single-precision concept cannot "
                "round-trip. Declare ``DoubleType``, or ``FloatType`` for "
                "4-byte single precision."
            )
        return ""

    def suggested_data_types(self) -> Dict[str, type]:
        """What MariaDB stores for each core concept it cannot spell.

        A concept MariaDB genuinely has is **rendered**, not suggested — the
        native ``ENUM`` is the obvious one: it used to appear here as
        ``MariaDBEnumType``, which said "I cannot render this" from a dialect
        that renders ``ENUM(...)`` perfectly well, and a name in both sets is
        one of the two being a lie.

        What is left is the honest remainder — ``uuid`` used to be here and no
        longer is, and ``real`` joins it for the reason its entry gives:

        ``uuid``
            **Removed.** MariaDB has had a native ``UUID`` column type since
            **10.7**, so this concept is *rendered* rather than substituted (see
            ``format_data_type_mariadb_uuid``, which is version-gated). The
            entry that used to sit here claimed MariaDB had no UUID type at all
            and pointed at a 16-byte ``BINARY`` instead — which was true before
            10.7 and false after it, and would have quietly produced a column
            that is not a UUID on every supported server. On a pre-10.7 server
            a UUID is a ``MariaDBBinaryType(length=16)``, and asking for that
            class is the honest way to say so.

        ``real``
            MariaDB documents ``REAL`` as one of the three words for the 8-byte
            type — its DOUBLE page gives ``DOUBLE``, ``DOUBLE PRECISION`` and
            ``REAL`` one grammar and says "``REAL`` and ``DOUBLE PRECISION`` are
            synonyms, unless the ``REAL_AS_FLOAT`` SQL mode is enabled, in which
            case ``REAL`` is a synonym for FLOAT rather than DOUBLE". Measured
            on all fifteen wired servers, 10.2.44 through 13.1.1, which agree
            byte for byte: a ``REAL`` column reports ``COLUMN_TYPE = 'double'``
            (and ``REAL UNSIGNED`` reports ``'double unsigned'``), while under
            ``REAL_AS_FLOAT`` it reports ``'float'``. The catalog therefore
            never writes the word ``real`` back, so the concept cannot
            round-trip: a declared ``RealType`` would introspect as a
            ``DoubleType`` on a default server and as a ``FloatType`` under the
            mode. The substitute is ``DoubleType`` — the storage the default
            server builds — and ``FloatType`` is what to declare when 4-byte
            single precision is what was meant. :meth:`substitute_advice`
            carries that sentence into the caller's error.

        ``binary`` / ``varbinary``
            The converse of the core ``blob`` case, which MariaDB *renders*: a
            ``BLOB`` here is unbounded, so it cannot stand in for a
            width-constrained ``BINARY(n)`` or ``VARBINARY(n)``. The
            substitutes are therefore the backend's own width-carrying classes
            rather than ``MariaDBBinaryType`` for both, which would silently
            drop the ``n`` that is the whole point of ``varbinary``.

        ``array``
            SQL:2016 defines arrays as a *constructed type* over every data
            type, and MariaDB implements none of them — a column cannot be
            declared ``INT[]``. What MariaDB does have is a native ``JSON``
            column that validates its contents, and that is what this backend's
            own array support raises on every array operation it cannot do
            ("Use JSON arrays instead"). So the substitute is ``JsonType``,
            which is what a MariaDB array is actually made of.

        ``xml``
            **Version-dependent, because MariaDB's answer changed.**
            MariaDB had no XML type at all before **12.3**: not a native one,
            not an alias, no ``XML`` keyword in its DDL grammar, and
            ``CREATE TABLE t (c XML)`` fails with errno 4161. On such a server an
            XML document is text with no validation applied to it, which is what
            ``TextType`` says — an accurate description of the storage rather
            than a consolation prize.

            From **12.3** MariaDB has a native ``XMLTYPE`` column type, and
            substituting ``TEXT`` there would be simply wrong: the backend can
            store a real XML column. The substitute becomes
            :class:`~...expression.types.MariaDBXmlType` — "basic XML storage
            capabilities only, without validation or specialized XML-specific
            functionality", 4 GB maximum "same as ``LONGBLOB``", no length
            permitted — which is a genuinely different column from ``TEXT``, so
            the suggestion has to follow the server rather than stay fixed.
            (PostgreSQL, which has ``XML`` natively *and* validates it against a
            registered schema, is why the two backends differ here and neither is
            wrong.)

        ``interval``
            The one suggestion with no exact answer, so the reasoning is worth
            stating. ``INTERVAL`` on MariaDB is an **expression** keyword —
            ``INTERVAL 1 DAY`` inside ``DATE_ADD`` — and never a column type,
            so there is nothing for an interval *column* to be. A span has to be
            stored as something else, and the two candidates are both lossy:
            ``TIME`` holds at most 838:59:59 (about 34 days) and has no notion
            of months or years at all, while an integer has no unit. What is
            left is the character form MariaDB's own interval arithmetic
            produces — ``1 02:03:04.000000`` — which is why the suggestion is
            ``VarCharType``: bounded, and readable by a human debugging a row.
            It is a suggestion, not a promise, and the caller is free to store
            seconds in a ``BIGINT`` instead.
        """
        from rhosocial.activerecord.backend.expression.types import (
            DoubleType,
            JsonType,
            TextType,
            VarCharType,
        )
        from .expression.types import (
            MariaDBUUIDType,
            MariaDBBinaryType,
            MariaDBVarBinaryType,
            MariaDBXmlType,
        )

        # The one version-dependent entry. MariaDB 12.3 added the native
        # ``XMLTYPE`` column type, and before it there was no XML type at all;
        # naming ``TextType`` unconditionally would be wrong on every 12.3+ server
        # (the backend *can* store an XML column there) and naming
        # ``MariaDBXmlType`` unconditionally would point a 12.2 or 11.x caller at
        # a type whose formatter refuses to render. The key stays ``xml`` either
        # way, so a caller asking "what does this backend do with XML?" gets an
        # answer on every server, and the class it names is one this dialect can
        # actually render — the property ``verify_backend.py`` checks.
        xml_substitute = (
            MariaDBXmlType
            if self.version >= MARIADB_VERSION_BOUNDARIES["XMLTYPE"]
            else TextType
        )

        return {
            "binary": MariaDBBinaryType,
            "varbinary": MariaDBVarBinaryType,
            "real": DoubleType,
            "array": JsonType,
            "xml": xml_substitute,
            "interval": VarCharType,
        }

    # endregion

    # region Custom implementations
    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, tuple]:
        """Format RETURNING clause for MariaDB."""
        all_params = []
        expr_parts = []
        for expr in clause.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        returning_sql = f"RETURNING {', '.join(expr_parts)}"
        return returning_sql, tuple(all_params)

    # endregion

    # region ConstraintSupport protocol implementation (MariaDB)

    def supports_primary_key_constraint(self) -> bool:
        return True

    def supports_unique_constraint(self) -> bool:
        return True

    def supports_not_null_constraint(self) -> bool:
        return True

    def supports_check_constraint(self) -> bool:
        return self.version >= MARIADB_VERSION_BOUNDARIES['CHECK_CONSTRAINT']

    def supports_foreign_key_constraint(self) -> bool:
        return True

    def supports_fk_on_delete(self) -> bool:
        return True

    def supports_fk_on_update(self) -> bool:
        return True

    def supports_fk_match(self) -> bool:
        return False

    def supports_deferrable_constraint(self) -> bool:
        """Whether ``DEFERRABLE`` / ``INITIALLY ...`` constraints are supported.

        Measured False on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc, and MariaDB
        10.6's grammar (``sql_yacc.yy``) has no ``DEFERRABLE`` or ``INITIALLY``
        token. Both spellings of the deferral pair are refused by name rather
        than dropped.
        """
        return False

    def supports_constraint_enforced(self) -> bool:
        """Whether ``CHECK ... [NOT] ENFORCED`` is supported.

        Measured False on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc: every version
        rejects ``CHECK (a > 0) ENFORCED`` and ``... NOT ENFORCED`` in CREATE
        TABLE and in ``ALTER TABLE ... ADD CONSTRAINT`` with errno 1064
        (sentinel rejected), and MariaDB 10.6's grammar has no ``ENFORCED``
        token. The previous declaration (``version >= (10, 2, 22)``) was never
        measured; the version belongs to MySQL's clause, not MariaDB's.
        """
        return False

    def supports_add_constraint(self) -> bool:
        return True

    def supports_drop_constraint(self) -> bool:
        return True

    # endregion

    # region TransactionControlSupport protocol implementation (MariaDB)

    def supports_transaction_mode(self) -> bool:
        return self.version >= (10, 2, 0)

    def supports_isolation_level_in_begin(self) -> bool:
        return False

    def supports_read_only_transaction(self) -> bool:
        return self.version >= (10, 2, 0)

    def supports_deferrable_transaction(self) -> bool:
        return False

    def supports_transaction_wait(self) -> bool:
        """Whether the ``WAIT`` / ``NO WAIT`` transaction clause is supported.

        Measured False on all 19 configured servers (10.2.44 ... 13.1.1):
        ``START TRANSACTION WAIT`` / ``NO WAIT`` / ``NOWAIT`` / ``WAIT 5``
        and ``BEGIN WAIT`` are syntax errors (errno 1064) everywhere;
        ``SET TRANSACTION WAIT`` / ``NO WAIT`` are rejected everywhere too
        (errno 1193 on 10.2, 1064 from 10.3). Every connection and group
        carried a sentinel that came back rejected. MariaDB does have
        ``WAIT n`` / ``NOWAIT`` on TRUNCATE, ALTER TABLE and LOCK TABLES,
        but not on the transaction statements this pair selects -- those are
        separate clauses with their own parameters, not this one.
        """
        return False

    def supports_savepoint(self) -> bool:
        return True

    def format_begin_transaction(self, expr) -> Tuple[str, tuple]:
        """Format BEGIN TRANSACTION statement for MariaDB.

        ``DEFERRABLE`` / ``NOT DEFERRABLE`` is consumed through the transaction
        probe: MariaDB answers ``supports_deferrable_transaction()`` False, so
        an explicit spelling is refused by name rather than dropped; a subclass
        that declares the probe True renders the spelling it declared.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        set_isolation = ""
        if expr._isolation_level is not None:
            level_map = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
            }
            level_name = level_map.get(expr._isolation_level)
            if level_name:
                set_isolation = f"SET TRANSACTION ISOLATION LEVEL {level_name}; "

        if expr._mode == TransactionMode.READ_ONLY:
            begin_sql = "START TRANSACTION READ ONLY"
        elif expr._mode == TransactionMode.READ_WRITE:
            begin_sql = "START TRANSACTION READ WRITE"
        else:
            begin_sql = "START TRANSACTION"

        if expr._deferrable or expr._not_deferrable:
            if not self.supports_deferrable_transaction():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRANSACTION DEFERRABLE"
                    if expr._deferrable
                    else "TRANSACTION NOT DEFERRABLE",
                    f"{self.name} does not support DEFERRABLE transactions.",
                )
            begin_sql += " DEFERRABLE" if expr._deferrable else " NOT DEFERRABLE"

        if expr._wait or expr._no_wait:
            if not self.supports_transaction_wait():
                spelling = "WAIT" if expr._wait else "NO WAIT"
                raise UnsupportedFeatureError(
                    self.name,
                    f"TRANSACTION {spelling}",
                    f"{self.name} does not support the {spelling} transaction clause.",
                )
            begin_sql += " WAIT" if expr._wait else " NO WAIT"

        return f"{set_isolation}{begin_sql}", ()

    def format_set_transaction(self, expr) -> Tuple[str, tuple]:
        """Format SET TRANSACTION statement for MariaDB.

        ``DEFERRABLE`` / ``NOT DEFERRABLE`` is consumed through the transaction
        probe, exactly as in :meth:`format_begin_transaction`.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        parts = ["SET TRANSACTION"]

        if expr._isolation_level is not None:
            level_map = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
            }
            level_name = level_map.get(expr._isolation_level)
            if level_name:
                parts.append(f"ISOLATION LEVEL {level_name}")

        if expr._mode is not None:
            if expr._mode == TransactionMode.READ_ONLY:
                parts.append("READ ONLY")
            elif expr._mode == TransactionMode.READ_WRITE:
                parts.append("READ WRITE")

        if expr._deferrable or expr._not_deferrable:
            if not self.supports_deferrable_transaction():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRANSACTION DEFERRABLE"
                    if expr._deferrable
                    else "TRANSACTION NOT DEFERRABLE",
                    f"{self.name} does not support DEFERRABLE transactions.",
                )
            parts.append("DEFERRABLE" if expr._deferrable else "NOT DEFERRABLE")

        if expr._wait or expr._no_wait:
            if not self.supports_transaction_wait():
                spelling = "WAIT" if expr._wait else "NO WAIT"
                raise UnsupportedFeatureError(
                    self.name,
                    f"TRANSACTION {spelling}",
                    f"{self.name} does not support the {spelling} transaction clause.",
                )
            parts.append("WAIT" if expr._wait else "NO WAIT")

        return " ".join(parts), ()

    # endregion

    # region Explain

    def format_explain_statement(self, expr) -> Tuple[str, tuple]:
        """Format EXPLAIN statement for MariaDB."""
        statement_sql, statement_params = expr.statement.to_sql()
        options = expr.options
        if options is None:
            return f"EXPLAIN {statement_sql}", statement_params

        parts = ["EXPLAIN"]
        from rhosocial.activerecord.backend.expression.statements import ExplainType

        if (hasattr(options, "type") and options.type == ExplainType.ANALYZE) or options.analyze:
            parts.append("ANALYZE")
        if options.format:
            parts.append(f"FORMAT={options.format.value.upper()}")
        if not options.costs:
            parts.append("COSTS OFF")
        if options.verbose:
            parts.append("VERBOSE")

        return f"{' '.join(parts)} {statement_sql}", statement_params

    # endregion

    # region DDL Support - format_create_table_statement

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        value = value.replace('\\', '\\\\')
        value = value.replace("'", "''")
        return value

    def format_table_constraint(
        self,
        t_const: "TableConstraint"
    ) -> Tuple[str, tuple]:
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.statements import (
            TableConstraintType, ForeignKeyConstraint, ReferentialAction,
        )

        parts = []
        params: List[Any] = []

        if t_const.name:
            parts.append(f"CONSTRAINT {self.format_identifier(t_const.name)}")

        if t_const.constraint_type == TableConstraintType.PRIMARY_KEY:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.UNIQUE:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"UNIQUE ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.FOREIGN_KEY:
            if t_const.columns and t_const.foreign_key_table and t_const.foreign_key_columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                ref_cols_str = ', '.join(
                    self.format_identifier(c) for c in t_const.foreign_key_columns
                )
                ref_table = t_const.foreign_key_table.to_sql()[0]
                parts.append(
                    f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table} ({ref_cols_str})"
                )

            if isinstance(t_const, ForeignKeyConstraint):
                if t_const.on_delete != ReferentialAction.NO_ACTION:
                    parts.append(f"ON DELETE {t_const.on_delete.value}")
                if t_const.on_update != ReferentialAction.NO_ACTION:
                    parts.append(f"ON UPDATE {t_const.on_update.value}")

        elif t_const.constraint_type == TableConstraintType.CHECK and t_const.check_condition:
            check_sql, check_params = t_const.check_condition.to_sql()
            parts.append(f"CHECK ({check_sql})")
            params.extend(check_params)

        # The constraint-option pairs: each requested spelling is consumed or
        # refused by name -- never dropped. MariaDB's grammar has no [NOT]
        # ENFORCED, no [NOT] DEFERRABLE and no INITIALLY clause (measured on
        # 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc, sentinels rejected; 10.6's
        # sql_yacc.yy has none of the tokens), so the probes answer False and
        # every spelling is refused. A subclass that flips a probe True renders
        # the spelling it declared.
        if t_const.deferrable or t_const.not_deferrable:
            if not self.supports_deferrable_constraint():
                raise UnsupportedFeatureError(
                    self.name,
                    "CONSTRAINT DEFERRABLE" if t_const.deferrable else "CONSTRAINT NOT DEFERRABLE",
                    f"{self.name} does not support DEFERRABLE constraints.",
                )
            parts.append("DEFERRABLE" if t_const.deferrable else "NOT DEFERRABLE")
        if t_const.initially_deferred or t_const.initially_immediate:
            raise UnsupportedFeatureError(
                self.name,
                "CONSTRAINT INITIALLY DEFERRED"
                if t_const.initially_deferred
                else "CONSTRAINT INITIALLY IMMEDIATE",
                f"{self.name} does not support the INITIALLY constraint attribute.",
            )
        if t_const.enforced or t_const.not_enforced:
            if t_const.constraint_type not in (
                TableConstraintType.CHECK,
                TableConstraintType.FOREIGN_KEY,
            ):
                raise ValueError(
                    "ENFORCED/NOT ENFORCED is only valid for CHECK and "
                    "FOREIGN KEY constraints"
                )
            if not self.supports_constraint_enforced():
                raise UnsupportedFeatureError(
                    self.name,
                    "CONSTRAINT ENFORCED" if t_const.enforced else "CONSTRAINT NOT ENFORCED",
                    f"{self.name} does not support ENFORCED constraints.",
                )
            parts.append("ENFORCED" if t_const.enforced else "NOT ENFORCED")

        return ' '.join(parts), tuple(params)

    # endregion
