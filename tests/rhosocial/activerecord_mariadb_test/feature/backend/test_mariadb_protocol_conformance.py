# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_protocol_conformance.py
"""
Tests to verify MariaDBDialect protocol conformance and protocol non-overlap.

This test ensures:
1. MariaDBDialect implements all methods defined in the protocols it claims to support
2. All protocols have at least one member
3. No two protocols share the same method name (no overlap)
"""
import inspect
import sys
from itertools import combinations

if sys.version_info >= (3, 13):
    from typing import get_protocol_members
elif sys.version_info >= (3, 12):
    from typing import _get_protocol_attrs as get_protocol_members

import pytest
from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.impl.mariadb import dialect as mariadb_dialect
from rhosocial.activerecord.backend.impl.mariadb import mixins as mysql_mixins
from rhosocial.activerecord.backend.impl.mariadb import protocols as mariadb_protocols
from rhosocial.activerecord.backend.impl.mariadb import protocols as mysql_protocols
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.protocols import types as mariadb_protocol_types


def get_all_protocol_methods(proto: type) -> set:
    """Extract all public method names from a protocol, including inherited."""
    members = set()
    if sys.version_info >= (3, 13):
        members = get_protocol_members(proto)
    elif sys.version_info >= (3, 12):
        members = get_protocol_members(proto)
    else:
        # Walk MRO to include methods from parent protocols
        for cls in proto.__mro__:
            if cls is object:
                continue
            for name in cls.__dict__:
                if name.startswith("_"):
                    continue
                val = cls.__dict__[name]
                if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
                    members.add(name)
            members.update(
                k for k in getattr(cls, "__annotations__", {})
                if not k.startswith("_")
            )
    return members


def get_own_protocol_methods(proto: type) -> set:
    """Extract public method names declared directly on a protocol (not inherited).

    Used for forward coverage: only checks methods the protocol itself declares,
    since parent protocol methods are typically implemented by generic mixins.
    """
    members = set()
    for name in proto.__dict__:
        if name.startswith("_"):
            continue
        val = proto.__dict__[name]
        if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
            members.add(name)
    members.update(
        k for k in getattr(proto, "__annotations__", {})
        if not k.startswith("_")
    )
    return members


MYSQL_PROTOCOLS = [
    # --- Named objects: how each kind of catalogue entry is spelled ---
    dialect_protocols.NamespaceSupport,
    dialect_protocols.TableObjectSupport,
    dialect_protocols.ViewObjectSupport,
    dialect_protocols.MaterializedViewObjectSupport,
    dialect_protocols.ForeignTableObjectSupport,
    dialect_protocols.IndexObjectSupport,
    dialect_protocols.SequenceObjectSupport,
    dialect_protocols.TriggerObjectSupport,
    dialect_protocols.RoutineObjectSupport,
    dialect_protocols.TypeObjectSupport,
    dialect_protocols.SynonymObjectSupport,
    # --- Query features ---
    dialect_protocols.AdvancedGroupingSupport,
    dialect_protocols.ArraySupport,
    dialect_protocols.CTESupport,
    dialect_protocols.CollationSupport,
    dialect_protocols.ColumnAttributeSupport,
    dialect_protocols.ColumnTypeSupport,
    dialect_protocols.DataTypeSupport,
    dialect_protocols.DateTimeSupport,
    dialect_protocols.DqlOrderSupport,
    dialect_protocols.ExplainSupport,
    dialect_protocols.FilterClauseSupport,
    dialect_protocols.FulltextIndexSupport,
    dialect_protocols.GeneratedColumnSupport,
    dialect_protocols.GraphSupport,
    dialect_protocols.ILIKESupport,
    dialect_protocols.JSONSupport,
    dialect_protocols.JoinSupport,
    dialect_protocols.LateralJoinSupport,
    dialect_protocols.LockingSupport,
    dialect_protocols.MaterializedViewSupport,
    dialect_protocols.MergeSupport,
    dialect_protocols.OrderedSetAggregationSupport,
    dialect_protocols.PartitionSupport,
    dialect_protocols.QualifyClauseSupport,
    dialect_protocols.ReturningSupport,
    dialect_protocols.SetOperationSupport,
    dialect_protocols.SQLFunctionSupport,
    dialect_protocols.TemporalTableSupport,
    dialect_protocols.UpsertSupport,
    dialect_protocols.WildcardSupport,
    dialect_protocols.WindowFunctionSupport,
    # --- DDL, one protocol per statement ---
    dialect_protocols.AlterDatabaseSupport,
    dialect_protocols.AlterDomainSupport,
    dialect_protocols.AlterSequenceSupport,
    dialect_protocols.AlterTableModifierSupport,
    dialect_protocols.AlterTableSupport,
    dialect_protocols.AlterTypeSupport,
    # One protocol per mechanism: the parameterless marker and the
    # parameterised standard clause. MariaDB declares both interfaces; its
    # probes answer True and False respectively.
    dialect_protocols.AutoIncrementColumnSupport,
    dialect_protocols.IdentityColumnSupport,
    dialect_protocols.ConstraintSupport,
    dialect_protocols.CreateDomainSupport,
    dialect_protocols.CreateIndexSupport,
    dialect_protocols.CreateRoutineSupport,
    dialect_protocols.CreateSchemaSupport,
    dialect_protocols.CreateSequenceSupport,
    dialect_protocols.CreateTableAsSupport,
    dialect_protocols.CreateTableCloneSupport,
    dialect_protocols.CreateTableLikeSupport,
    dialect_protocols.CreateTableSupport,
    dialect_protocols.CreateTableUsingTemplateSupport,
    dialect_protocols.CreateTriggerSupport,
    dialect_protocols.CreateTypeSupport,
    dialect_protocols.CreateViewSupport,
    dialect_protocols.DropDomainSupport,
    dialect_protocols.DropIndexSupport,
    dialect_protocols.DropRoutineSupport,
    dialect_protocols.DropSchemaSupport,
    dialect_protocols.DropSequenceSupport,
    dialect_protocols.DropTableSupport,
    dialect_protocols.DropTriggerSupport,
    dialect_protocols.DropTypeSupport,
    dialect_protocols.DropViewSupport,
    dialect_protocols.TruncateSupport,
    # --- Introspection and sessions ---
    dialect_protocols.IntrospectionSupport,
    dialect_protocols.TransactionControlSupport,
    # --- MariaDB-specific protocols ---
    mysql_protocols.MariaDBAdminSupport,
    mysql_protocols.MariaDBAlterTableSupport,
    mysql_protocols.MariaDBCTESupport,
    mysql_protocols.MariaDBCharsetCollationSupport,
    mysql_protocols.MariaDBDMLOperationSupport,
    mysql_protocols.MariaDBFullTextSearchSupport,
    mysql_protocols.MariaDBIntersectExceptSupport,
    mysql_protocols.MariaDBJSONFunctionSupport,
    mysql_protocols.MariaDBLockingSupport,
    mysql_protocols.MariaDBMaintenanceSupport,
    mysql_protocols.MariaDBModifyColumnSupport,
    mysql_protocols.MariaDBPartitionSupport,
    mysql_protocols.MariaDBRenameTableSupport,
    mysql_protocols.MariaDBReturningSupport,
    mysql_protocols.MariaDBRoutineSupport,
    mysql_protocols.MariaDBSequenceSupport,
    mysql_protocols.MariaDBSetTypeSupport,
    mysql_protocols.MariaDBSpatialSupport,
    mysql_protocols.MariaDBSystemVersioningSupport,
    mysql_protocols.MariaDBTableSupport,
    mysql_protocols.MariaDBTriggerSupport,
    mysql_protocols.MariaDBWindowFunctionSupport,
    # MariaDB's own data-type attributes. This one was declared and never
    # composed, which made all nine of its capability members unreachable.
    mysql_protocols.MariaDBTypeSupport,
]


