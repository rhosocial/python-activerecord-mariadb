# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_create_table_expression_diff.py
"""
CreateTableExpression.diff() coverage for the MariaDB dialect.

The generic ``CreateTableExpressionDiffMixin`` lives in the core library and is
composed into ``SQLDialectBase``; MariaDB overrides two hooks to unlock
in-place column type changes (``MODIFY COLUMN``):

- ``_supports_alter_column_type()`` → True
- ``alter_column_type_action()`` → ``ModifyColumn(self, column=new_col)``

These tests are pure expression-level (no live server needed) and pin:
- DiffPlan/RebuildPlan shapes for MariaDB
- rendered ``to_sql()`` text for ALTER TABLE actions
"""

import pytest

from rhosocial.activerecord.backend.expression import DiffPlan, RebuildPlan
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumn,
    AddIndex,
    AlterColumn,
    ColumnAlterOperation,
    DropColumn,
    DropIndex,
    ModifyColumn,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    TextType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _col(name, dtype, *constraints):
    return ColumnDefinition(name=name, data_type=dtype, constraints=list(constraints))


def _pk():
    return ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY)


def _not_null():
    return ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL)


def _expr(dialect, columns, indexes=None, constraints=None, **kwargs):
    return CreateTableExpression(
        dialect=dialect,
        table=kwargs.pop("table", "items"),
        columns=columns,
        indexes=indexes,
        table_constraints=constraints,
        **kwargs,
    )


@pytest.fixture
def dialect():
    return MariaDBDialect("11.4.0")


# ---------------------------------------------------------------------------
# Protocol conformance / capability hooks
# ---------------------------------------------------------------------------

class TestProtocolConformance:
    """MariaDB capability hooks: in-place type changes (MODIFY COLUMN) and
    ALTER TABLE ADD/DROP INDEX stay on the alter path."""

    def test_supports_alter_column_type(self, dialect):
        assert dialect._supports_alter_column_type() is True

    def test_alter_column_type_action_returns_modify_column(self, dialect):
        old_col = _col("code", IntegerType())
        new_col = _col("code", VarCharType(length=100))
        action = dialect.alter_column_type_action(old_col, new_col)
        assert isinstance(action, ModifyColumn)
        assert action.column is new_col

    def test_supports_alter_table_index_actions(self, dialect):
        assert dialect._supports_alter_table_index_actions() is True

    def test_supports_alter_column_properties(self, dialect):
        assert dialect._supports_alter_column_properties() is True


# ---------------------------------------------------------------------------
# No change
# ---------------------------------------------------------------------------

class TestNoChange:

    def test_identical_definitions_empty_plan(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("name", TextType())])
        new = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("name", TextType())])
        plan = old.diff(new)
        assert not plan.has_changes
        assert plan.rebuild is None
        assert plan.alters == []


# ---------------------------------------------------------------------------
# Column add / drop
# ---------------------------------------------------------------------------

class TestColumnChanges:

    def test_added_column_yields_add_action(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk())])
        new = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("bio", TextType())])
        plan = old.diff(new)
        assert plan.rebuild is None and plan.has_changes
        (alter,) = plan.alters
        assert len(alter.actions) == 1
        action = alter.actions[0]
        assert isinstance(action, AddColumn)
        assert action.column.name == "bio"
        sql, _ = alter.to_sql()
        assert "ADD COLUMN" in sql
        assert "`bio`" in sql

    def test_removed_column_yields_drop_action(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("bio", TextType())])
        new = _expr(dialect, [_col("id", IntegerType(), _pk())])
        plan = old.diff(new)
        (alter,) = plan.alters
        action = alter.actions[0]
        assert isinstance(action, DropColumn)
        assert action.column_name == "bio"
        sql, _ = alter.to_sql()
        assert "DROP COLUMN" in sql
        assert "`bio`" in sql


