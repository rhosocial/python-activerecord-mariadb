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
    CollationSupport,
    CTESupport,
    WindowFunctionSupport,
    ReturningSupport,
    SetOperationSupport,
    SequenceSupport,
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
    SchemaSupport,
    IndexSupport,
    ConstraintSupport,
    IntrospectionSupport,
    TransactionControlSupport,
    GeneratedColumnSupport,
    ViewSupport,
    FunctionSupport,
    # Additional Protocols
    SQLFunctionSupport,
    DDLTypeSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CollationMixin,
    CTEMixin,
    WindowFunctionMixin,
    JSONMixin,
    ReturningMixin,
    SetOperationMixin,
    SequenceMixin,
    UpsertMixin,
    LockingMixin,
    ExplainMixin,
    JoinMixin,
    ILIKEMixin,
    FilterClauseMixin,
    AdvancedGroupingMixin,
    ArrayMixin,
    LateralJoinMixin,
    MergeMixin,
    TemporalTableMixin,
    QualifyClauseMixin,
    OrderedSetAggregationMixin,
    GraphMixin,
    # DDL Mixins
    TableMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    TriggerMixin,
    GeneratedColumnMixin,
    ViewMixin,
    FunctionMixin,
    IntrospectionMixin,
    # Additional Mixins
    IdentifierMixin,
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    TransactionControlMixin,
    PartitionMixin,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

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
    MariaDBSetTypeMixin,
    MariaDBModifyColumnMixin,
    MariaDBPartitionMixin,
    MariaDBTypeSupportMixin,
    MariaDBTypeSuggestionMixin,
    MariaDBAlterColumnModifierMixin,
    MariaDBAlterConstraintModifierMixin,
    MariaDBRenameTableMixin,
    MariaDBTruncateMixin,
    MariaDBAlterTableMixin,
    MariaDBMaintenanceMixin,
    MariaDBRoutineMixin,
    MariaDBAdminMixin,
    MARIADB_VERSION_BOUNDARIES,
)
from .collation import validate_mariadb_collation_name
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
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression import bases
    from rhosocial.activerecord.backend.expression.collation import CollateExpression
    from rhosocial.activerecord.backend.expression.statements import (
        CreateTableExpression,
        InsertExpression,
        ReturningClause,
    )
    from rhosocial.activerecord.backend.expression.statements.ddl_alter import ModifyColumn
    from .expression.load_data import MariaDBLoadDataExpression

MARIADB_VERSION_BOUNDARIES = {
    'WINDOW_FUNCTIONS': (10, 2, 0),
    'CTE': (10, 2, 0),
    'JSON_FUNCTIONS': (10, 2, 3),
    'JSON_ARROWS': (10, 2, 7),
    'INTERSECT_EXCEPT': (10, 3, 0),
    'SEQUENCE': (10, 3, 0),
    'SYSTEM_VERSIONING': (10, 3, 0),
    'RETURNING': (10, 5, 0),
    'EXPLAIN_FORMAT': (10, 6, 0),
    'INSTEAD_OF_TRIGGER': (10, 4, 0),
    'SKIP_LOCKED': (10, 3, 0),
    'RENAME_TABLE_IF_EXISTS': (10, 5, 0),
    'RENAME_TABLE_WAIT': (10, 3, 0),
    'TRUNCATE_WAIT': (10, 3, 0),
    'ROUTINE_OR_REPLACE': (10, 1, 3),
    'ROUTINE_IF_NOT_EXISTS': (10, 1, 3),
    'GRANT_OR_REPLACE': (10, 1, 4),
    'GRANT_IF_EXISTS': (10, 1, 4),
    'DENY': (13, 1, 0),
}

_SUGGESTION_ARRAY = "MariaDB does not support native array types. Use JSON arrays instead."
_SUGGESTION_GRAPH_MATCH = "MariaDB does not support graph MATCH clause."
_SUGGESTION_ORDERED_SET_AGG = "MariaDB does not support ordered-set aggregate functions (WITHIN GROUP)."
_SUGGESTION_QUALIFY = "MariaDB does not support QUALIFY clause. Use a subquery or CTE instead."
_SUGGESTION_MERGE = "MariaDB does not support MERGE statement. Use INSERT ... ON DUPLICATE KEY UPDATE instead."
_SUGGESTION_TEMPORAL = "MariaDB system-versioned tables require specific table creation syntax."


