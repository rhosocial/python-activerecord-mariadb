# tests/rhosocial/activerecord_mariadb_test/feature/backend/dialect/test_expression_fields_match_formatters.py
"""A formatter may not read a field its statement does not carry.

A statement formatter that reads ``expr.schema_name`` needs the expression to
have that attribute. When the formatter was changed to qualify names and the
expression was not given the field, the result is not wrong SQL -- it is an
``AttributeError`` on a statement that can never be built, which is how
SQLServerColumnstoreIndexExpression reached CI.

These were source scans rather than runtime tests. A scan does not work here:
whether the field exists depends on inheritance reaching core, which lives in
another repository, and on **core_kwargs forwarding. Reading the source of this
repository can see neither, so a scan reported defects that were not there --
two were chased down and both were false alarms -- while a field genuinely
removed still passed. Building the statement answers the question the defect
actually asks: does this statement build, and does the schema reach the SQL?

One known blocker is left in place rather than fixed, so it is written down
here where the next person will meet it: ``format_create_trigger_statement``
reads ``expr.or_replace`` (trigger.py:218) and ``expr.ordering``
(trigger.py:238), and core's ``CreateTriggerExpression`` carries neither. That
path therefore raises ``AttributeError`` before it reaches any schema
qualification, which is why CREATE TRIGGER has no case below. ``DROP TRIGGER``
goes through a separate formatter that reads only ``schema_name``, so it is
covered.
"""
import importlib
import inspect

import pytest

from rhosocial.activerecord.backend.expression.core import TableExpression

#: Statement fields a formatter may read that some expression classes carry
#: under a different name. Reading these by their own name is the defect.
#: TruncateExpression names the field `schema`; the DDL statements name it
#: `schema_name`. No formatter on this backend reads the alias, so nothing here
#: exercises it.
KNOWN_ALIASES = {
    "schema": {"TruncateExpression"},
}