class TestMariaDBDialectProtocolConformance:
    """Assert MariaDBDialect implements all protocols it declares to support."""

    @pytest.fixture
    def dialect(self):
        """Create a MariaDBDialect instance for testing."""
        return mariadb_dialect.MariaDBDialect()

    @pytest.mark.parametrize("protocol", MYSQL_PROTOCOLS)
    def test_implements_protocol(self, dialect, protocol):
        """MariaDBDialect should implement each protocol in MYSQL_PROTOCOLS."""
        assert isinstance(dialect, protocol), (
            f"MariaDBDialect does not implement protocol {protocol.__name__}, "
            f"missing methods: {get_all_protocol_methods(protocol) - set(dir(dialect))}"
        )


# Generic protocols MariaDBDialect intentionally does NOT implement.
#
# Listing them makes the omission a deliberate, tested contract: if MariaDB ever
# satisfies one by accident, the negative test fails and forces a conscious
# decision (move to MYSQL_PROTOCOLS or revert).
MARIADB_NOT_IMPLEMENTED = [
    # UUID value expressions (generation / nil-max constants / cast) are not
    # implemented yet on this dialect. Listed here so the omission is a
    # recorded decision rather than a gap; move it to the implemented list
    # when the mixin lands.
    dialect_protocols.UUIDSupport,
    # --- Intentional non-support ---
    # MariaDB has no standalone COMMENT ON statement; inline table/column
    # comments are rendered by CREATE TABLE instead.
    dialect_protocols.CommentSupport,
    # MariaDB has no SQL/PGQ property-graph tables.
    dialect_protocols.GraphTableSupport,
    # MariaDB has no PIVOT / UNPIVOT.
    dialect_protocols.PivotSupport,
    # MariaDB has no SQL/XML support.
    dialect_protocols.SQLXMLSupport,
    dialect_protocols.SQLXMLParsingSupport,
    dialect_protocols.SQLXMLSerializationSupport,
    dialect_protocols.SQLXMLConstructionSupport,
    dialect_protocols.SQLXMLAggregationSupport,
    dialect_protocols.SQLXMLQueryingSupport,
    # CREATE/DROP DATABASE are answered by MariaDBDatabaseMixin, which declares
    # the MariaDB-only capabilities (OR REPLACE, encoding, collation) rather
    # than core's full set (owner, tablespace, template, connection limit).
    # MariaDB has none of those, so declaring the generic protocol would be a
    # claim the dialect cannot keep.
    dialect_protocols.CreateDatabaseSupport,
    dialect_protocols.DropDatabaseSupport,
]