class MariaDBDialect(
    SQLDialectBase,
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
    MariaDBSetTypeMixin,
    MariaDBModifyColumnMixin,
    MariaDBPartitionMixin,
    MariaDBTypeSupportMixin,
    MariaDBTypeSuggestionMixin,
    MariaDBAlterColumnModifierMixin,
    MariaDBAlterConstraintModifierMixin,
    MariaDBRenameTableMixin,
    MariaDBAlterTableMixin,
    MariaDBMaintenanceMixin,
    MariaDBRoutineMixin,
    MariaDBAdminMixin,
    CollationMixin,
    CTEMixin,
    WindowFunctionMixin,
    JSONMixin,
    ReturningMixin,
    SetOperationMixin,
    SequenceMixin,
    UpsertMixin,
    LockingMixin,
    ExplainMixin,
    JoinMixin,
    ILIKEMixin,
    FilterClauseMixin,
    AdvancedGroupingMixin,
    ArrayMixin,
    LateralJoinMixin,
    MergeMixin,
    TemporalTableMixin,
    QualifyClauseMixin,
    OrderedSetAggregationMixin,
    GraphMixin,
    TableMixin,
    MariaDBTruncateMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    TriggerMixin,
    GeneratedColumnMixin,
    ViewMixin,
    FunctionMixin,
    IntrospectionMixin,
    IdentifierMixin,
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    TransactionControlMixin,
    PartitionMixin,
    # Protocol support markers
    CollationSupport,
    CTESupport,
    WindowFunctionSupport,
    ReturningSupport,
    SetOperationSupport,
    SequenceSupport,
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
    SchemaSupport,
    IndexSupport,
    ConstraintSupport,
    IntrospectionSupport,
    TransactionControlSupport,
    GeneratedColumnSupport,
    ViewSupport,
    FunctionSupport,
    SQLFunctionSupport,
    DDLTypeSupport,
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
        if version is not None:
            self.version = version

    def format_insert_statement(self, expr: "InsertExpression"):
        """Delegate INSERT formatting to MariaDBDMLOperationMixin."""
        # Explicit override to ensure MariaDB's INSERT IGNORE / REPLACE INTO logic is used
        from .mixins.dml import MariaDBDMLOperationMixin
        return MariaDBDMLOperationMixin.format_insert_statement(self, expr)

    def format_replace_statement(self, expr: "InsertExpression"):
        """Delegate REPLACE formatting to MariaDBDMLOperationMixin."""
        from .mixins.dml import MariaDBDMLOperationMixin
        return MariaDBDMLOperationMixin.format_replace_statement(self, expr)

    def format_load_data_statement(self, expr: "MariaDBLoadDataExpression"):
        """Delegate LOAD DATA formatting to MariaDBDMLOperationMixin."""
        from .mixins.dml import MariaDBDMLOperationMixin
        return MariaDBDMLOperationMixin.format_load_data_statement(self, expr)

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

    def format_date_trunc_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        field = expr.field.value.upper()
        formats = {
            "YEAR": "%Y-01-01 00:00:00",
            "MONTH": "%Y-%m-01 00:00:00",
            "DAY": "%Y-%m-%d 00:00:00",
            "HOUR": "%Y-%m-%d %H:00:00",
            "MINUTE": "%Y-%m-%d %H:%i:00",
            "SECOND": "%Y-%m-%d %H:%i:%s",
        }
        if field not in formats:
            raise UnsupportedFeatureError(self.name, f"date_trunc({expr.field.value})")
        sql = f"CAST(DATE_FORMAT({source_sql}, %s) AS DATETIME)"
        return self._apply_value_expression_modifiers(
            sql, source_params + (formats[field],), expr
        )

    def format_interval_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        sql = f"INTERVAL %s {expr.unit.value.upper()}"
        return self._apply_value_expression_modifiers(sql, (expr.value,), expr)

    def format_datetime_add_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"DATE_ADD({source_sql}, {interval_sql})"
        return self._apply_value_expression_modifiers(
            sql, source_params + interval_params, expr
        )

    def format_datetime_subtract_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"DATE_SUB({source_sql}, {interval_sql})"
        return self._apply_value_expression_modifiers(
            sql, source_params + interval_params, expr
        )

    def format_datetime_diff_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        start_sql, start_params = expr.start.to_sql()
        end_sql, end_params = expr.end.to_sql()
        sql = f"TIMESTAMPDIFF({expr.unit.value.upper()}, {start_sql}, {end_sql})"
        return self._apply_value_expression_modifiers(sql, start_params + end_params, expr)

    def supports_collate_expression(self) -> bool:
        """MariaDB supports expression-level COLLATE."""
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate MariaDB collation names and return their SQL representation."""
        if expr.collation_options:
            unsupported = ", ".join(sorted(expr.collation_options))
            raise UnsupportedFeatureError(self.name, f"COLLATE options: {unsupported}")
        return validate_mariadb_collation_name(expr.collation_name, getattr(self, "version", None))

    def format_identifier(self, identifier: str) -> str:
        """Format identifier using MariaDB's backtick quoting mechanism.

        Args:
            identifier: Raw identifier string

        Returns:
            Quoted identifier with escaped internal backticks
        """
        escaped = identifier.replace('`', '``')
        return f'`{escaped}`'

    # region Version-based feature support
    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['CTE']

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['CTE']

    def supports_materialized_cte(self) -> bool:
        """MATERIALIZED hint is not supported by MariaDB."""
        return False

    def supports_window_functions(self) -> bool:
        """Window functions are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']

    def supports_window_frame_clause(self) -> bool:
        """Window frame clauses are supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']

    def supports_returning_insert(self) -> bool:
        """RETURNING clause for INSERT is supported since MariaDB 10.5."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_returning_update(self) -> bool:
        """RETURNING clause for UPDATE is NOT supported by MariaDB."""
        return False

    def supports_returning_delete(self) -> bool:
        """RETURNING clause for DELETE is supported since MariaDB 10.5."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['RETURNING']

    def supports_json_type(self) -> bool:
        """JSON type is supported since MariaDB 10.2.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['JSON_FUNCTIONS']

    def get_json_access_operator(self) -> str:
        """MariaDB uses '->' for JSON access (since 10.2.7)."""
        if self.version >= MARIADB_VERSION_BOUNDARIES['JSON_ARROWS']:
            return "->"
        return ""

    def supports_json_table(self) -> bool:
        """MariaDB does not support JSON_TABLE function directly."""
        return False

    def supports_filter_clause(self) -> bool:
        """FILTER clause is supported since MariaDB 10.2."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['WINDOW_FUNCTIONS']

    def supports_intersect(self) -> bool:
        """INTERSECT is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']

    def supports_except(self) -> bool:
        """EXCEPT is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['INTERSECT_EXCEPT']

    def supports_sequence(self) -> bool:
        """SEQUENCE is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_create_sequence(self) -> bool:
        """CREATE SEQUENCE is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_drop_sequence(self) -> bool:
        """DROP SEQUENCE is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_alter_sequence(self) -> bool:
        """ALTER SEQUENCE is supported since MariaDB 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['SEQUENCE']

    def supports_upsert(self) -> bool:
        """UPSERT (ON DUPLICATE KEY UPDATE) is supported."""
        return True

    def get_upsert_syntax_type(self) -> str:
        """MariaDB uses ON DUPLICATE KEY UPDATE syntax."""
        return "ON DUPLICATE KEY"

    def supports_on_conflict_clause(self) -> bool:
        """Whether INSERT can carry an ON CONFLICT style clause.

        MariaDB expresses upsert via the ON DUPLICATE KEY UPDATE clause.
        """
        return True

    def supports_multiple_on_conflict_clauses(self) -> bool:
        """MariaDB ON DUPLICATE KEY UPDATE allows only a single clause."""
        return False

    def supports_explain_analyze(self) -> bool:
        """EXPLAIN ANALYZE is supported since MariaDB 10.6."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT']

    def supports_explain_format(self, format_type: str) -> bool:
        """Check if specific EXPLAIN format is supported since MariaDB 10.6.

        MariaDB supports FORMAT=JSON and FORMAT=TRADITIONAL.
        FORMAT=TREE is MySQL 8.0+ only and not supported by MariaDB.
        """
        if self.version >= MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT']:
            return format_type.upper() in ["JSON", "TRADITIONAL"]
        return False

    # endregion

    # region Unsupported features
    def supports_rollup(self) -> bool:
        """MariaDB supports ROLLUP with GROUP BY."""
        return True

    def supports_cube(self) -> bool:
        """MariaDB does not support CUBE."""
        return False

    def supports_grouping_sets(self) -> bool:
        """MariaDB does not support GROUPING SETS."""
        return False

    def supports_array_type(self) -> bool:
        """MariaDB does not support native array types."""
        return False

    def supports_array_constructor(self) -> bool:
        """MariaDB does not support ARRAY constructor."""
        return False

    def supports_array_access(self) -> bool:
        """MariaDB does not support array subscript access."""
        return False

    def supports_graph_match(self) -> bool:
        """MariaDB does not support graph MATCH clause."""
        return False

    def supports_ordered_set_aggregation(self) -> bool:
        """MariaDB does not support ordered-set aggregate functions."""
        return False

    def supports_qualify_clause(self) -> bool:
        """MariaDB does not support QUALIFY clause."""
        return False

    def supports_merge_statement(self) -> bool:
        """MariaDB does not support MERGE statement."""
        return False

    def supports_for_update_skip_locked(self) -> bool:
        """MariaDB supports FOR UPDATE SKIP LOCKED."""
        return True

    def supports_lateral_join(self) -> bool:
        """MariaDB supports LATERAL joins."""
        return True

    def supports_ilike(self) -> bool:
        """MariaDB does not support ILIKE directly (use LOWER())."""
        return False

    def supports_temporal_tables(self) -> bool:
        """MariaDB supports system-versioned tables since 10.3."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['SYSTEM_VERSIONING']

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

    def format_array_expression(self, _expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format array expression - not supported."""
        raise UnsupportedFeatureError(self.name, "Array operations", _SUGGESTION_ARRAY)

    def format_match_clause(self, _clause) -> Tuple[str, tuple]:
        """Format MATCH clause - not supported."""
        raise UnsupportedFeatureError(self.name, "graph MATCH clause", _SUGGESTION_GRAPH_MATCH)

    def format_ordered_set_aggregation(self, _aggregation) -> Tuple[str, Tuple]:
        """Format ordered-set aggregation - not supported."""
        raise UnsupportedFeatureError(self.name, "ordered-set aggregate functions", _SUGGESTION_ORDERED_SET_AGG)

    def format_qualify_clause(self, clause) -> Tuple[str, tuple]:
        """Format QUALIFY clause - not supported."""
        raise UnsupportedFeatureError(self.name, "QUALIFY clause", _SUGGESTION_QUALIFY)

    # endregion

    # region DDL Support
    def supports_create_table(self) -> bool:
        return True

    def supports_drop_table(self) -> bool:
        return True

    def supports_alter_table(self) -> bool:
        return True

    def supports_temporary_table(self) -> bool:
        return True

    def supports_if_not_exists_table(self) -> bool:
        return True

    def supports_if_exists_table(self) -> bool:
        return True

    def supports_rename_table(self) -> bool:
        return True

    def supports_rename_column(self) -> bool:
        return True

    def supports_drop_column(self) -> bool:
        return True

    def supports_table_partitioning(self) -> bool:
        return True

    def supports_table_tablespace(self) -> bool:
        return False

    def supports_create_index(self) -> bool:
        return True

    def supports_drop_index(self) -> bool:
        return True

    def supports_unique_index(self) -> bool:
        return True

    def supports_index_if_exists(self) -> bool:
        return True

    def supports_index_if_not_exists(self) -> bool:
        return True

    def supports_partial_index(self) -> bool:
        return False

    def supports_functional_index(self) -> bool:
        return True

    def supports_concurrent_index(self) -> bool:
        return False

    def supports_index_type(self) -> bool:
        return True

    def supports_index_tablespace(self) -> bool:
        return False

    def supports_fulltext_index(self) -> bool:
        return True

    def supports_fulltext_boolean_mode(self) -> bool:
        return True

    def supports_fulltext_parser(self) -> bool:
        return True

    def supports_fulltext_query_expansion(self) -> bool:
        return True

    def supports_index_include(self) -> bool:
        return False

    def supports_generated_columns(self) -> bool:
        return True

    def supports_stored_generated_columns(self) -> bool:
        return True

    def supports_virtual_generated_columns(self) -> bool:
        return True

    def supports_truncate(self) -> bool:
        return True

    def supports_truncate_table_keyword(self) -> bool:
        return True

    def supports_truncate_restart_identity(self) -> bool:
        return False

    def supports_truncate_cascade(self) -> bool:
        return False

    def supports_create_view(self) -> bool:
        return True

    def supports_drop_view(self) -> bool:
        return True

    def supports_or_replace_view(self) -> bool:
        return True

    def supports_temporary_view(self) -> bool:
        return True

    def supports_materialized_view(self) -> bool:
        return False

    def supports_if_exists_view(self) -> bool:
        return True

    def supports_view_check_option(self) -> bool:
        return True

    def supports_cascade_view(self) -> bool:
        return True

    def supports_trigger(self) -> bool:
        return True

    def supports_create_trigger(self) -> bool:
        return True

    def supports_drop_trigger(self) -> bool:
        return True

    def supports_instead_of_trigger(self) -> bool:
        return True

    def supports_statement_trigger(self) -> bool:
        return False

    def supports_trigger_referencing(self) -> bool:
        return True

    def supports_trigger_when(self) -> bool:
        return True

    def supports_trigger_if_not_exists(self) -> bool:
        return False

    def supports_schema(self) -> bool:
        """MariaDB has no schema layer distinct from its databases."""
        return False

    def supports_create_schema(self) -> bool:
        return False

    def supports_drop_schema(self) -> bool:
        return False

    def supports_function(self) -> bool:
        return True

    def supports_create_function(self) -> bool:
        return True

    def supports_drop_function(self) -> bool:
        return True

    def supports_function_or_replace(self) -> bool:
        return True

    def supports_function_parameters(self) -> bool:
        return True

    # endregion

    # region Function Support

    _MARIADB_FUNCTION_VERSIONS = {
        # JSON functions: MariaDB 10.2.3+
        "json_extract": ((10, 2, 3), None),
        "json_unquote": ((10, 2, 3), None),
        "json_object": ((10, 2, 3), None),
        "json_array": ((10, 2, 3), None),
        "json_contains": ((10, 2, 3), None),
        "json_set": ((10, 2, 3), None),
        "json_remove": ((10, 2, 3), None),
        "json_type": ((10, 2, 3), None),
        "json_valid": ((10, 2, 3), None),
        "json_search": ((10, 2, 3), None),
        # Spatial functions: MariaDB 10.2+
        "st_geom_from_text": ((10, 2, 0), None),
        "st_geom_from_wkb": ((10, 2, 0), None),
        "st_as_text": ((10, 2, 0), None),
        "st_as_geojson": ((10, 2, 0), None),
        "st_distance": ((10, 2, 0), None),
        "st_within": ((10, 2, 0), None),
        "st_contains": ((10, 2, 0), None),
        "st_intersects": ((10, 2, 0), None),
        # Full-text search: All versions
        "match_against": (None, None),
        # SET type functions: All versions
        "find_in_set": (None, None),
        # Enum type functions: All versions
        "elt": (None, None),
        "field": (None, None),
        # Math enhanced functions: All versions
        "round_": (None, None),
        "pow": (None, None),
        "power": (None, None),
        "sqrt": (None, None),
        "mod": (None, None),
        "ceil": (None, None),
        "floor": (None, None),
        "trunc": (None, None),
        "max_": (None, None),
        "min_": (None, None),
        "avg": (None, None),
        # Bitwise functions: All versions (native operators)
        "bit_and": (None, None),
        "bit_or": (None, None),
        "bit_xor": (None, None),
        "bit_count": ((10, 0, 0), None),
        "bit_get_bit": (None, None),
        "bit_shift_left": (None, None),
        "bit_shift_right": (None, None),
    }

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        This method combines:
        1. Core functions from rhosocial.activerecord.backend.expression.functions
        2. MariaDB-specific functions from rhosocial.activerecord.backend.impl.mariadb.functions

        MariaDB version-specific functions:
        - JSON functions: MariaDB 10.2.3+
        - Spatial functions: MariaDB 10.2+
        - BIT_COUNT: MariaDB 10.0+

        Returns:
            Dict mapping function names to True (supported) or False.
        """
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )
        from rhosocial.activerecord.backend.impl.mariadb import functions as mariadb_functions

        expression_constructors = {
            "xmlagg",
            "xmlattributes",
            "xmlcomment",
            "xmlconcat",
            "xmlelement",
            "xmlexists",
            "xmlforest",
            "xmlparse",
            "xmlpi",
            "xmlquery",
            "xmlroot",
            "xmlserialize",
            "xmltable",
        }
        result = {}
        for func_name in core_functions:
            if func_name not in expression_constructors:
                result[func_name] = True

        mariadb_funcs = getattr(mariadb_functions, "__all__", [])
        for func_name in mariadb_funcs:
            if func_name in self._MARIADB_FUNCTION_VERSIONS:
                result[func_name] = self._is_mariadb_function_supported(func_name)
            elif func_name not in result:
                result[func_name] = True

        return result

    def _is_mariadb_function_supported(self, func_name: str) -> bool:
        """Check if a MariaDB-specific function is supported based on version.

        Args:
            func_name: Name of the MariaDB function

        Returns:
            True if supported, False otherwise
        """
        version_range = self._MARIADB_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        min_version, max_version = version_range

        if min_version is not None and self.version < min_version:
            return False

        if max_version is not None and self.version > max_version:
            return False

        return True


    def format_table_options(self, expr) -> str:
        """Render MariaDB table options from ``expr.table_options``.

        The structured ``TableOptions`` (charset/collation/engine/comment)
        fully owns the tail options when present; otherwise the raw
        ``expr.storage_options`` dict is used as a legacy fallback.
        """
        opts = getattr(expr, "table_options", None)
        if opts is not None and getattr(opts, "has_options", lambda: False)():
            parts = []
            if opts.engine:
                parts.append(f"ENGINE={opts.engine}")
            if opts.charset:
                parts.append(f"DEFAULT CHARACTER SET={opts.charset}")
            if opts.collation:
                parts.append(f"COLLATE={opts.collation}")
            if opts.tablespace:
                parts.append(f"TABLESPACE={opts.tablespace}")
            if opts.comment:
                escaped = self._escape_sql_string(opts.comment)
                parts.append(f"COMMENT='{escaped}'")
            return ' '.join(parts)

        if expr.storage_options:
            return self.format_storage_options(expr.storage_options)
        return ""

    def format_create_table_like(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE statement."""
        like_table = expr.dialect_options['like_table']

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(expr.table.to_sql()[0])

        if isinstance(like_table, tuple):
            schema, table = like_table
            like_table_str = f"{self.format_identifier(schema)}.{self.format_identifier(table)}"
        else:
            like_table_str = self.format_identifier(like_table)

        parts.append(f"LIKE {like_table_str}")
        return ' '.join(parts), ()

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        value = value.replace('\\', '\\\\')
        value = value.replace("'", "''")
        return value

    def format_column_definition(
        self,
        col_def: "ColumnDefinition",
        constraint_type=None,
    ) -> Tuple[str, List[Any]]:
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            ColumnConstraintType,
        )
        if constraint_type is None:
            constraint_type = ColumnConstraintType
        type_sql, type_params = col_def.data_type.to_sql(self)
        parts = [self.format_identifier(col_def.name), type_sql]
        params: List[Any] = list(type_params)

        constraint_parts = []
        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                constraint_parts.append("PRIMARY KEY")
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                constraint_parts.append("NOT NULL")
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                constraint_parts.append("UNIQUE")
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                if constraint.default_value is not None:
                    from rhosocial.activerecord.backend.expression import bases
                    if isinstance(constraint.default_value, bases.BaseExpression):
                        default_sql, default_params = constraint.default_value.to_sql()
                        constraint_parts.append(f"DEFAULT {default_sql}")
                        params.extend(default_params)
                    elif isinstance(constraint.default_value, str):
                        escaped = self._escape_sql_string(constraint.default_value)
                        constraint_parts.append(f"DEFAULT '{escaped}'")
                    else:
                        constraint_parts.append(f"DEFAULT {constraint.default_value}")
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                constraint_parts.append("NULL")

            if constraint.is_auto_increment:
                constraint_parts.append("AUTO_INCREMENT")

        if constraint_parts:
            parts.append(' '.join(constraint_parts))

        if col_def.comment:
            escaped_comment = self._escape_sql_string(col_def.comment)
            parts.append(f"COMMENT '{escaped_comment}'")

        return ' '.join(parts), tuple(params)

    def format_table_constraint(
        self,
        t_const: "TableConstraint",
        TableConstraintType
    ) -> Tuple[str, List[Any]]:
        from rhosocial.activerecord.backend.expression.statements import (
            ForeignKeyConstraint, ReferentialAction,
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
                ref_table = self.format_identifier(t_const.foreign_key_table)
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

            if t_const.dialect_options and t_const.dialect_options.get('enforced') is False:
                parts.append("NOT ENFORCED")

        return ' '.join(parts), tuple(params)

    def format_inline_index(self, idx_def: "IndexDefinition") -> str:
        parts = []

        if idx_def.unique:
            parts.append("UNIQUE")

        parts.append("INDEX")
        parts.append(self.format_identifier(idx_def.name))

        cols_str = ', '.join(self.format_identifier(c) for c in idx_def.columns)
        parts.append(f"({cols_str})")

        if idx_def.type:
            parts.append(f"USING {idx_def.type}")

        return ' '.join(parts)

    def format_storage_options(self, storage_options: Dict[str, Any]) -> str:
        parts = []
        for key, value in storage_options.items():
            if isinstance(value, str):
                parts.append(f"{key}='{self._escape_sql_string(value)}'")
            else:
                parts.append(f"{key}={value}")
        return ' '.join(parts)

    # region ConstraintSupport protocol implementation (MariaDB)

    def supports_primary_key_constraint(self) -> bool:
        return True

    def supports_unique_constraint(self) -> bool:
        return True

    def supports_not_null_constraint(self) -> bool:
        return True

    def supports_check_constraint(self) -> bool:
        return True

    def supports_foreign_key_constraint(self) -> bool:
        return True

    def supports_fk_on_delete(self) -> bool:
        return True

    def supports_fk_on_update(self) -> bool:
        return True

    def supports_fk_match(self) -> bool:
        return False

    def supports_deferrable_constraint(self) -> bool:
        return False

    def supports_constraint_enforced(self) -> bool:
        return self.version >= (10, 2, 22)

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

    def supports_savepoint(self) -> bool:
        return True

    def format_begin_transaction(self, expr) -> Tuple[str, tuple]:
        """Format BEGIN TRANSACTION statement for MariaDB.

        MariaDB does not support isolation level within START TRANSACTION.
        When isolation level is set, generates SET TRANSACTION ISOLATION LEVEL
        followed by START TRANSACTION (with optional READ ONLY/READ WRITE).
        """
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        # Build SET TRANSACTION ISOLATION LEVEL if needed
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

        # Build START TRANSACTION with optional mode
        if expr._mode == TransactionMode.READ_ONLY:
            begin_sql = "START TRANSACTION READ ONLY"
        elif expr._mode == TransactionMode.READ_WRITE:
            begin_sql = "START TRANSACTION READ WRITE"
        else:
            begin_sql = "START TRANSACTION"

        return f"{set_isolation}{begin_sql}", ()

    def format_set_transaction(self, expr) -> Tuple[str, tuple]:
        """Format SET TRANSACTION statement for MariaDB.

        MariaDB supports SET TRANSACTION for isolation level and
        access mode (READ ONLY / READ WRITE).

        Args:
            expr: SetTransactionExpression with isolation level and/or mode.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        parts = ["SET TRANSACTION"]

        # Add isolation level if set
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

        # Add access mode if set
        if expr._mode is not None:
            if expr._mode == TransactionMode.READ_ONLY:
                parts.append("READ ONLY")
            elif expr._mode == TransactionMode.READ_WRITE:
                parts.append("READ WRITE")

        return " ".join(parts), ()

    # endregion

    # region CreateTableExpression diff support

    def _supports_alter_column_type(self) -> bool:
        """MariaDB changes column types in place via MODIFY COLUMN."""
        return True

    def alter_column_type_action(self, old_col, new_col) -> "ModifyColumn":
        """Build the in-place type-change action (MODIFY COLUMN <new def>)."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import ModifyColumn
        return ModifyColumn(self, column=new_col)

    # endregion

    # region Explain

    def format_explain_statement(self, expr) -> Tuple[str, tuple]:
        """Format EXPLAIN statement for MariaDB.

        MariaDB uses FORMAT=JSON (with equals sign), not FORMAT JSON.
        """
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

    # endregion
