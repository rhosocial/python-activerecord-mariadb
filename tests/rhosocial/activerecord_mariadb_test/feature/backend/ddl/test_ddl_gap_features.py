# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_ddl_gap_features.py
"""
MariaDB DDL coverage-gap features tests.

This module tests MariaDB-specific DDL features that fill coverage gaps in the
backend implementation:
- RENAME TABLE (multi-table, IF EXISTS, WAIT/NOWAIT)
- TRUNCATE TABLE (WAIT/NOWAIT, RESTART IDENTITY / CASCADE rejection)
- Statement-level ALTER TABLE IF EXISTS and WAIT/NOWAIT
- ALTER TABLE ... RENAME INDEX
"""
import pytest
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumn,
    AlterTableExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import ColumnDefinition
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import TruncateExpression
from rhosocial.activerecord.backend.expression.types import TextType
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.rename_index import (
    MariaDBRenameIndexExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.admin import (
    AccountSpec,
    GrantPrivilege,
    MariaDBAlterUserExpression,
    MariaDBCreateRoleExpression,
    MariaDBCreateUserExpression,
    MariaDBDenyExpression,
    MariaDBDropRoleExpression,
    MariaDBDropUserExpression,
    MariaDBFlushExpression,
    MariaDBGrantExpression,
    MariaDBKillExpression,
    MariaDBRevokeExpression,
    MariaDBShutdownExpression,
    FlushOption,
    KillTarget,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.maintenance import (
    MariaDBTableMaintenanceExpression,
    TableMaintenanceOperation,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.routine import (
    MariaDBCallExpression,
    MariaDBCreateFunctionExpression,
    MariaDBCreateProcedureExpression,
    MariaDBDropFunctionExpression,
    MariaDBDropProcedureExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.rename_table import (
    MariaDBRenameTableExpression,
)


def _dialect(version):
    return MariaDBDialect(version=version)


class TestMariaDBRenameTable:
    """Tests for MariaDB RENAME TABLE."""

    def test_single_rename(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRenameTableExpression(
            dialect, [('old_table', 'new_table')]
        )
        sql, params = expr.to_sql()
        assert sql == 'RENAME TABLE `old_table` TO `new_table`'
        assert params == ()

    def test_multi_table_rename(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRenameTableExpression(
            dialect, [('t1', 't2'), ('t3', 't4')]
        )
        sql, params = expr.to_sql()
        assert sql == 'RENAME TABLE `t1` TO `t2`, `t3` TO `t4`'

    def test_supports_multi_table_rename(self):
        assert _dialect((10, 6, 0)).supports_multi_table_rename() is True

    def test_if_exists_supported_on_10_5(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRenameTableExpression(
            dialect, [('old_table', 'new_table')],
            dialect_options={'if_exists': True},
        )
        sql, params = expr.to_sql()
        assert sql == 'RENAME TABLE IF EXISTS `old_table` TO `new_table`'

    def test_if_exists_version_gated(self):
        dialect = _dialect((10, 4, 0))
        expr = MariaDBRenameTableExpression(
            dialect, [('old_table', 'new_table')],
            dialect_options={'if_exists': True},
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_wait_option(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRenameTableExpression(
            dialect, [('old_table', 'new_table')],
            dialect_options={'wait': 5},
        )
        sql, params = expr.to_sql()
        assert sql == 'RENAME TABLE `old_table` WAIT 5 TO `new_table`'

    def test_nowait_option(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRenameTableExpression(
            dialect, [('old_table', 'new_table')],
            dialect_options={'nowait': True},
        )
        sql, params = expr.to_sql()
        assert sql == 'RENAME TABLE `old_table` NOWAIT TO `new_table`'

    def test_wait_version_gated(self):
        dialect = _dialect((10, 2, 0))
        expr = MariaDBRenameTableExpression(
            dialect, [('old_table', 'new_table')],
            dialect_options={'nowait': True},
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_invalid_pair_raises(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRenameTableExpression(dialect, [])
        with pytest.raises(ValueError):
            expr.validate()


class TestMariaDBTruncate:
    """Tests for MariaDB TRUNCATE TABLE."""

    def test_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = TruncateExpression(dialect, table='users')
        sql, params = expr.to_sql()
        assert sql == 'TRUNCATE TABLE `users`'
        assert params == ()

    def test_wait_option(self):
        dialect = _dialect((10, 6, 0))
        expr = TruncateExpression(dialect, table='users',
                                  dialect_options={'wait': 3})
        sql, params = expr.to_sql()
        assert sql == 'TRUNCATE TABLE `users` WAIT 3'

    def test_nowait_option(self):
        dialect = _dialect((10, 6, 0))
        expr = TruncateExpression(dialect, table='users',
                                  dialect_options={'nowait': True})
        sql, params = expr.to_sql()
        assert sql == 'TRUNCATE TABLE `users` NOWAIT'

    def test_wait_version_gated(self):
        dialect = _dialect((10, 2, 0))
        expr = TruncateExpression(dialect, table='users',
                                  dialect_options={'nowait': True})
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_restart_identity_rejected(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_truncate_restart_identity() is False
        expr = TruncateExpression(dialect, table='users',
                                  restart_identity=True)
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_cascade_rejected(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_truncate_cascade() is False
        expr = TruncateExpression(dialect, table='users', cascade=True)
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()


class TestMariaDBAlterTableStatement:
    """Tests for MariaDB statement-level ALTER TABLE qualifiers."""

    def _add_column_action(self, dialect):
        return AddColumn(
            dialect, column=ColumnDefinition('email', TextType())
        )

    def test_basic_alter(self):
        dialect = _dialect((10, 6, 0))
        expr = AlterTableExpression(
            dialect, 'users', [self._add_column_action(dialect)]
        )
        sql, params = expr.to_sql()
        assert 'ALTER TABLE `users`' in sql
        assert 'ADD COLUMN `email`' in sql

    def test_alter_if_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = AlterTableExpression(
            dialect, 'users', [self._add_column_action(dialect)],
            dialect_options={'if_exists': True},
        )
        sql, params = expr.to_sql()
        assert sql.startswith('ALTER TABLE IF EXISTS `users`')
        assert 'ADD COLUMN `email`' in sql

    def test_alter_if_exists_version_gated(self):
        dialect = _dialect((10, 4, 0))
        assert dialect.supports_alter_table_if_exists() is False
        expr = AlterTableExpression(
            dialect, 'users', [self._add_column_action(dialect)],
            dialect_options={'if_exists': True},
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_alter_wait(self):
        dialect = _dialect((10, 6, 0))
        expr = AlterTableExpression(
            dialect, 'users', [self._add_column_action(dialect)],
            dialect_options={'wait': 4},
        )
        sql, params = expr.to_sql()
        assert 'ALTER TABLE `users` WAIT 4' in sql
        assert 'ADD COLUMN `email`' in sql

    def test_alter_if_exists_nowait(self):
        dialect = _dialect((10, 6, 0))
        expr = AlterTableExpression(
            dialect, 'users', [self._add_column_action(dialect)],
            dialect_options={'if_exists': True, 'nowait': True},
        )
        sql, params = expr.to_sql()
        assert 'ALTER TABLE IF EXISTS `users` NOWAIT' in sql
        assert 'ADD COLUMN `email`' in sql


class TestMariaDBRenameIndex:
    """Tests for MariaDB ALTER TABLE ... RENAME INDEX."""

    def test_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRenameIndexExpression(
            dialect, 'users', 'idx_old', 'idx_new'
        )
        sql, params = expr.to_sql()
        assert sql == 'ALTER TABLE `users` RENAME INDEX `idx_old` TO `idx_new`'
        assert params == ()

    def test_supports_rename_index_on_10_5_3(self):
        dialect = _dialect((10, 5, 3))
        assert dialect.supports_rename_index() is True

    def test_version_gated_below_10_5_3(self):
        dialect = _dialect((10, 5, 2))
        assert dialect.supports_rename_index() is False
        expr = MariaDBRenameIndexExpression(
            dialect, 'users', 'idx_old', 'idx_new'
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()


class TestMariaDBTableMaintenance:
    """Tests for MariaDB table maintenance statements."""

    def _expr(self, dialect, operation, tables, **options):
        return MariaDBTableMaintenanceExpression(
            dialect, operation, tables,
            dialect_options=options,
        )

    def test_analyze_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(dialect, TableMaintenanceOperation.ANALYZE, ['users'])
        sql, params = expr.to_sql()
        assert sql == 'ANALYZE TABLE `users`'
        assert params == ()

    def test_analyze_multi_table(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.ANALYZE, ['a', 'b']
        )
        sql, params = expr.to_sql()
        assert sql == 'ANALYZE TABLE `a`, `b`'

    def test_analyze_no_write_to_binlog(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.ANALYZE, ['users'],
            no_write_to_binlog=True,
        )
        sql, params = expr.to_sql()
        assert sql == 'ANALYZE NO_WRITE_TO_BINLOG TABLE `users`'

    def test_analyze_local(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.ANALYZE, ['users'], local=True
        )
        sql, params = expr.to_sql()
        assert sql == 'ANALYZE NO_WRITE_TO_BINLOG TABLE `users`'

    def test_analyze_persistent_all(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.ANALYZE, ['users'],
            persistent='all',
        )
        sql, params = expr.to_sql()
        assert sql == 'ANALYZE TABLE `users` PERSISTENT FOR ALL'

    def test_analyze_persistent_columns(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.ANALYZE, ['users'],
            persistent={'columns': ['name', 'email']},
        )
        sql, params = expr.to_sql()
        assert sql == 'ANALYZE TABLE `users` PERSISTENT FOR COLUMNS (`name`, `email`)'

    def test_analyze_persistent_indexes(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.ANALYZE, ['users'],
            persistent={'indexes': ['idx_name']},
        )
        sql, params = expr.to_sql()
        assert sql == 'ANALYZE TABLE `users` PERSISTENT FOR INDEXES (`idx_name`)'

    def test_analyze_persistent_version_gated(self):
        dialect = _dialect((10, 4, 0))
        assert dialect.supports_analyze_table_persistent() is False
        expr = self._expr(
            dialect, TableMaintenanceOperation.ANALYZE, ['users'],
            persistent='all',
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_check_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(dialect, TableMaintenanceOperation.CHECK, ['users'])
        sql, params = expr.to_sql()
        assert sql == 'CHECK TABLE `users`'

    def test_check_quick_extended(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.CHECK, ['users'],
            check_mode=['QUICK', 'EXTENDED'],
        )
        sql, params = expr.to_sql()
        assert sql == 'CHECK TABLE `users` QUICK EXTENDED'

    def test_check_for_upgrade(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.CHECK, ['users'],
            check_mode=['FOR UPGRADE'],
        )
        sql, params = expr.to_sql()
        assert sql == 'CHECK TABLE `users` FOR UPGRADE'

    def test_checksum_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.CHECKSUM, ['users']
        )
        sql, params = expr.to_sql()
        assert sql == 'CHECKSUM TABLE `users`'

    def test_checksum_quick(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.CHECKSUM, ['users'],
            checksum_mode='quick',
        )
        sql, params = expr.to_sql()
        assert sql == 'CHECKSUM TABLE `users` QUICK'

    def test_optimize_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.OPTIMIZE, ['users']
        )
        sql, params = expr.to_sql()
        assert sql == 'OPTIMIZE TABLE `users`'

    def test_optimize_no_binlog(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.OPTIMIZE, ['users'],
            no_write_to_binlog=True,
        )
        sql, params = expr.to_sql()
        assert sql == 'OPTIMIZE NO_WRITE_TO_BINLOG TABLE `users`'

    def test_repair_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.REPAIR, ['users']
        )
        sql, params = expr.to_sql()
        assert sql == 'REPAIR TABLE `users`'

    def test_repair_modes(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.REPAIR, ['users'],
            repair_mode=['QUICK', 'EXTENDED'],
        )
        sql, params = expr.to_sql()
        assert sql == 'REPAIR TABLE `users` QUICK EXTENDED'

    def test_repair_use_frm(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(
            dialect, TableMaintenanceOperation.REPAIR, ['users'],
            repair_mode=['USE_FRM'],
        )
        sql, params = expr.to_sql()
        assert sql == 'REPAIR TABLE `users` USE_FRM'

    def test_invalid_no_tables(self):
        dialect = _dialect((10, 6, 0))
        expr = self._expr(dialect, TableMaintenanceOperation.ANALYZE, [])
        with pytest.raises(ValueError):
            expr.validate()

    def test_supports_flags(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_analyze_table() is True
        assert dialect.supports_check_table() is True
        assert dialect.supports_checksum_table() is True
        assert dialect.supports_optimize_table() is True
        assert dialect.supports_repair_table() is True


class TestMariaDBRoutine:
    """Tests for MariaDB stored routines."""

    def test_create_procedure_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateProcedureExpression(
            dialect, 'get_user', body='BEGIN SELECT * FROM users; END'
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE PROCEDURE `get_user` () BEGIN SELECT * FROM users; END'
        assert params == ()

    def test_create_procedure_params(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateProcedureExpression(
            dialect, 'get_user',
            params=[('IN', 'uid', 'INT'), ('OUT', 'name', 'VARCHAR(50)')],
            body='BEGIN SELECT name INTO name FROM users WHERE id = uid; END',
        )
        sql, params = expr.to_sql()
        assert sql == (
            'CREATE PROCEDURE `get_user` (IN `uid` INT, OUT `name` VARCHAR(50))'
            ' BEGIN SELECT name INTO name FROM users WHERE id = uid; END'
        )

    def test_create_procedure_or_replace(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateProcedureExpression(
            dialect, 'get_user', or_replace=True, body='BEGIN END'
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE OR REPLACE PROCEDURE `get_user` () BEGIN END'

    def test_create_procedure_if_not_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateProcedureExpression(
            dialect, 'get_user', if_not_exists=True, body='BEGIN END'
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE IF NOT EXISTS PROCEDURE `get_user` () BEGIN END'

    def test_create_procedure_or_replace_version_gated(self):
        dialect = _dialect((10, 1, 2))
        assert dialect.supports_routine_or_replace() is False
        expr = MariaDBCreateProcedureExpression(
            dialect, 'get_user', or_replace=True, body='BEGIN END'
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_procedure_if_not_exists_version_gated(self):
        dialect = _dialect((10, 1, 2))
        assert dialect.supports_routine_if_not_exists() is False
        expr = MariaDBCreateProcedureExpression(
            dialect, 'get_user', if_not_exists=True, body='BEGIN END'
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_procedure_schema_qualified(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateProcedureExpression(
            dialect, ('app', 'get_user'), body='BEGIN END'
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE PROCEDURE `app`.`get_user` () BEGIN END'

    def test_drop_procedure(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBDropProcedureExpression(dialect, 'get_user')
        sql, params = expr.to_sql()
        assert sql == 'DROP PROCEDURE `get_user`'

    def test_drop_procedure_if_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBDropProcedureExpression(dialect, 'get_user', if_exists=True)
        sql, params = expr.to_sql()
        assert sql == 'DROP PROCEDURE IF EXISTS `get_user`'

    def test_create_function_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateFunctionExpression(
            dialect, 'add_one', returns='INT',
            params=[('IN', 'x', 'INT')],
            body='RETURN x + 1;',
        )
        sql, params = expr.to_sql()
        assert sql == (
            'CREATE FUNCTION `add_one` (IN `x` INT) RETURNS INT'
            ' RETURN x + 1;'
        )

    def test_create_function_deterministic(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateFunctionExpression(
            dialect, 'add_one', returns='INT', deterministic=True,
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE FUNCTION `add_one` () RETURNS INT DETERMINISTIC'

    def test_create_aggregate_function(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_aggregate_function() is True
        expr = MariaDBCreateFunctionExpression(
            dialect, 'my_sum', returns='INT', aggregate=True,
            body='...',
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE AGGREGATE FUNCTION `my_sum` () RETURNS INT ...'

    def test_drop_function(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBDropFunctionExpression(dialect, 'add_one')
        sql, params = expr.to_sql()
        assert sql == 'DROP FUNCTION `add_one`'

    def test_drop_function_if_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBDropFunctionExpression(dialect, 'add_one', if_exists=True)
        sql, params = expr.to_sql()
        assert sql == 'DROP FUNCTION IF EXISTS `add_one`'

    def test_call_basic(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCallExpression(dialect, 'get_user')
        sql, params = expr.to_sql()
        assert sql == 'CALL `get_user` ()'
        assert params == ()

    def test_call_args(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCallExpression(dialect, 'get_user', args=[1, 'alice'])
        sql, params = expr.to_sql()
        assert sql == 'CALL `get_user` (%s, %s)'
        assert params == (1, 'alice')

    def test_call_schema_qualified(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCallExpression(dialect, ('app', 'get_user'), args=[])
        sql, params = expr.to_sql()
        assert sql == 'CALL `app`.`get_user` ()'

    def test_supports_flags(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_procedure() is True
        assert dialect.supports_stored_function() is True
        assert dialect.supports_call() is True


class TestMariaDBAdmin:
    """Tests for MariaDB administrative / account management statements."""

    def _user(self):
        return AccountSpec('app_user', 'localhost')

    def _users(self):
        return [AccountSpec('app_user', 'localhost')]

    def test_create_user(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateUserExpression(
            dialect, self._users(), identified_by='secret'
        )
        sql, params = expr.to_sql()
        assert sql == "CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'secret'"

    def test_create_user_if_not_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateUserExpression(
            dialect, self._users(), if_not_exists=True
        )
        sql, params = expr.to_sql()
        assert sql == "CREATE USER IF NOT EXISTS 'app_user'@'localhost'"

    def test_alter_user(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBAlterUserExpression(
            dialect, self._users(), identified_by='newpass'
        )
        sql, params = expr.to_sql()
        assert sql == "ALTER USER 'app_user'@'localhost' IDENTIFIED BY 'newpass'"

    def test_alter_user_if_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBAlterUserExpression(dialect, self._users(), if_exists=True)
        sql, params = expr.to_sql()
        assert sql == "ALTER USER IF EXISTS 'app_user'@'localhost'"

    def test_drop_user(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBDropUserExpression(dialect, self._users())
        sql, params = expr.to_sql()
        assert sql == "DROP USER 'app_user'@'localhost'"

    def test_drop_user_if_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBDropUserExpression(dialect, self._users(), if_exists=True)
        sql, params = expr.to_sql()
        assert sql == "DROP USER IF EXISTS 'app_user'@'localhost'"

    def test_default_host_is_percent(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateUserExpression(
            dialect, [AccountSpec('app_user')]
        )
        sql, params = expr.to_sql()
        assert sql == "CREATE USER 'app_user'@'%'"

    def test_create_role(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateRoleExpression(dialect, ['app_role'])
        sql, params = expr.to_sql()
        assert sql == 'CREATE ROLE `app_role`'

    def test_create_role_if_not_exists_multi(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBCreateRoleExpression(
            dialect, ['a_role', 'b_role'], if_not_exists=True
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE ROLE IF NOT EXISTS `a_role`, `b_role`'

    def test_drop_role(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBDropRoleExpression(dialect, ['app_role'], if_exists=True)
        sql, params = expr.to_sql()
        assert sql == 'DROP ROLE IF EXISTS `app_role`'

    def test_grant(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBGrantExpression(
            dialect,
            [GrantPrivilege('SELECT')],
            self._users(),
            on_object='app.users',
        )
        sql, params = expr.to_sql()
        assert sql == "GRANT SELECT ON app.users TO 'app_user'@'localhost'"

    def test_grant_multi_privilege_with_columns(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBGrantExpression(
            dialect,
            [GrantPrivilege('SELECT', ['id', 'name']), GrantPrivilege('UPDATE')],
            self._users(),
            on_object='app.users',
        )
        sql, params = expr.to_sql()
        assert sql == (
            "GRANT SELECT (`id`, `name`), UPDATE ON app.users"
            " TO 'app_user'@'localhost'"
        )

    def test_grant_with_grant_option(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBGrantExpression(
            dialect,
            [GrantPrivilege('SELECT')],
            self._users(),
            with_grant_option=True,
        )
        sql, params = expr.to_sql()
        assert sql == "GRANT SELECT ON *.* TO 'app_user'@'localhost' WITH GRANT OPTION"

    def test_grant_or_replace(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_grant_or_replace() is True
        expr = MariaDBGrantExpression(
            dialect,
            [GrantPrivilege('SELECT')],
            self._users(),
            or_replace=True,
        )
        sql, params = expr.to_sql()
        assert sql == "GRANT OR REPLACE SELECT ON *.* TO 'app_user'@'localhost'"

    def test_grant_or_replace_version_gated(self):
        dialect = _dialect((10, 1, 3))
        assert dialect.supports_grant_or_replace() is False
        expr = MariaDBGrantExpression(
            dialect,
            [GrantPrivilege('SELECT')],
            self._users(),
            or_replace=True,
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_grant_if_exists(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_grant_if_exists() is True
        expr = MariaDBGrantExpression(
            dialect,
            [GrantPrivilege('SELECT')],
            self._users(),
            if_exists=True,
        )
        sql, params = expr.to_sql()
        assert sql == "GRANT IF EXISTS SELECT ON *.* TO 'app_user'@'localhost'"

    def test_revoke(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRevokeExpression(
            dialect,
            [GrantPrivilege('SELECT')],
            self._users(),
            on_object='app.users',
        )
        sql, params = expr.to_sql()
        assert sql == "REVOKE SELECT ON app.users FROM 'app_user'@'localhost'"

    def test_revoke_if_exists(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBRevokeExpression(
            dialect,
            [GrantPrivilege('SELECT')],
            self._users(),
            if_exists=True,
        )
        sql, params = expr.to_sql()
        assert sql == "REVOKE IF EXISTS SELECT ON *.* FROM 'app_user'@'localhost'"

    def test_deny(self):
        dialect = _dialect((13, 1, 0))
        assert dialect.supports_deny() is True
        expr = MariaDBDenyExpression(
            dialect,
            [GrantPrivilege('DELETE')],
            self._users(),
            on_object='app.users',
        )
        sql, params = expr.to_sql()
        assert sql == "DENY DELETE ON app.users TO 'app_user'@'localhost'"

    def test_deny_version_gated(self):
        dialect = _dialect((13, 0, 0))
        assert dialect.supports_deny() is False
        expr = MariaDBDenyExpression(
            dialect,
            [GrantPrivilege('DELETE')],
            self._users(),
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_flush(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBFlushExpression(dialect, [FlushOption.PRIVILEGES])
        sql, params = expr.to_sql()
        assert sql == 'FLUSH PRIVILEGES'

    def test_flush_multiple_no_binlog(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBFlushExpression(
            dialect, [FlushOption.LOGS, FlushOption.STATUS],
            no_write_to_binlog=True,
        )
        sql, params = expr.to_sql()
        assert sql == 'FLUSH NO_WRITE_TO_BINLOG LOGS, STATUS'

    def test_flush_invalid_empty(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBFlushExpression(dialect, [])
        with pytest.raises(ValueError):
            expr.validate()

    def test_kill_connection(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBKillExpression(dialect, 42)
        sql, params = expr.to_sql()
        assert sql == 'KILL CONNECTION 42'

    def test_kill_query(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBKillExpression(dialect, 42, target=KillTarget.QUERY)
        sql, params = expr.to_sql()
        assert sql == 'KILL QUERY 42'

    def test_shutdown(self):
        dialect = _dialect((10, 6, 0))
        expr = MariaDBShutdownExpression(dialect)
        sql, params = expr.to_sql()
        assert sql == 'SHUTDOWN'

    def test_supports_flags(self):
        dialect = _dialect((10, 6, 0))
        assert dialect.supports_flush() is True
        assert dialect.supports_kill() is True
        assert dialect.supports_shutdown() is True
        assert dialect.supports_create_user() is True
        assert dialect.supports_alter_user() is True
        assert dialect.supports_drop_user() is True
        assert dialect.supports_create_role() is True
        assert dialect.supports_drop_role() is True
        assert dialect.supports_grant() is True
        assert dialect.supports_revoke() is True