def get_all_generic_protocols() -> dict:
    """Discover every generic dialect protocol defined in protocols.py."""
    from typing import Protocol

    discovered = {}
    for name, obj in inspect.getmembers(dialect_protocols, inspect.isclass):
        if Protocol not in getattr(obj, "__mro__", []) or not name.endswith("Support"):
            continue
        if name == "DDLTypeSupport":
            assert obj is dialect_protocols.DataTypeSupport
            continue
        assert name == obj.__name__, f"unexpected protocol alias: {name}"
        discovered[name] = obj
    return discovered


class TestMariaDBDialectNegativeProtocolConformance:
    """Assert MariaDBDialect does not implement intentionally-unsupported protocols."""

    @pytest.fixture
    def dialect(self):
        return mariadb_dialect.MariaDBDialect()

    @pytest.mark.parametrize("protocol", MARIADB_NOT_IMPLEMENTED)
    def test_does_not_implement_protocol(self, dialect, protocol):
        """MariaDBDialect must NOT implement any protocol in MARIADB_NOT_IMPLEMENTED."""
        assert not isinstance(dialect, protocol), (
            f"MariaDBDialect unexpectedly implements {protocol.__name__}. "
            f"If intentional, move it from MARIADB_NOT_IMPLEMENTED to MYSQL_PROTOCOLS "
            f"(and implement the behaviour fully)."
        )

    def test_positive_and_negative_lists_partition_all_protocols(self):
        """Every generic protocol must be classified for MariaDB."""
        all_protos = get_all_generic_protocols()
        # Match on the class rather than on ``__module__``: core now gives each
        # protocol its own module under ``protocols/``, so every one of them
        # reports a ``__module__`` that differs from the package's.
        positive = {
            p.__name__ for p in MYSQL_PROTOCOLS
            if all_protos.get(p.__name__) is p
        }
        negative = {p.__name__ for p in MARIADB_NOT_IMPLEMENTED}

        overlap = positive & negative
        assert not overlap, f"Protocols in BOTH lists: {sorted(overlap)}"

        unclassified = set(all_protos) - positive - negative
        assert not unclassified, (
            f"Generic protocols not classified for MariaDB: {sorted(unclassified)}. "
            f"Add each to MYSQL_PROTOCOLS or MARIADB_NOT_IMPLEMENTED."
        )


