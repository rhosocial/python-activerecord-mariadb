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
    MariaDBCollationMixin,
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
)
from .reserved_words import MARIADB_RESERVED_WORDS
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
    from rhosocial.activerecord.backend.expression.statements import (
        InsertExpression,
        ReturningClause,
    )
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
    MariaDBAlterColumnModifierMixin,
    MariaDBAlterConstraintModifierMixin,
    MariaDBRenameTableMixin,
    MariaDBAlterTableMixin,
    MariaDBMaintenanceMixin,
    MariaDBRoutineMixin,
    MariaDBAdminMixin,
    # New mixins from dialect.py split
    MariaDBDateTimeMixin,
    MariaDBCollationMixin,
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
        self._reserved_words = MARIADB_RESERVED_WORDS
        if version is not None:
            self.version = version

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

    def suggested_data_types(self) -> Dict[str, type]:
        """Cross-backend type-consistency suggestions for MariaDB."""
        from .expression.types import (
            MariaDBBinaryType,
            MariaDBEnumType,
            MariaDBVarBinaryType,
        )

        return {
            "uuid": MariaDBBinaryType,
            "enum": MariaDBEnumType,
            "binary": MariaDBBinaryType,
            "varbinary": MariaDBVarBinaryType,
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
        """Format BEGIN TRANSACTION statement for MariaDB."""
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

        return f"{set_isolation}{begin_sql}", ()

    def format_set_transaction(self, expr) -> Tuple[str, tuple]:
        """Format SET TRANSACTION statement for MariaDB."""
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

    def format_create_table_statement(
        self, expr: "CreateTableExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement for MariaDB."""
        all_params: List[Any] = []

        options_part = ""
        table_options = getattr(expr, "table_options", None)
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
        parts.append(self.format_identifier(expr.table_name))

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
            idx_sql, idx_params = self.format_inline_index(idx_def)
            column_parts.append(idx_sql)
            all_params.extend(idx_params)

        parts.append(f"({', '.join(column_parts)})")

        if expr.storage_options:
            storage_sql = self._format_storage_options(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        if 'comment' in expr.dialect_options:
            escaped_comment = self._escape_sql_string(expr.dialect_options['comment'])
            parts.append(f"COMMENT '{escaped_comment}'")

        return ' '.join(parts), tuple(all_params)

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        value = value.replace('\\', '\\\\')
        value = value.replace("'", "''")
        return value

    def format_column_definition(
        self,
        col_def: "ColumnDefinition"
    ) -> Tuple[str, tuple]:
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType

        type_sql, type_params = col_def.data_type.to_sql()
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
        t_const: "TableConstraint"
    ) -> Tuple[str, tuple]:
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

    # endregion