class TestQualifiedStatementsRender:
    """A statement whose formatter qualifies names must build with a schema.

    Checked by building each statement and rendering it, not by scanning
    source. Each case names the statement and how to build it, so adding
    coverage for a newly qualified object type is one entry rather than a new
    mechanism.

    MariaDB quotes with backticks, so the expected SQL below carries
    ```app```.`name` where ``app`` was passed in.
    """

    @pytest.fixture
    def dialect(self):
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

        return MariaDBDialect(version=(11, 4, 0))

    def test_alter_table_inherits_the_field_from_core(self, dialect):
        """The case a source scan got wrong in both directions.

        AlterTableExpression lives in core and assigns schema_name there. A
        scan of this repository sees the formatter reading the field and no
        assignment at all, so it either misses a field that is there or reports
        one that is not, depending on how it resolves the base. Building it
        settles the question.
        """
        from rhosocial.activerecord.backend.expression import (
            AlterTableExpression,
            DropColumn,
        )

        def build(schema_name=None):
            return AlterTableExpression(
                dialect,
                table=TableExpression(dialect, "orders", schema_name=schema_name),
                actions=[DropColumn(dialect, "note")],
            )

        assert build().to_sql()[0] == (
            "ALTER TABLE `orders`  DROP COLUMN `note`"
        ), build().to_sql()[0]
        assert build(schema_name="app").to_sql()[0] == (
            "ALTER TABLE `app`.`orders`  DROP COLUMN `note`"
        )

    def test_alter_table_subclass_qualifies_too(self, dialect):
        """The subclass above inherited the field; this one has to pass it on.

        MariaDBAlterTableExpression adds if_exists/nowait/wait, and its __init__
        signature ends in a keyword-only marker. schema_name sits after that
        marker in core, so forwarding it means naming the parameter here rather
        than letting **kwargs carry it -- and forgetting to did not show up as a
        missing attribute but as an ALTER TABLE that ignored the schema, which is
        the failure mode this whole file exists to catch.
        """
        from rhosocial.activerecord.backend.expression import DropColumn
        from rhosocial.activerecord.backend.impl.mariadb.expression import (
            MariaDBAlterTableExpression,
        )

        def build(schema_name=None):
            return MariaDBAlterTableExpression(
                dialect,
                table=TableExpression(dialect, "orders", schema_name=schema_name),
                actions=[DropColumn(dialect, "note")],
                if_exists=True,
            )

        assert build().to_sql()[0] == (
            "ALTER TABLE IF EXISTS `orders`  DROP COLUMN `note`"
        )
        assert build("app").to_sql()[0] == (
            "ALTER TABLE IF EXISTS `app`.`orders`  DROP COLUMN `note`"
        )

    def test_rename_index_qualifies_the_table_not_the_index(self, dialect):
        """A class defined in this repository, qualified by a formatter here.

        MariaDBRenameIndexExpression carries schema_name itself, and the
        formatter puts it on the table only -- the two index names stay bare,
        because that is what ``ALTER TABLE ... RENAME INDEX`` accepts.
        """
        from rhosocial.activerecord.backend.impl.mariadb.expression.rename_index import (
            MariaDBRenameIndexExpression,
        )

        def build(schema_name=None):
            return MariaDBRenameIndexExpression(
                dialect,
                table_name="orders",
                old_index_name="idx_old",
                new_index_name="idx_new",
                schema_name=schema_name,
            )

        assert build().to_sql()[0] == (
            "ALTER TABLE `orders` RENAME INDEX `idx_old` TO `idx_new`"
        ), build().to_sql()[0]
        assert build(schema_name="app").to_sql()[0] == (
            "ALTER TABLE `app`.`orders` RENAME INDEX `idx_old` TO `idx_new`"
        )

    def test_drop_trigger(self, dialect):
        from rhosocial.activerecord.backend.expression import DropTriggerExpression

        expr = DropTriggerExpression(
            dialect, trigger_name="trg_audit", table_name="orders"
        )
        assert expr.to_sql()[0] == "DROP TRIGGER `trg_audit`", expr.to_sql()[0]
        qualified = DropTriggerExpression(
            dialect, trigger_name="trg_audit", table_name="orders", schema_name="app"
        )
        assert qualified.to_sql()[0] == "DROP TRIGGER `app`.`trg_audit`", (
            qualified.to_sql()[0]
        )

    def test_create_function_takes_the_generic_branch(self, dialect):
        """The routine formatter dispatches on shape, and both branches differ.

        ``MariaDBCreateFunctionExpression`` has ``_format_name`` and takes the
        first branch, which never touches ``schema_name``. Core's
        ``CreateFunctionExpression`` takes the second, which does. Asserting the
        second branch is what keeps the qualifier from quietly going missing
        when the dispatch changes.
        """
        from rhosocial.activerecord.backend.expression import CreateFunctionExpression

        def build(schema_name=None):
            return CreateFunctionExpression(
                dialect,
                function_name="fn_calc",
                parameters=[],
                returns="INT",
                body="RETURN 1;",
                schema_name=schema_name,
            )

        assert build().to_sql()[0] == "CREATE FUNCTION `fn_calc` () RETURNS INT RETURN 1;", (
            build().to_sql()[0]
        )
        assert build(schema_name="app").to_sql()[0] == (
            "CREATE FUNCTION `app`.`fn_calc` () RETURNS INT RETURN 1;"
        )

    def test_drop_function(self, dialect):
        from rhosocial.activerecord.backend.expression import DropFunctionExpression

        expr = DropFunctionExpression(dialect, function_name="fn_calc")
        assert expr.to_sql()[0] == "DROP FUNCTION `fn_calc`", expr.to_sql()[0]
        qualified = DropFunctionExpression(
            dialect, function_name="fn_calc", schema_name="app"
        )
        assert qualified.to_sql()[0] == "DROP FUNCTION `app`.`fn_calc`", (
            qualified.to_sql()[0]
        )
    def test_create_trigger_qualifies_schema(self, dialect):
        """CREATE TRIGGER built on MariaDB's own expression.

        This used to be built on core's CreateTriggerExpression, with the
        formatter reaching for or_replace and ordering through getattr because
        core declares neither. Those options are real on MariaDB, so they now
        live on MariaDBCreateTriggerExpression and the formatter reads them
        directly -- which means the statement has to be built on the MariaDB
        type, and this is that path.

        Schema qualification is asserted here because the old getattr stood
        between the formatter and the code that reaches the schema: it raised on
        every trigger, so nothing after it was ever exercised.
        """
        from rhosocial.activerecord.backend.expression.statements import (
            TriggerEvent,
            TriggerTiming,
        )
        from rhosocial.activerecord.backend.impl.mariadb.expression import (
            MariaDBCreateTriggerExpression,
        )

        def build(schema_name=None):
            return MariaDBCreateTriggerExpression(
                dialect,
                trigger_name="trg_audit",
                table_name="orders",
                timing=TriggerTiming.BEFORE,
                events=[TriggerEvent.INSERT],
                function_name="audit_fn",
                schema_name=schema_name,
            )

        assert "trg_audit" in build().to_sql()[0]

        sql = build("app").to_sql()[0]
        assert "`app`.`trg_audit`" in sql, sql
        assert "`app`.`orders`" in sql, sql


class TestExpressionSignatures:
    """The expressions this backend's formatters qualify must take the field."""

    @pytest.mark.parametrize(
        "import_path,class_name",
        [
            (
                "rhosocial.activerecord.backend.expression.statements.ddl_alter",
                "AlterTableExpression",
            ),
            (
                "rhosocial.activerecord.backend.impl.mariadb.expression.rename_index",
                "MariaDBRenameIndexExpression",
            ),
            (
                "rhosocial.activerecord.backend.expression.statements.ddl_trigger",
                "DropTriggerExpression",
            ),
            (
                "rhosocial.activerecord.backend.expression.statements.ddl_function",
                "CreateFunctionExpression",
            ),
            (
                "rhosocial.activerecord.backend.expression.statements.ddl_function",
                "DropFunctionExpression",
            ),
        ],
    )
    def test_qualified_expression_accepts_schema_name(self, import_path, class_name):
        module = importlib.import_module(import_path)
        cls = getattr(module, class_name)
        params = inspect.signature(cls.__init__).parameters
        assert "schema_name" in params, (
            f"{class_name} is qualified by its formatter, so it needs the "
            f"field; got {list(params)}"
        )
        assert params["schema_name"].default is None, (
            f"{class_name} must default schema_name to None -- None is what "
            f"means unqualified"
        )