class TestProtocolNonOverlap:
    """Assert protocols do not have overlapping method names."""

    def test_no_interface_overlap_between_protocols(self):
        """No two protocols should share the same method name.

        One shared group is not an overlap: every named-object protocol
        inherits the namespace switches from ``NamespaceSupport``, because
        catalog, schema and name are one question about every kind of object.
        Core says so once, on the base, and the per-kind protocols inherit it;
        enumerating those pairs here would be noise, so a pair whose shared
        members are all namespace switches passes.
        """
        member_map = {
            proto.__name__: get_all_protocol_methods(proto)
            for proto in MYSQL_PROTOCOLS
        }

        for name, members in member_map.items():
            assert len(members) > 0, f"Protocol {name} has no members defined"

        excluded_overlaps = {
            # MariaDB-specific protocols extend generic protocols, so they
            # inherit the base's methods as well as declaring their own.
            ('JSONSupport', 'MariaDBJSONFunctionSupport'),
            ('MariaDBJSONFunctionSupport', 'JSONSupport'),
            ('LockingSupport', 'MariaDBLockingSupport'),
            ('MariaDBLockingSupport', 'LockingSupport'),
            ('PartitionSupport', 'MariaDBPartitionSupport'),
            ('MariaDBPartitionSupport', 'PartitionSupport'),
            ('TableObjectSupport', 'MariaDBTableSupport'),
            ('MariaDBTableSupport', 'TableObjectSupport'),
            ('TriggerObjectSupport', 'MariaDBTriggerSupport'),
            ('MariaDBTriggerSupport', 'TriggerObjectSupport'),
            # MySQL DML includes upsert capabilities (ON DUPLICATE KEY UPDATE)
            ('UpsertSupport', 'MariaDBDMLOperationSupport'),
            ('MariaDBDMLOperationSupport', 'UpsertSupport'),
            # MySQL fulltext search restates the generic fulltext capabilities
            ('FulltextIndexSupport', 'MariaDBFullTextSearchSupport'),
            ('MariaDBFullTextSearchSupport', 'FulltextIndexSupport'),
            # MariaDB's CTE protocol restates the recursive-CTE switch.
            ('CTESupport', 'MariaDBCTESupport'),
            ('MariaDBCTESupport', 'CTESupport'),
            # MariaDB's INTERSECT/EXCEPT protocol restates two set-operation switches.
            ('SetOperationSupport', 'MariaDBIntersectExceptSupport'),
            ('MariaDBIntersectExceptSupport', 'SetOperationSupport'),
            # MariaDB's window protocol restates the window-functions switch.
            ('WindowFunctionSupport', 'MariaDBWindowFunctionSupport'),
            ('MariaDBWindowFunctionSupport', 'WindowFunctionSupport'),
            # MariaDB's RETURNING protocol restates the clause renderer.
            ('ReturningSupport', 'MariaDBReturningSupport'),
            ('MariaDBReturningSupport', 'ReturningSupport'),
            # Rename table shares capability detection with ALTER TABLE
            ('AlterTableSupport', 'MariaDBRenameTableSupport'),
            ('MariaDBRenameTableSupport', 'AlterTableSupport'),
            # ... and with the MariaDB-specific table protocol
            ('MariaDBTableSupport', 'MariaDBRenameTableSupport'),
            ('MariaDBRenameTableSupport', 'MariaDBTableSupport'),
            # MariaDB's table protocol restates CREATE TABLE and
            # CREATE TABLE ... LIKE, which core now declares separately.
            ('CreateTableSupport', 'MariaDBTableSupport'),
            ('MariaDBTableSupport', 'CreateTableSupport'),
            ('CreateTableLikeSupport', 'MariaDBTableSupport'),
            ('MariaDBTableSupport', 'CreateTableLikeSupport'),
            # ... and the column-comment switch, which core declares on
            # ConstraintSupport.
            ('ConstraintSupport', 'MariaDBTableSupport'),
            ('MariaDBTableSupport', 'ConstraintSupport'),
            # MariaDB's trigger protocol restates the whole CREATE/DROP
            # TRIGGER surface core declares per statement.
            ('CreateTriggerSupport', 'MariaDBTriggerSupport'),
            ('MariaDBTriggerSupport', 'CreateTriggerSupport'),
            ('DropTriggerSupport', 'MariaDBTriggerSupport'),
            ('MariaDBTriggerSupport', 'DropTriggerSupport'),
            # MariaDB's sequence protocol restates the CREATE/ALTER/DROP
            # SEQUENCE surface core declares per statement, including the
            # per-option probes.
            ('CreateSequenceSupport', 'MariaDBSequenceSupport'),
            ('MariaDBSequenceSupport', 'CreateSequenceSupport'),
            ('DropSequenceSupport', 'MariaDBSequenceSupport'),
            ('MariaDBSequenceSupport', 'DropSequenceSupport'),
            ('AlterSequenceSupport', 'MariaDBSequenceSupport'),
            ('MariaDBSequenceSupport', 'AlterSequenceSupport'),
            # MariaDB's routine protocol restates the CREATE/DROP FUNCTION
            # surface core declares per statement.
            ('CreateRoutineSupport', 'MariaDBRoutineSupport'),
            ('MariaDBRoutineSupport', 'CreateRoutineSupport'),
            ('DropRoutineSupport', 'MariaDBRoutineSupport'),
            ('MariaDBRoutineSupport', 'DropRoutineSupport'),
        }

        namespace_members = get_all_protocol_methods(dialect_protocols.NamespaceSupport)

        violations = []
        for (name_a, members_a), (name_b, members_b) in combinations(member_map.items(), 2):
            overlap = members_a & members_b
            if not overlap:
                continue
            if (name_a, name_b) in excluded_overlaps:
                continue
            # The namespace switches are shared by design, by inheritance.
            if overlap <= namespace_members:
                continue
            violations.append(f"{name_a} ∩ {name_b} = {overlap}")

        assert not violations, (
            "The following protocols have overlapping interfaces, need to merge or rename:\n"
            + "\n".join(f"  • {v}" for v in violations)
        )


class TestMySQLProtocolDerivation:
    """Verify MariaDB-specific protocols derive from their generic counterparts.

    This ensures that backend-specific protocols inherit the standard interface,
    allowing isinstance() checks against generic protocols to work correctly.
    """

    PROTOCOL_DERIVATIONS = [
        ("MariaDBLockingSupport", "LockingSupport"),
    ]

    @pytest.mark.parametrize("mysql_name,generic_name", PROTOCOL_DERIVATIONS)
    def test_protocol_derives_from_generic(self, mysql_name, generic_name):
        """Backend-specific protocol should derive from its generic counterpart."""
        mysql_proto = getattr(mysql_protocols, mysql_name)
        generic_proto = getattr(dialect_protocols, generic_name)
        assert issubclass(mysql_proto, generic_proto), (
            f"{mysql_name} does not derive from {generic_name}"
        )

    def test_dialect_satisfies_generic_protocols_via_derivation(self):
        """MariaDBDialect should satisfy generic protocols through derived protocols."""
        dialect = mariadb_dialect.MariaDBDialect()
        for mysql_name, generic_name in self.PROTOCOL_DERIVATIONS:
            generic_proto = getattr(dialect_protocols, generic_name)
            if getattr(generic_proto, "_is_runtime_protocol", False):
                assert isinstance(dialect, generic_proto), (
                    f"MariaDBDialect does not satisfy {generic_name} "
                    f"(should be inherited via {mysql_name})"
                )


