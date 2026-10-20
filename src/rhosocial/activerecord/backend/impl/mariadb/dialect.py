# src/rhosocial/activerecord/backend/impl/mariadb/dialect.py
"""
MariaDB backend SQL dialect implementation.

This dialect implements protocols for features that MariaDB supports,
based on the MariaDB version provided at initialization.

MariaDB version-specific features:
- Window functions (since 10.2)
- CTE (since 10.2)
- UNION / UNION ALL (every release, measured on 10.2.44 through 13.1.1)
- INTERSECT/EXCEPT (since 10.3)
- SEQUENCE (since 10.3)
- System-versioned tables (since 10.3)
- RETURNING clause (since 10.5)
- JSON functions (since 10.2.3)
- JSON arrow operators (since 10.2.7)
- EXPLAIN FORMAT (since 10.6)
"""

from typing import Dict, Optional, Tuple, TYPE_CHECKING

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
    MariaDBLiteralValueMixin,
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
    # Ahead of SQLDialectBase, unlike every other MariaDB mixin. Those add
    # methods the base does not have, so their position is a readability
    # choice; this one overrides ``format_literal``, which the base defines,
    # and a mixin placed after the class it overrides never wins. It
    # resolves MariaDB's two tier-2 spellings -- binary ``X'...'`` and the
    # bare quoted UUID text -- and leaves the base's portable forms and the
    # literal-construction protocol to it (INTERVAL is deliberately absent:
    # mixins/literal.py records the measured refusals behind that).
    MariaDBLiteralValueMixin,
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
    #
    # Every probe in this region is answered from a live measurement, and the
    # answer is what the docstring says it measured -- not what the MariaDB
    # documentation says. The two disagree in exactly one place,
    # ``REFERENCES``, and it is recorded on
    # :meth:`supports_foreign_key_constraint` with the evidence that settles it.
    #
    # The server the numbers below come from is **13.1.1** (192.168.1.3:15694,
    # TLSv1.2) unless the docstring says otherwise; several were re-measured
    # across 10.2.44 / 10.4.34 / 10.5.29 / 12.0.2 / 12.1.2 as well and the
    # version grid is recorded where it applies.
    #
    # **Every constraint verdict this backend relies on is declared *here*.**
    # Some of the values agree with core's defaults, and the agreement is the
    # point rather than an accident: a probe that resolves to a core default
    # can be moved by a commit in another repository with no MariaDB file
    # edited. Three of these (``supports_constraint_novalidate``,
    # ``supports_alter_constraint_enforced``, ``supports_validate_constraint``)
    # were previously *undeclared* and resolved to the ``ConstraintSupport``
    # protocol stub, which core reads through ``getattr`` and treats as "no
    # answer" -- so the value could change under this backend and no MariaDB
    # test would notice. The declaration is what makes that a visible failure
    # instead of a quiet contract change; the test that enforces it is
    # ``test_declared_by_a_mariadb_class`` in this backend's suite.

    def supports_primary_key_constraint(self) -> bool:
        """Whether PRIMARY KEY constraints are supported.

        True. Measured on **13.1.1**: ``ALTER TABLE t ADD CONSTRAINT pk PRIMARY
        KEY (v)`` is accepted and rendered back by ``SHOW CREATE TABLE`` as
        ``PRIMARY KEY (`v`)``.

        Two measured details belong to the **name space**, not to this switch,
        and they are recorded on :meth:`supports_drop_constraint` because that
        is where they bite: MariaDB discards the ``CONSTRAINT pk`` symbol for a
        primary key (the rendered DDL contains no ``pk``), and a second primary
        key is refused with ``1068 (42000): Multiple primary key defined``.
        """
        return True

    def supports_unique_constraint(self) -> bool:
        """Whether UNIQUE constraints are supported.

        True. Measured on **13.1.1**: ``ALTER TABLE t ADD CONSTRAINT uq UNIQUE
        (v)`` is accepted, the symbol survives in ``SHOW CREATE TABLE`` as
        ``UNIQUE KEY `uq` (`v`)``, and ``ALTER TABLE t DROP CONSTRAINT uq``
        removes it.
        """
        return True

    def supports_not_null_constraint(self) -> bool:
        """Whether NOT NULL column constraints are supported.

        True. Measured on **13.1.1**: ``CREATE TABLE t (x INT NOT NULL)`` is
        accepted and renders ``x int(11) NOT NULL``. Trivial for the server;
        declared here so the verdict is this backend's rather than an
        inherited default that could move under it.
        """
        return True

    def supports_check_constraint(self) -> bool:
        """Whether CHECK constraints are supported **and enforced**.

        Version-gated at **10.2.1** (``MARIADB_VERSION_BOUNDARIES
        ['CHECK_CONSTRAINT']``). Measured on **13.1.1**: ``ALTER TABLE t ADD
        CONSTRAINT ck CHECK (c > 0)`` is accepted, rendered back by
        ``SHOW CREATE TABLE`` as ``CONSTRAINT `ck` CHECK (`c` > 0)``, and
        enforced -- a violating insert is refused with ``4025 (23000):
        CONSTRAINT `ck` failed for `test_db`.`t` ``. Adding it over an
        already-violating row fails with the same errno, so there is no
        "add first, validate later" path on this server (see
        :meth:`supports_constraint_novalidate` for the clause MariaDB would need
        for that and does not have).

        The errno is MariaDB's own and differs from MySQL 8's ``3819``; code
        that classifies the violation has to branch on the server.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['CHECK_CONSTRAINT']

    def supports_exclude_constraint(self) -> bool:
        """Whether EXCLUDE table constraints are supported.

        False. Measured on **13.1.1**: ``ALTER TABLE t ADD CONSTRAINT ex
        EXCLUDE (a WITH =)`` answers

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MariaDB server version for the
            right syntax to use near 'EXCLUDE (a WITH =)' at line 1

        and the PostgreSQL-shaped ``ADD EXCLUDE USING btree (a WITH =)`` fails
        differently -- ``4161 (HY000): Unknown data type: 'USING' `` -- because
        the parser reaches ``USING`` as a type name. Two errnos for one
        constraint kind is exactly why error classification cannot stand in for
        a capability answer here.

        Core reads this probe through ``getattr`` and treats ``None`` as "no
        answer", so while it was undeclared it resolved to the
        ``ConstraintSupport`` protocol stub. Declared here so the measured
        answer travels with the measurement.
        """
        return False

    def supports_foreign_key_constraint(self) -> bool:
        """Whether FOREIGN KEY constraints are supported.

        True. The table-level ``CONSTRAINT <name> FOREIGN KEY ...`` form works
        on every measured version, and so does the column-level ``REFERENCES``
        shortcut -- from **10.5** onward, which is the part the official MariaDB
        documentation gets wrong. It says the shortcut ``"does nothing"``
        (``mariadb.com/docs/server/reference/sql-statements/
        data-definition/constraint``). Measured live (192.168.1.3, TLSv1.2, one
        server per release):

        ============  =========================================================
        version        ``c INT REFERENCES r(id)``
        ============  =========================================================
        10.2.44 -      **nothing built.** No FK in ``SHOW CREATE TABLE``, no
        10.4.34        entry in ``TABLE_CONSTRAINTS``, no index, and a violating
                       row inserts fine. The documentation is *right* here.
        10.5.29 -      A real, enforced foreign key: ``KEY `c` (`c`)`` and
        12.0.2         ``CONSTRAINT <tbl>_ibfk_1 FOREIGN KEY (c) REFERENCES
                       r (id)``, violating row rejected with **errno 1452**.
        12.1.2 -      Same enforced foreign key, **but the generated name
        13.1.1        changes to a positional integer** -- ``CONSTRAINT `1```,
                       then ``CONSTRAINT `2``` for a second column. Not
                       ``<tbl>_ibfk_N``.
        ============  =========================================================

        So "does nothing" was true and stopped being true, and the plan built on
        it (answer False for the column-level form, refuse it by name) was
        withdrawn. What remains is the **name**: it is server-generated, and its
        *shape* moved at 12.1, so a caller must not depend on either spelling. A
        caller that needs a named foreign key uses the table-level form; the
        shortcut cannot name one, and on 10.2-10.4 it does not build one at all.
        Either way MariaDB auto-creates an index named after the *column*
        (``KEY `c` (`c`)``), which is what has to be dropped alongside it.

        Core's per-kind split (``supports_column_foreign_key_constraint`` /
        ``supports_table_foreign_key_constraint``) has not landed, so this single
        switch carries both answers and the version gate above is the value the
        column-level one must take when it does.
        """
        return True

    def supports_fk_on_delete(self) -> bool:
        """Whether ``ON DELETE`` referential actions are supported.

        True. Measured on **13.1.1**: all five ``reference_option`` values are
        accepted on ``ADD CONSTRAINT``, and four of the five survive in
        ``information_schema.REFERENTIAL_CONSTRAINTS.DELETE_RULE``:

        ==================================  ===========================
        written                              read back
        ==================================  ===========================
        ``ON DELETE CASCADE``                ``CASCADE``
        ``ON DELETE SET NULL``               ``SET NULL``
        ``ON DELETE RESTRICT``               ``RESTRICT``
        ``ON DELETE NO ACTION``              ``NO ACTION``
        ``ON DELETE SET DEFAULT``            ``RESTRICT``  ← silently changed
        ==================================  ===========================

        The last row is the trap: ``SET DEFAULT`` is **accepted** and stored as
        ``RESTRICT``, so a caller that writes it gets a stricter rule than it
        asked for and no error to notice it by. This is a different failure
        shape from ``MATCH`` (see :meth:`supports_fk_match`), where the clause
        vanishes; here it is replaced by a live rule.

        **And the rewrite is itself version-gated.** Measured across fifteen
        servers (10.2.44 ... 13.1.1), ``SET DEFAULT`` on 10.2.44 / 10.3.39 /
        10.4.34 is **refused** -- ``1005 (HY000): Can't create table ... (errno:
        150 "Foreign key constraint is incorrectly formed")`` -- and is the
        silent-rewrite behaviour from **10.5.29** onward. So the answer here is
        ``True`` on every version, but *why* a caller sees it change: below
        10.5 the statement fails loudly, from 10.5 it succeeds and lies.

        Independent of the MATCH verdict: these actions survive even when a
        ``MATCH`` clause is written alongside them, precisely because that
        clause is discarded (measured).
        """
        return True

    def supports_fk_on_update(self) -> bool:
        """Whether ``ON UPDATE`` referential actions are supported.

        True. Measured on **13.1.1**: ``ON UPDATE CASCADE`` is accepted and
        ``information_schema.REFERENTIAL_CONSTRAINTS.UPDATE_RULE`` reads back
        ``CASCADE``.

        The one measured interaction to know about is not with this switch but
        with CHECK: a foreign key carrying ``ON UPDATE CASCADE`` cannot be
        added to a column a CHECK constraint already covers -- **errno 1901 /
        SQLSTATE HY000**, ``Function or expression 'c' cannot be used in the
        CHECK clause of `ck` `` -- in either order (FK first, or CHECK first).

        That conflict is **itself version-gated**, measured across fifteen
        servers: 10.2.44 / 10.3.39 / 10.4.34 accept the combination and keep
        both constraints, and every server from **10.5.29** on answers 1901. So
        the same DDL is legal before 10.5 and refused after it, which is why
        the boundary -- not just the errno -- has to be on the record.

        ``ON DELETE CASCADE`` on the same column is accepted on every measured
        version, so it is ``ON UPDATE`` specifically that trips it. It is not a
        rendering decision and no formatter refuses it: the clause is rendered
        by core's ``format_table_foreign_key_constraint``, and the server is the
        one that refuses, so a caller must not put a CHECK over the same column
        as a cascading foreign key from 10.5 on.
        """
        return True

    def supports_foreign_key_on_delete(self) -> bool:
        """Whether a **column-level** ``ON DELETE`` action is supported.

        True, and the same measurement as :meth:`supports_fk_on_delete` --
        both probes gate the same server behaviour, core just consults the
        column one when rendering a column definition's REFERENCES clause and
        the table one when rendering a table-level FOREIGN KEY.

        Measured on **13.1.1**: ``CREATE TABLE c (id INT, d INT REFERENCES p
        (id) ON DELETE CASCADE)`` is accepted and
        ``REFERENTIAL_CONSTRAINTS.DELETE_RULE`` reads ``CASCADE``. The
        ``SET DEFAULT`` -> ``RESTRICT`` rewrite recorded on
        :meth:`supports_fk_on_delete` applies here too.

        Declared locally rather than inherited from core's ``DDLColumnMixin``
        (which answers True) so the measured answer is this backend's: the
        agreement is the point, not an accident.
        """
        return True

    def supports_foreign_key_on_update(self) -> bool:
        """Whether a **column-level** ``ON UPDATE`` action is supported.

        True. Same measurement as :meth:`supports_fk_on_update`: measured on
        **13.1.1**, ``CREATE TABLE c (id INT, d INT REFERENCES p (id) ON
        UPDATE CASCADE)`` is accepted and
        ``REFERENTIAL_CONSTRAINTS.UPDATE_RULE`` reads ``CASCADE``.

        Declared locally for the reason on
        :meth:`supports_foreign_key_on_delete`.
        """
        return True

    def supports_fk_match(self) -> bool:
        """Whether ``MATCH {SIMPLE|PARTIAL|FULL}`` is supported.

        False, and **for a different reason than on MySQL** -- the two
        MySQL-family servers are both measured to accept the clause and drop
        it, but they drop it differently, and a caller reading the catalog back
        sees a different answer on each.

        Measured on **MariaDB 13.1.1** (192.168.1.3:15694, TLSv1.2), and the
        same shape re-measured on 10.2.44 / 10.4.34 / 10.5.29 / 12.0.2 /
        12.1.2 -- every version accepts it::

            ALTER TABLE vm ADD CONSTRAINT mf FOREIGN KEY (c)
              REFERENCES vp (id) MATCH FULL;      -- accepted

        and then discards it. What the catalog says afterwards:

        ==================================  ==============================
        catalog read-back                    MariaDB 13.1.1
        ==================================  ==============================
        ``REFERENTIAL_CONSTRAINTS``          ``MATCH_OPTION = 'NONE'``
        ``.MATCH_OPTION``
        ``SHOW CREATE TABLE vm``             no MATCH clause
        ==================================  ==============================

        ``'NONE'`` is MariaDB's own answer and it is worth not generalizing
        from the sibling: **MySQL 26.7.0 records ``'FULL'`` in the same
        column** for the same statement (measured on the same day, against
        192.168.1.3:14686). So "was MATCH recorded" cannot be ported between
        the two servers -- MariaDB loses the token outright, MySQL keeps the
        mode and enforces nothing from it. A test that asserts
        ``MATCH_OPTION == 'NONE'`` is a MariaDB-only statement and reads as a
        bug on MySQL.

        ``MATCH SIMPLE`` and ``MATCH PARTIAL`` are accepted on the same
        footing; neither leaves a trace either.

        Rendering the clause would tell a caller MATCH is in force when nothing
        enforces it, so the spelling is refused by name instead of being
        dropped -- the refusal is the point, not a conservative reading of
        "unsupported".
        """
        return False

    def supports_deferrable_constraint(self) -> bool:
        """Whether ``DEFERRABLE`` / ``INITIALLY ...`` constraints are supported.

        False. Measured on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc, and re-measured
        on **13.1.1** plus 10.2.44 / 10.4.34 / 10.5.29 / 12.0.2 / 12.1.2: every
        spelling of the pair is **errno 1064 / SQLSTATE 42000**, with the
        server naming the offending token:

        ==================================  ===============================
        statement                             errno text
        ==================================  ===============================
        ``... FOREIGN KEY (...) DEFERRABLE``  ``near 'DEFERRABLE'``
        ``... FOREIGN KEY (...) NOT DEFERRABLE``  ``near 'NOT DEFERRABLE'``
        ``... FOREIGN KEY (...) INITIALLY DEFERRED``  ``near 'INITIALLY DEFERRED'``
        ==================================  ===============================

        MariaDB 10.6's grammar (``sql_yacc.yy``) has no ``DEFERRABLE`` or
        ``INITIALLY`` token, and the servers agree, so all three are refused by
        name rather than dropped. ``NOT VALID`` is a separate spelling with the
        same errno and lives on its own probe,
        :meth:`supports_constraint_novalidate`.
        """
        return False

    def supports_constraint_enforced(self) -> bool:
        """Whether ``[NOT] ENFORCED`` is supported.

        False. Measured on 10.2 / 10.3 / 10.6 / 11.4 / 13.1rc, and re-measured
        on **13.1.1** plus 10.2.44 / 10.4.34 / 10.5.29 / 12.0.2 / 12.1.2:
        **both** spellings are **errno 1064 / SQLSTATE 42000** on every one of
        them, naming the token -- ``near 'NOT ENFORCED'`` and ``near
        'ENFORCED'``.

        This is the clause where the MySQL family's split is most likely to be
        got wrong: **MySQL 26.7 accepts both** on the same statement shape
        (measured the same day on 192.168.1.3:14686), so a value copied across
        from MySQL would tell a MariaDB caller its ``NOT ENFORCED`` constraint
        would be stored unenforced when the server would have refused the
        statement outright. Do not copy MySQL's values here.

        The previous declaration (``version >= (10, 2, 22)``) was never
        measured; that version belongs to MySQL's clause, not MariaDB's.

        Related measurement, recorded because it is what a caller would reach
        for to work around the refusal: **MariaDB 13.1.1's
        ``information_schema.TABLE_CONSTRAINTS`` has no ``ENFORCED`` column**
        at all (its columns are ``CONSTRAINT_CATALOG``, ``CONSTRAINT_SCHEMA``,
        ``CONSTRAINT_NAME``, ``TABLE_SCHEMA``, ``TABLE_NAME``,
        ``CONSTRAINT_TYPE``). There is nothing to read back even if the
        clause were accepted, so introspection cannot answer the question this
        switch answers.
        """
        return False

    def supports_constraint_novalidate(self) -> bool:
        """Whether ``NOT VALID`` is accepted on ``ADD CONSTRAINT``.

        False. Measured on **13.1.1** plus 10.2.44 / 10.4.34 / 10.5.29 /
        12.0.2 / 12.1.2: ``ALTER TABLE ... ADD CONSTRAINT ck CHECK (c > 0) NOT
        VALID`` is **errno 1064 / SQLSTATE 42000** (``near 'NOT VALID'``) on
        every one of them.

        The clause is not merely undeclared -- it is what makes
        :meth:`supports_add_constraint`'s "add first, check later" impossible:
        adding a CHECK validates the rows already present (``4025 (23000)``),
        and without ``NOT VALID`` there is no spelling that defers that.

        It was previously *undeclared* rather than answered ``False``: core
        reads this probe through ``getattr(self,
        "supports_constraint_novalidate", None)`` and treats ``None`` as "no
        answer", so it resolved to the ``ConstraintSupport`` protocol stub.
        Declared here so the measured answer travels with the measurement.
        """
        return False

    def supports_alter_constraint_enforced(self) -> bool:
        """Whether ``ALTER CONSTRAINT ... [NOT] ENFORCED`` is supported.

        False. Measured on **13.1.1**: ``ALTER TABLE t ALTER CONSTRAINT ck NOT
        ENFORCED`` and ``ALTER TABLE t ALTER CONSTRAINT ck DEFERRABLE`` are both
        **errno 1064 / SQLSTATE 42000**, naming the whole tail --
        ``near 'CONSTRAINT ck NOT ENFORCED'`` and ``near 'CONSTRAINT ck
        DEFERRABLE'``. The same errno and the same shape of message covers
        ``RENAME CONSTRAINT`` (``near 'CONSTRAINT ck TO ck_new'``), ``VALIDATE
        CONSTRAINT`` / ``ENABLE CONSTRAINT`` / ``DISABLE CONSTRAINT`` /
        ``NOCHECK CONSTRAINT`` / ``CHECK CONSTRAINT`` (all ``near 'CONSTRAINT
        ck'``) and ``DROP CHECK`` (``near 'CHECK ck'``), so **MariaDB's ALTER
        TABLE grammar carries no constraint lifecycle clause beyond ADD and
        DROP**. The full measured list is recorded on
        :class:`rhosocial.activerecord.backend.impl.mariadb.mixins.ddl.constraint.MariaDBAlterConstraintModifierMixin`.

        MySQL accepts both ``[NOT] ENFORCED`` spellings here; MariaDB accepts
        neither. The verdict is stated for this server alone.

        **No parameter.** A probe answers one question -- "is this capability
        family present on this server" -- and the kind is not part of it. This
        one used to take an ignored ``constraint_type``; keeping the parameter
        would have kept two call shapes alive for an answer that is the same
        for every kind. The kind, where one exists, is decided by the branch
        class in :meth:`format_alter_constraint_action`.
        """
        return False

    def supports_constraint_naming(self) -> bool:
        """Whether a constraint may carry a ``CONSTRAINT <name>`` prefix.

        True, and the answer is *level-dependent*, which is why the boolean
        answers the family and the column level narrows it.

        Measured on **13.1.1** (192.168.1.3:15694, TLSv1.2):

        * **Table level: every kind.** ``ALTER TABLE t ADD CONSTRAINT uq UNIQUE
          (v)`` is accepted and the symbol survives as ``UNIQUE KEY `uq```;
          ``ADD CONSTRAINT ck CHECK (c > 0)`` and ``ADD CONSTRAINT fk FOREIGN
          KEY (c) REFERENCES p (id)`` likewise. ``CREATE TABLE t (u INT,
          CONSTRAINT uq_u UNIQUE (u))`` renders ``UNIQUE KEY `uq_u```.
        * **Column level: the foreign key only.** ``p INT CONSTRAINT fk_p
          REFERENCES parent (id)`` is accepted and renders ``CONSTRAINT `fk_p`
          FOREIGN KEY (`p`) REFERENCES `parent` (`id`)``. Every other
          column-level kind answers **errno 1064 / SQLSTATE 42000**, in either
          position: ``CONSTRAINT`` before or after ``UNIQUE``,
          ``UNIQUE KEY``, ``PRIMARY KEY`` and ``CHECK`` are all syntax errors.

        The narrowing is therefore a formatter decision, not a probe decision:
        :meth:`MariaDBTableMixin.format_column_constraint` refuses a name on any
        column branch that is not :class:`ColumnForeignKeyConstraint`. Reporting
        ``False`` here instead would be wrong in the other direction -- it would
        refuse the table-level name that is the whole point of the switch.
        """
        return True

    def supports_validate_constraint(self) -> bool:
        """Whether ``VALIDATE CONSTRAINT name`` is supported.

        False. Measured on **13.1.1**: ``ALTER TABLE t VALIDATE CONSTRAINT ck``
        is **errno 1064 / SQLSTATE 42000**, ``near 'CONSTRAINT ck'``. The same
        message answers ``ENABLE CONSTRAINT`` / ``DISABLE CONSTRAINT`` /
        ``NOCHECK CONSTRAINT`` / ``CHECK CONSTRAINT`` on the same server, so
        the parser rejects the bare token before it can decide what to do with
        it -- which is why those four cannot be told apart by errno and have to
        be answered one switch at a time.

        This is a genuine gap rather than an alternative spelling: because
        ``ADD CONSTRAINT`` validates immediately (see
        :meth:`supports_add_constraint`) and there is no ``NOT VALID`` and no
        ``VALIDATE``, a constraint that cannot be validated on add cannot be
        validated afterwards either. There is no deferred-validation workflow
        on this server.

        Core reads this probe through ``getattr`` too, so it answered ``None``
        from the protocol stub until this declaration.
        """
        return False

    def supports_column_character_set(self) -> bool:
        """Whether a column-level ``CHARACTER SET <name>`` attribute is supported.

        True. Measured on **13.1.1**: ``CREATE TABLE t (e VARCHAR(10)
        CHARACTER SET utf8mb3)`` is accepted and honoured --
        ``information_schema.COLUMNS.CHARACTER_SET_NAME`` reads ``utf8mb3`` for
        that column only and ``SHOW CREATE TABLE`` echoes ``CHARACTER SET
        utf8mb3 COLLATE utf8mb3_uca1400_ai_ci`` on it.

        This was a **wrong** inherited value, not merely an inherited one:
        core's ``DDLColumnMixin`` answers ``False``, while this backend's own
        :meth:`MariaDBTableMixin.format_column_definition` renders the
        attribute (``CHARACTER SET `utf8mb4```), so the switch had been
        answering the opposite of what this dialect's own formatter does.
        """
        return True

    def supports_column_collation(self) -> bool:
        """Whether a column-level ``COLLATE <name>`` attribute is supported.

        True. Measured on **13.1.1**: ``CREATE TABLE t (c VARCHAR(10) COLLATE
        utf8mb4_bin)`` is accepted and echoed by ``SHOW CREATE TABLE`` as
        ``CHARACTER SET utf8mb4 COLLATE utf8mb4_bin``. Core already defaults
        this to True; it is declared here so the measured answer is MariaDB's
        own rather than an inherited default that may change under it.

        The two attributes are not independent on the server: a ``COLLATE``
        naming a collation of the wrong character set is refused with
        **errno 1253 / SQLSTATE 42000**, ``COLLATION 'utf8mb4_bin' is not
        valid for CHARACTER SET 'utf8mb3' ``. Declaring both switches True
        therefore does not mean any pairing renders.
        """
        return True

    def supports_add_constraint(self) -> bool:
        """Whether ``ALTER TABLE ADD CONSTRAINT`` is supported.

        True for all four kinds MariaDB has. Measured on **13.1.1**, each of
        these is accepted and rendered back by ``SHOW CREATE TABLE``:
        ``ADD CONSTRAINT uq UNIQUE (v)``, ``ADD CONSTRAINT ck CHECK (c > 0)``,
        ``ADD CONSTRAINT fk FOREIGN KEY (c) REFERENCES p (id) ON DELETE
        CASCADE``, and ``ADD CONSTRAINT pk PRIMARY KEY (v)`` on a table that
        has no primary key yet.

        Adding validates the rows already present: a CHECK over a violating
        row fails with ``4025 (23000)`` and a FOREIGN KEY over a dangling row
        with ``1452 (23000)``. There is therefore no "add first, check later"
        spelling on this server, which is why
        :meth:`supports_constraint_novalidate` is ``False`` rather than
        unused.

        Adding does **not** work for EXCLUDE (``1064``, see
        :meth:`supports_exclude_constraint`) and the clause-level attributes
        are refused rather than dropped -- see
        :meth:`supports_deferrable_constraint`,
        :meth:`supports_constraint_enforced`, :meth:`supports_fk_match`.
        """
        return True

    def supports_drop_constraint(self) -> bool:
        """Whether ``ALTER TABLE DROP CONSTRAINT`` is supported.

        True, but the **name space** is narrower than it looks, and this is
        the one place where MariaDB and MySQL differ in the opposite
        direction from ``IF EXISTS``.

        Measured on **13.1.1**:

        * ``DROP CONSTRAINT uq`` (UNIQUE), ``DROP CONSTRAINT fk`` (FOREIGN
          KEY), ``DROP CONSTRAINT ck`` (CHECK) all work.
        * A constraint that does not exist answers **``1091 (42000): Can't
          DROP CONSTRAINT `nope`; check that it exists``** -- a real errno, so
          unlike MySQL (whose ``DROP CONSTRAINT`` failure is ``3940``) the
          absent case is catchable. ``DROP CONSTRAINT IF EXISTS`` makes it
          unnecessary -- see
          :class:`rhosocial.activerecord.backend.impl.mariadb.mixins.ddl.constraint.MariaDBAlterConstraintModifierMixin`.
        * A **primary key symbol is not in the name space.** ``ADD CONSTRAINT
          pk_x PRIMARY KEY (v)`` succeeds but the symbol is discarded -- the
          rendered DDL says only ``PRIMARY KEY (`v`)`` -- and ``DROP
          CONSTRAINT pk_x`` then answers ``1091``. The working spelling is
          ``ALTER TABLE t DROP PRIMARY KEY`` (measured: it removes the key).
          The literal name ``PRIMARY`` *is* accepted by ``DROP CONSTRAINT``
          and does drop the key.
        * The positional name a column-level ``REFERENCES`` generates (``1``,
          ``2``, ...) **is** droppable: ``DROP CONSTRAINT `1``` removes the
          foreign key and leaves the auto-created ``KEY `c` (`c`)`` behind --
          the index is dropped by name separately.

        So ``supports_drop_constraint() is True`` does not mean "any named
        constraint can be dropped": a primary key needs a different statement,
        and that is a per-kind gap one boolean cannot express.
        """
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

    def format_begin_transaction_statement(self, expr) -> Tuple[str, tuple]:
        """Format BEGIN TRANSACTION statement for MariaDB.

        ``DEFERRABLE`` / ``NOT DEFERRABLE`` is consumed through the transaction
        probe: MariaDB answers ``supports_deferrable_transaction()`` False, so
        an explicit spelling is refused by name rather than dropped; a subclass
        that declares the probe True renders the spelling it declared.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        set_isolation = ""
        if expr.isolation_level is not None:
            level_map = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
            }
            level_name = level_map.get(expr.isolation_level)
            if level_name:
                set_isolation = f"SET TRANSACTION ISOLATION LEVEL {level_name}; "

        if expr.mode == TransactionMode.READ_ONLY:
            begin_sql = "START TRANSACTION READ ONLY"
        elif expr.mode == TransactionMode.READ_WRITE:
            begin_sql = "START TRANSACTION READ WRITE"
        else:
            begin_sql = "START TRANSACTION"

        if expr.deferrable or expr.not_deferrable:
            if not self.supports_deferrable_transaction():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRANSACTION DEFERRABLE"
                    if expr.deferrable
                    else "TRANSACTION NOT DEFERRABLE",
                    f"{self.name} does not support DEFERRABLE transactions.",
                )
            begin_sql += " DEFERRABLE" if expr.deferrable else " NOT DEFERRABLE"

        if expr.wait or expr.no_wait:
            if not self.supports_transaction_wait():
                spelling = "WAIT" if expr.wait else "NO WAIT"
                raise UnsupportedFeatureError(
                    self.name,
                    f"TRANSACTION {spelling}",
                    f"{self.name} does not support the {spelling} transaction clause.",
                )
            begin_sql += " WAIT" if expr.wait else " NO WAIT"

        return f"{set_isolation}{begin_sql}", ()

    def format_set_transaction(self, expr) -> Tuple[str, tuple]:
        """Format SET TRANSACTION statement for MariaDB.

        ``DEFERRABLE`` / ``NOT DEFERRABLE`` is consumed through the transaction
        probe, exactly as in :meth:`format_begin_transaction_statement`.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        parts = ["SET TRANSACTION"]

        if expr.isolation_level is not None:
            level_map = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
            }
            level_name = level_map.get(expr.isolation_level)
            if level_name:
                parts.append(f"ISOLATION LEVEL {level_name}")

        if expr.mode is not None:
            if expr.mode == TransactionMode.READ_ONLY:
                parts.append("READ ONLY")
            elif expr.mode == TransactionMode.READ_WRITE:
                parts.append("READ WRITE")

        if expr.deferrable or expr.not_deferrable:
            if not self.supports_deferrable_transaction():
                raise UnsupportedFeatureError(
                    self.name,
                    "TRANSACTION DEFERRABLE"
                    if expr.deferrable
                    else "TRANSACTION NOT DEFERRABLE",
                    f"{self.name} does not support DEFERRABLE transactions.",
                )
            parts.append("DEFERRABLE" if expr.deferrable else "NOT DEFERRABLE")

        if expr.wait or expr.no_wait:
            if not self.supports_transaction_wait():
                spelling = "WAIT" if expr.wait else "NO WAIT"
                raise UnsupportedFeatureError(
                    self.name,
                    f"TRANSACTION {spelling}",
                    f"{self.name} does not support the {spelling} transaction clause.",
                )
            parts.append("WAIT" if expr.wait else "NO WAIT")

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

    # endregion
