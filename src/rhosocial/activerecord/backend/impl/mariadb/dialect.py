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
    CTESupport,
    WindowFunctionSupport,
    JSONSupport,
    ReturningSupport,
    SetOperationSupport,
    SequenceSupport,
    UpsertSupport,
    LockingSupport,
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
    # DDL Protocols
    TableSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    TriggerSupport,
    GeneratedColumnSupport,
    ViewSupport,
    FunctionSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
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
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression import bases
    from rhosocial.activerecord.backend.expression.statements import ReturningClause

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
}

_SUGGESTION_ARRAY = "MariaDB does not support native array types. Use JSON arrays instead."
_SUGGESTION_GRAPH_MATCH = "MariaDB does not support graph MATCH clause."
_SUGGESTION_ORDERED_SET_AGG = "MariaDB does not support ordered-set aggregate functions (WITHIN GROUP)."
_SUGGESTION_QUALIFY = "MariaDB does not support QUALIFY clause. Use a subquery or CTE instead."
_SUGGESTION_MERGE = "MariaDB does not support MERGE statement. Use INSERT ... ON DUPLICATE KEY UPDATE instead."
_SUGGESTION_TEMPORAL = "MariaDB system-versioned tables require specific table creation syntax."


class MariaDBDialect(
    SQLDialectBase,
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
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    TriggerMixin,
    GeneratedColumnMixin,
    ViewMixin,
    FunctionMixin,
    CTESupport,
    WindowFunctionSupport,
    JSONSupport,
    ReturningSupport,
    SetOperationSupport,
    SequenceSupport,
    UpsertSupport,
    LockingSupport,
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
    TableSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    TriggerSupport,
    GeneratedColumnSupport,
    ViewSupport,
    FunctionSupport,
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

    def __init__(self, version: Tuple[int, int, int] = (10, 11, 0)):
        """Initialize MariaDB dialect with specific version.

        Args:
            version: MariaDB version tuple (major, minor, patch)
        """
        self.version = version
        super().__init__()

    def get_parameter_placeholder(self, position: int = 0) -> str:
        """MariaDB uses positional placeholders like :0, :1 or %s."""
        return "%s"

    def get_server_version(self) -> Tuple[int, int, int]:
        """Return the MariaDB version this dialect is configured for."""
        return self.version

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

    def supports_returning_clause(self) -> bool:
        """RETURNING clause is supported since MariaDB 10.5."""
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

    def supports_explain_analyze(self) -> bool:
        """EXPLAIN ANALYZE is supported since MariaDB 10.6."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT']

    def supports_explain_format(self, format_type: str) -> bool:
        """Check if specific EXPLAIN format is supported since MariaDB 10.6."""
        if self.version >= MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT']:
            return format_type.upper() in ["JSON", "TREE", "TRADITIONAL"]
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
        if not self.supports_returning_clause():
            raise UnsupportedFeatureError(
                self.name, "RETURNING clause",
                "RETURNING clause requires MariaDB 10.5 or later. Use a separate SELECT statement."
            )

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

    def format_qualify_clause(self, _clause) -> Tuple[str, tuple]:
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
        return False

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