class TestMySQLExpressionDialectSeparation:
    """Verify MariaDB-specific expression classes delegate to dialect for SQL generation.

    Expression-Dialect separation means expression classes collect parameters
    and delegate to_sql() to dialect.format_*() methods, never directly
    constructing SQL strings.
    """

    EXPRESSION_DIALECT_PAIRS = [
        ("MariaDBLoadDataExpression", "format_load_data_statement"),
        ("MariaDBJSONTableExpression", "format_json_table_expression"),
        ("MariaDBJSONExtractExpression", "format_json_extract"),
        ("MariaDBJSONObjectExpression", "format_json_object"),
        ("MariaDBJSONArrayExpression", "format_json_array"),
        ("MariaDBJSONContainsExpression", "format_json_contains"),
        ("MariaDBSTGeomFromTextExpression", "format_st_geom_from_text"),
        ("MariaDBSTDistanceExpression", "format_st_distance"),
        ("MariaDBSTWithinExpression", "format_st_within"),
        ("MariaDBSTContainsExpression", "format_st_contains"),
        ("MariaDBMatchAgainstExpression", "format_match_against"),
    ]

    @pytest.mark.parametrize("expr_name,format_method", EXPRESSION_DIALECT_PAIRS)
    def test_expression_delegates_to_dialect(self, expr_name, format_method):
        """Expression.to_sql() should delegate to dialect.format_*() method."""
        from rhosocial.activerecord.backend.impl.mariadb import expression as mysql_expr

        # Find the expression class
        expr_class = None
        for module_name in dir(mysql_expr):
            module = getattr(mysql_expr, module_name)
            if hasattr(module, expr_name):
                expr_class = getattr(module, expr_name)
                break

        # Also check top-level imports
        if expr_class is None:
            expr_class = getattr(mysql_expr, expr_name, None)

        assert expr_class is not None, f"Expression class {expr_name} not found"

        # Verify the dialect has the corresponding format method
        dialect = mariadb_dialect.MariaDBDialect()
        assert hasattr(dialect, format_method), (
            f"MariaDBDialect missing format method {format_method} "
            f"for expression {expr_name}"
        )


# ============================================================================
# Phase -1: Protocol Implementation Completeness Tests
# ============================================================================

# Map from MariaDB-specific Protocol → corresponding Mixin class
MYSQL_PROTOCOL_MIXIN_PAIRS = [
    (mysql_protocols.MariaDBDMLOperationSupport, mysql_mixins.MariaDBDMLOperationMixin),
    (mysql_protocols.MariaDBTriggerSupport, mysql_mixins.MariaDBTriggerMixin),
    (mysql_protocols.MariaDBTableSupport, mysql_mixins.MariaDBTableMixin),
    (mysql_protocols.MariaDBSetTypeSupport, mysql_mixins.MariaDBSetTypeMixin),
    (mysql_protocols.MariaDBJSONFunctionSupport, mysql_mixins.MariaDBJSONMixin),
    (mysql_protocols.MariaDBSpatialSupport, mysql_mixins.MariaDBSpatialMixin),
    (mysql_protocols.MariaDBFullTextSearchSupport, mysql_mixins.MariaDBFullTextSearchMixin),
    (mysql_protocols.MariaDBLockingSupport, mysql_mixins.MariaDBLockingMixin),
    (mysql_protocols.MariaDBModifyColumnSupport, mysql_mixins.MariaDBModifyColumnMixin),
    (mysql_protocols.MariaDBSequenceSupport, mysql_mixins.MariaDBSequenceMixin),
]