# ---------------------------------------------------------------------------
# Column type change → MODIFY COLUMN (MariaDB override)
# ---------------------------------------------------------------------------

class TestTypeChangeRebuild:
    """Type changes stay in place on MariaDB (MODIFY COLUMN)."""

    def test_type_change_yields_modify_column(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("code", IntegerType())])
        new = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("code", VarCharType(length=100))])
        plan = old.diff(new)
        assert plan.rebuild is None
        (alter,) = plan.alters
        action = alter.actions[0]
        assert isinstance(action, ModifyColumn)
        assert action.column.name == "code"

    def test_type_change_renders_modify_column_sql(self, dialect):
        old = _expr(dialect, [_col("code", IntegerType())])
        new = _expr(dialect, [_col("code", VarCharType(length=100))])
        plan = old.diff(new)
        sql, _ = plan.alters[0].to_sql()
        assert "MODIFY COLUMN" in sql
        assert "VARCHAR(100)" in sql

    def test_varchar_length_change_is_in_place(self, dialect):
        old = _expr(dialect, [_col("name", VarCharType(length=50))])
        new = _expr(dialect, [_col("name", VarCharType(length=100))])
        plan = old.diff(new)
        assert plan.rebuild is None
        assert isinstance(plan.alters[0].actions[0], ModifyColumn)


# ---------------------------------------------------------------------------
# Column property changes (default / nullability)
# ---------------------------------------------------------------------------

class TestColumnPropertyChanges:

    def test_set_default(self, dialect):
        old = _expr(dialect, [_col("status", TextType())])
        new = _expr(dialect, [_col(
            "status", TextType(),
            ColumnConstraint(constraint_type=ColumnConstraintType.DEFAULT, default_value="ok"),
        )])
        plan = old.diff(new)
        (action,) = plan.alters[0].actions
        assert isinstance(action, AlterColumn)
        assert action.operation == ColumnAlterOperation.SET_DEFAULT
        assert action.new_value == "ok"
        sql, _ = plan.alters[0].to_sql()
        assert "SET DEFAULT" in sql

    def test_drop_default(self, dialect):
        old = _expr(dialect, [_col(
            "status", TextType(),
            ColumnConstraint(constraint_type=ColumnConstraintType.DEFAULT, default_value="ok"),
        )])
        new = _expr(dialect, [_col("status", TextType())])
        plan = old.diff(new)
        (action,) = plan.alters[0].actions
        assert action.operation == ColumnAlterOperation.DROP_DEFAULT
        sql, _ = plan.alters[0].to_sql()
        assert "DROP DEFAULT" in sql

    def test_set_not_null(self, dialect):
        old = _expr(dialect, [_col("name", TextType())])
        new = _expr(dialect, [_col("name", TextType(), _not_null())])
        plan = old.diff(new)
        (action,) = plan.alters[0].actions
        assert action.operation == ColumnAlterOperation.SET_NOT_NULL
        sql, _ = plan.alters[0].to_sql()
        assert "SET NOT NULL" in sql

    def test_drop_not_null(self, dialect):
        old = _expr(dialect, [_col("name", TextType(), _not_null())])
        new = _expr(dialect, [_col("name", TextType())])
        plan = old.diff(new)
        (action,) = plan.alters[0].actions
        assert action.operation == ColumnAlterOperation.DROP_NOT_NULL
        sql, _ = plan.alters[0].to_sql()
        assert "DROP NOT NULL" in sql


# ---------------------------------------------------------------------------
# Index changes (ALTER TABLE ADD/DROP INDEX is valid MariaDB syntax)
# ---------------------------------------------------------------------------