class TestProtocolMethodSignatureConformance:
    """Verify MariaDBDialect method signatures match Protocol declarations.

    Python's @runtime_checkable Protocol only checks method existence,
    not signature compatibility. This test catches parameter mismatches.
    """

    @pytest.fixture
    def dialect(self):
        """Create a MariaDBDialect instance for testing."""
        return mariadb_dialect.MariaDBDialect()

    # Known signature mismatches between MySQL dialect and generic protocols.
    # MySQL uses **kwargs or different parameter names for some methods.
    # These are pre-existing issues that require a broader refactoring to fix.
    _SIGNATURE_MISMATCH_EXCLUSIONS = {
        # JSONSupport: MySQL uses expr-based signatures instead of named params
        ('JSONSupport', 'format_json_expression'),
        ('JSONSupport', 'format_json_table_expression'),
        # MariaDBJSONFunctionSupport inherits from JSONSupport, same signature issues
        ('MariaDBJSONFunctionSupport', 'format_json_expression'),
        ('MariaDBJSONFunctionSupport', 'format_json_table_expression'),
        # ArraySupport: MySQL doesn't support arrays natively
        ('ArraySupport', 'format_array_expression'),
        # ExplainSupport: MySQL uses **kwargs for explain options
        ('ExplainSupport', 'format_explain_statement'),
        # QualifyClauseSupport: MariaDB doesn't support QUALIFY, param name differs
        ('QualifyClauseSupport', 'format_qualify_clause'),
        # MariaDBLockingSupport: format_lock_in_share_mode uses different param name
        ('MariaDBLockingSupport', 'format_lock_in_share_mode'),
        # GraphSupport: format_match_clause uses a different param name (_clause)
        ('GraphSupport', 'format_match_clause'),
        # OrderedSetAggregationSupport: format_ordered_set_aggregation uses a
        # different param name (_aggregation)
        ('OrderedSetAggregationSupport', 'format_ordered_set_aggregation'),
    }

    @pytest.mark.parametrize("protocol", MYSQL_PROTOCOLS)
    def test_method_signatures_match_protocol(self, dialect, protocol):
        """Each method on MariaDBDialect must have a compatible signature
        with the corresponding Protocol method."""
        proto_methods = get_all_protocol_methods(protocol)
        missing = []
        signature_mismatch = []

        for method_name in proto_methods:
            # Check existence
            if not hasattr(dialect, method_name):
                missing.append(method_name)
                continue

            # Check signature compatibility
            # Skip known mismatches between MySQL and generic protocols
            if (protocol.__name__, method_name) in self._SIGNATURE_MISMATCH_EXCLUSIONS:
                continue

            proto_method = getattr(protocol, method_name, None)
            dialect_method = getattr(dialect, method_name)

            if proto_method is not None and callable(proto_method):
                try:
                    proto_sig = inspect.signature(proto_method)
                    dialect_sig = inspect.signature(dialect_method)

                    # Compare parameter names (excluding 'self')
                    proto_params = [
                        p for p in proto_sig.parameters.values()
                        if p.name != 'self'
                    ]
                    dialect_params = [
                        p for p in dialect_sig.parameters.values()
                        if p.name != 'self'
                    ]

                    # Dialect must accept at least all required proto params
                    proto_required = [
                        p for p in proto_params
                        if p.default is inspect.Parameter.empty
                        and p.kind not in (
                            inspect.Parameter.VAR_POSITIONAL,
                            inspect.Parameter.VAR_KEYWORD,
                        )
                    ]
                    dialect_param_names = {p.name for p in dialect_params}

                    for req_param in proto_required:
                        if req_param.name not in dialect_param_names:
                            signature_mismatch.append(
                                f"{method_name}: missing required param "
                                f"'{req_param.name}' from protocol"
                            )
                except (ValueError, TypeError):
                    pass  # Some protocol methods can't be inspected

        assert not missing, (
            f"MariaDBDialect missing methods for {protocol.__name__}: {missing}"
        )
        assert not signature_mismatch, (
            f"Signature mismatches for {protocol.__name__}: {signature_mismatch}"
        )


class TestProtocolMixinForwardCoverage:
    """Verify every method declared in Protocol is implemented in Mixin.

    This catches the failure mode where a Protocol declares format_* or
    supports_* methods but the corresponding Mixin doesn't implement them.
    """

    @pytest.mark.parametrize("protocol,mixin", MYSQL_PROTOCOL_MIXIN_PAIRS)
    def test_protocol_declared_methods_are_implemented(self, protocol, mixin):
        """Every format_* / supports_* in Protocol must exist in Mixin.

        Only checks methods declared directly on the protocol (not inherited
        from parent protocols), since parent protocol methods are typically
        implemented by generic mixins rather than the MariaDB-specific one.
        """
        proto_methods = get_own_protocol_methods(protocol)
        mixin_methods = {name for name in dir(mixin) if not name.startswith('_')}
        missing = proto_methods - mixin_methods
        assert not missing, (
            f"{mixin.__name__} does not implement these methods "
            f"declared in {protocol.__name__}: {missing}"
        )


class TestProtocolMixinReverseCoverage:
    """Verify every format_*/supports_* in Mixin is declared in Protocol.

    This catches the failure mode where a Mixin implements format_* or
    supports_* methods but the corresponding Protocol doesn't declare them.
    This is the exact problem we're fixing: Mixin has format_* methods
    that Protocol doesn't know about.
    """

    @pytest.mark.parametrize("protocol,mixin", MYSQL_PROTOCOL_MIXIN_PAIRS)
    def test_mixin_public_methods_are_declared_in_protocol(self, protocol, mixin):
        """Every format_*/supports_*/get_* in Mixin must be declared in Protocol.

        Only checks methods defined on the Mixin itself (not inherited
        from object or other generic bases), and only public methods
        with the format_*/supports_*/get_* prefix pattern.
        """
        proto_methods = get_all_protocol_methods(protocol)

        # Collect Mixin's own public format_*, supports_*, get_* methods
        mixin_own_methods = set()
        for name in dir(mixin):
            if name.startswith('_'):
                continue
            if not (name.startswith('format_') or name.startswith('supports_')
                    or name.startswith('get_')):
                continue
            # Only include methods defined on the mixin itself, not inherited
            # from object or other generic bases
            if name in mixin.__dict__:
                mixin_own_methods.add(name)

        undeclared = mixin_own_methods - proto_methods
        assert not undeclared, (
            f"{mixin.__name__} implements these methods not declared in "
            f"{protocol.__name__}: {undeclared}"
        )

# ============================================================================
# MariaDBTypeSupport — a declared protocol has to be reachable
# ============================================================================


class TestMariaDBTypeProtocolIsComposed:
    """``MariaDBTypeSupport`` must be composed, exported, and answered correctly.

    The protocol was declared with nine ``supports_mariadb_*`` capability
    members, implemented by the mixin, and then left on the shelf: not exported
    from ``protocols/__init__.py``, not composed into ``MariaDBDialect``, and not
    in ``MYSQL_PROTOCOLS``. A ``runtime_checkable`` protocol is only an
    ``isinstance`` target, so with nothing composed there was no way for any
    caller -- or any test -- to see a single one of those members. MySQL's sibling
    ``MySQLTypeSupport`` has always composed its own, which is the precedent that
    makes this an inconsistency rather than a house style.

    Three things are checked here, and they are not the same thing:

    1. **composed** — ``isinstance(dialect, MariaDBTypeSupport)`` holds, and the
       protocol is really in the MRO rather than satisfied by accident;
    2. **answered** — each member returns the value its docstring claims, with
       the two version-gated ones exercised on *both* sides of their boundary;
    3. **not vacuous** — a wrong entry in ``MYSQL_PROTOCOLS`` would fail, and an
       incomplete dialect would fail, so the positive list cannot quietly become
       a list of hopes.
    """

    #: The protocol's own declared members. Read from the class rather than
    #: repeated here, so adding a member to the protocol without a test for it
    #: is impossible: the "every member is implemented" and "every member is
    #: reachable" checks below both walk this.
    @staticmethod
    def _declared_members():
        return [
            name for name in vars(mariadb_protocols.MariaDBTypeSupport)
            if not name.startswith("_")
        ]

    def test_protocol_is_exported_from_the_package(self):
        """Half the original defect: it was not even importable by name."""
        assert "MariaDBTypeSupport" in mariadb_protocols.__all__
        assert (
            mariadb_protocols.MariaDBTypeSupport
            is mariadb_protocol_types.MariaDBTypeSupport
        )

    def test_protocol_is_composed_into_the_dialect(self):
        assert mariadb_protocols.MariaDBTypeSupport in MariaDBDialect.__mro__

    def test_dialect_satisfies_the_protocol(self):
        dialect = mariadb_dialect.MariaDBDialect()
        assert isinstance(dialect, mariadb_protocols.MariaDBTypeSupport)

    def test_it_is_in_the_positive_conformance_list(self):
        assert mariadb_protocols.MariaDBTypeSupport in MYSQL_PROTOCOLS

    def test_mixin_defines_every_declared_member(self):
        """Forward coverage, and it is the mixin that must supply them.

        Without this the ``isinstance`` check would still pass if some *other*
        class in the MRO happened to answer ``supports_mariadb_xml_type``, which
        would leave the protocol satisfied by a class nobody intended to be
        responsible for it.
        """
        mixin = mysql_mixins.MariaDBTypeSupportMixin
        missing = [n for n in self._declared_members() if n not in vars(mixin)]
        assert not missing, (
            f"{mixin.__name__} does not implement these members declared in "
            f"MariaDBTypeSupport: {missing}"
        )

    def test_every_declared_member_is_reachable_on_the_dialect(self):
        dialect = mariadb_dialect.MariaDBDialect()
        missing = [
            n for n in self._declared_members()
            if not callable(getattr(dialect, n, None))
        ]
        assert not missing, (
            "MariaDBDialect cannot reach these declared capability members: "
            f"{missing}"
        )

    # ---- the values, on both sides of each version gate ----

    @pytest.mark.parametrize("member", [
        "supports_mariadb_integer_attributes",
        "supports_mariadb_mediumint_width",
        "supports_mariadb_year_display_width",
        "supports_mariadb_enum_charset",
        "supports_mariadb_geometry_srid",
        "supports_mariadb_sized_text",
        "supports_mariadb_sized_blob",
    ])
    def test_ungated_capability_is_true_on_every_supported_version(self, member):
        """These seven hold on every MariaDB release this backend supports.

        Asserted across the whole version span rather than on the fixture alone,
        because "always true" and "true because the fixture happens to be new
        enough" look identical at one version.
        """
        for version in [(10, 2, 0), (10, 6, 0), (11, 8, 9), (12, 3, 0),
                        (13, 0, 0), (13, 1, 1)]:
            target = mariadb_dialect.MariaDBDialect(version=version)
            assert getattr(target, member)() is True, (member, version)

    @pytest.mark.parametrize("version,expected", [
        ((10, 6, 0), False),
        ((11, 8, 9), False),
        ((12, 2, 2), False),
        ((12, 3, 0), True),
        ((12, 3, 3), True),
        ((13, 0, 2), True),
        ((13, 1, 1), True),
    ])
    def test_xml_capability_flips_at_12_3(self, version, expected):
        """``XMLTYPE`` arrived in 12.3; below it there is no XML type at all."""
        target = mariadb_dialect.MariaDBDialect(version=version)
        assert target.supports_mariadb_xml_type() is expected

    @pytest.mark.parametrize("version,expected", [
        ((10, 5, 9), False),
        ((10, 6, 28), False),
        ((10, 7, 0), True),
        ((12, 3, 3), True),
    ])
    def test_uuid_capability_flips_at_10_7(self, version, expected):
        """MariaDB's native ``UUID`` column type arrived in 10.7."""
        target = mariadb_dialect.MariaDBDialect(version=version)
        assert target.supports_mariadb_uuid_type() is expected

    @pytest.mark.parametrize("version", [
        (10, 6, 0), (10, 7, 0), (12, 2, 2), (12, 3, 0), (13, 1, 1),
    ])
    def test_gated_capability_agrees_with_the_per_type_gate(self, version):
        """One version boundary, two names -- they must not drift.

        The capability method is for a caller asking "does this server have the
        type"; the ``supports_data_type_*`` method is the same question read
        through the naming convention and is what the formatter's own gate uses.
        A divergence between them would mean the DDL could be refused by a
        capability that claimed to be available.
        """
        target = mariadb_dialect.MariaDBDialect(version=version)
        assert target.supports_mariadb_xml_type() is \
            target.supports_data_type_mariadb_xml()
        assert target.supports_mariadb_uuid_type() is \
            target.supports_data_type_uuid()
        assert target.supports_mariadb_uuid_type() is \
            target.supports_data_type_mariadb_uuid()

    @pytest.mark.parametrize("version,expected", [
        ((12, 2, 2), False),
        ((12, 3, 0), True),
    ])
    def test_gated_capability_matches_what_the_server_accepts(self, version, expected):
        """The gate has to be about the server, not about a hardcoded flag."""
        from rhosocial.activerecord.backend.impl.mariadb.mixins.backend import (
            MARIADB_VERSION_BOUNDARIES,
        )

        target = mariadb_dialect.MariaDBDialect(version=version)
        assert target.supports_mariadb_xml_type() is (
            version >= MARIADB_VERSION_BOUNDARIES["XMLTYPE"]
        )
        assert target.supports_mariadb_xml_type() is expected
        assert target.supports_mariadb_uuid_type() is (
            version >= MARIADB_VERSION_BOUNDARIES["UUID"]
        )

    # ---- the negative direction: a wrong entry has to fail ----

    def test_positive_list_contains_only_protocols_the_dialect_satisfies(
        self,
    ):
        """``MYSQL_PROTOCOLS`` must not be able to grow an unbacked entry.

        ``test_implements_protocol`` already asserts this one protocol at a time;
        the loop is here so that adding a bogus entry produces one failure naming
        the entry, instead of a single parametrised failure among dozens.
        """
        dialect = mariadb_dialect.MariaDBDialect()
        unsatisfied = [
            p.__name__ for p in MYSQL_PROTOCOLS
            if getattr(p, "_is_runtime_protocol", False)
            and not isinstance(dialect, p)
        ]
        assert not unsatisfied, (
            f"MariaDBDialect does not satisfy protocols listed as supported: "
            f"{unsatisfied}. Either compose the mixin that implements them or "
            f"remove them from MYSQL_PROTOCOLS."
        )

    def test_an_object_missing_the_members_is_not_an_instance(self):
        """The ``isinstance`` check has teeth: it is not vacuously true.

        A bare object is the easy direction. The one that matters is an object
        satisfying *all but one* member -- the shape a partially-landed fix takes
        -- because that is the failure ``isinstance`` exists to catch.
        """
        protocol = mariadb_protocols.MariaDBTypeSupport
        members = self._declared_members()
        assert members

        class Nothing:
            pass

        assert not isinstance(Nothing(), protocol)

        class AlmostNothing:
            pass

        for name in members[:-1]:
            setattr(AlmostNothing, name, lambda self: True)
        assert not isinstance(AlmostNothing(), protocol)

        class Everything:
            pass

        for name in members:
            setattr(Everything, name, lambda self: True)
        assert isinstance(Everything(), protocol)

    def test_a_mixin_missing_one_member_would_not_satisfy_the_protocol(self):
        """Remove one method from the mixin and the check must notice.

        This is the regression the original defect would have passed: a protocol
        that nothing composes can be edited forever without a single test
        failing, because no code path reaches it.

        The patched classes are built on ``object``, *not* on the mixin, so the
        dropped member is genuinely absent rather than merely shadowed -- a
        subclass would still find the real implementation further up its MRO and
        the assertion would pass for the wrong reason.
        """
        protocol = mariadb_protocols.MariaDBTypeSupport
        members = self._declared_members()
        base = mysql_mixins.MariaDBTypeSupportMixin
        implementations = {n: vars(base)[n] for n in members}

        for drop in members:
            namespace = {n: f for n, f in implementations.items() if n != drop}
            patched = type("PatchedMixin", (), namespace)()
            assert not isinstance(patched, protocol), (
                f"dropping {drop} should stop {base.__name__} satisfying "
                f"{protocol.__name__}, but isinstance() still says yes"
            )

        # ...and with every member present it is satisfied again, so the loop
        # above is measuring the member set and not something incidental.
        complete = type("CompleteMixin", (), dict(implementations))()
        assert isinstance(complete, protocol)