class TestIndexChanges:

    def test_added_index(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("code", IntegerType())])
        new = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("code", IntegerType())],
                    indexes=[IndexDefinition(name="idx_code", columns=["code"])])
        plan = old.diff(new)
        assert plan.rebuild is None
        action = plan.alters[0].actions[0]
        assert isinstance(action, AddIndex)
        assert action.index.name == "idx_code"
        sql, _ = plan.alters[0].to_sql()
        assert "ADD INDEX" in sql
        assert "`idx_code`" in sql

    def test_removed_index(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("code", IntegerType())],
                    indexes=[IndexDefinition(name="idx_code", columns=["code"])])
        new = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("code", IntegerType())])
        plan = old.diff(new)
        action = plan.alters[0].actions[0]
        assert isinstance(action, DropIndex)
        sql, _ = plan.alters[0].to_sql()
        assert "DROP INDEX" in sql
        assert "`idx_code`" in sql


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:

    def test_cross_dialect_raises(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk())])
        new = _expr(SQLiteDialect(), [_col("id", IntegerType(), _pk())])
        with pytest.raises(ValueError, match="different dialects"):
            old.diff(new)

    def test_cross_table_raises(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk())])
        new = _expr(dialect, [_col("id", IntegerType(), _pk())], table="other")
        with pytest.raises(ValueError, match="different tables"):
            old.diff(new)


# ---------------------------------------------------------------------------
# Primary key change → rebuild
# ---------------------------------------------------------------------------

class TestTableConstraintChanges:

    def test_pk_change_rebuilds(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType()), _col("code", TextType())],
                    constraints=[TableConstraint(
                        constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"])])
        new = _expr(dialect, [_col("id", IntegerType()), _col("code", TextType())],
                    constraints=[TableConstraint(
                        constraint_type=TableConstraintType.PRIMARY_KEY, columns=["code"])])
        plan = old.diff(new)
        assert plan.alters == []
        rp = plan.rebuild
        assert isinstance(rp, RebuildPlan)
        assert "primary key" in rp.reason

    def test_rebuild_plan_renders_sql(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType())],
                    constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"])])
        new = _expr(dialect, [_col("code", TextType())],
                    constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["code"])])
        rp = old.diff(new).rebuild
        create_sql, _ = rp.create.to_sql()
        drop_sql, _ = rp.drop_old.to_sql()
        rename_sql, _ = rp.rename.to_sql()
        assert "CREATE TABLE" in create_sql.upper()
        assert "DROP TABLE" in drop_sql.upper()
        assert "RENAME" in rename_sql.upper()

    def test_rebuild_plan_shape(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType())],
                    constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"])])
        new = _expr(dialect, [_col("code", TextType())],
                    constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["code"])])
        rp = old.diff(new).rebuild
        assert rp.create.table_name == "items__rebuild__"
        assert rp.drop_old.table.name == "items"
        assert rp.rename.table == "items__rebuild__"
        assert rp.copy_columns == []


# ---------------------------------------------------------------------------
# DiffPlan invariants
# ---------------------------------------------------------------------------

class TestDiffPlanInvariants:

    def test_alters_and_rebuild_mutually_exclusive(self, dialect):
        old = _expr(dialect, [_col("id", IntegerType(), _pk())])
        new = _expr(dialect, [_col("id", IntegerType(), _pk()), _col("x", TextType())])
        plan = old.diff(new)
        assert plan.rebuild is None and plan.alters
        old2 = _expr(dialect, [_col("id", IntegerType())],
                     constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"])])
        new2 = _expr(dialect, [_col("code", TextType())],
                     constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["code"])])
        plan2 = old2.diff(new2)
        assert plan2.rebuild is not None and plan2.alters == []

    def test_plan_rejects_both_fields(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AlterTableExpression
        old = _expr(dialect, [_col("id", IntegerType())],
                    constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"])])
        new = _expr(dialect, [_col("code", TextType())],
                    constraints=[TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["code"])])
        rp = old.diff(new).rebuild
        assert rp is not None
        alter = AlterTableExpression(dialect, table="t", actions=[])
        with pytest.raises(ValueError, match="mutually exclusive"):
            DiffPlan(alters=[alter], rebuild=rp)
