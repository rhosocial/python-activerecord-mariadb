# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_expression_roundtrip_all.py
"""
Functional serialization coverage for every expression class MariaDB can render.

Two packages are in scope:

* ``rhosocial.activerecord.backend.impl.mariadb.expression`` -- this backend's
  own statements.
* ``rhosocial.activerecord.backend.expression`` -- core's statements, rendered
  by the MariaDB dialect.

Core's package is in the matrix because the five backends' own expression
packages do not reach it, and that gap had a cost: a backend formatter reading
a field core had removed months earlier stayed green, because no test rendered
a core statement through a backend dialect at all. Nine of this file's
exemptions are core classes MariaDB has no formatter for; without the core
package in the matrix those absences would be invisible rather than listed.

Why ``to_sql()`` is classified rather than caught
==================================================

This matrix used to call the testsuite's ``sql_consistent``, which wraps the
first render in ``except Exception: return``. Every render failure was therefore
a green tick, and the three SQL comparisons that function performs never ran. A
formatter that had gone stale, a class that could no longer be constructed, and
a dialect feature that is genuinely unsupported were indistinguishable in the
output. The same vacuity is what let a namespace test pass while the formatter
ignored the namespace it claimed to be testing.

Each outcome is now named and asserted:

* **renders** -- all three encodings must restore byte-identical SQL *and*
  byte-identical bind parameters.
* a member of :data:`LEGITIMATE_NON_RENDERS` -- a class that cannot render for a
  reason belonging to its own tree. Each entry pins the exception type *and* a
  message fragment, so a class that starts failing for a different reason fails
  here instead of staying quietly green.
* :class:`UnsupportedFeatureError` from a class *not* named in the dict --
  MariaDB does not model the feature. Asserted as exactly that type, so a
  subclass raised for an unrelated reason is still visible rather than passing.
* **anything else** -- a failure naming the class and the exception.

The dict is read before the :class:`UnsupportedFeatureError` branch, because core
reports a *missing formatter* as ``UnsupportedFeatureError`` as well; see
:func:`assert_sql_roundtrip_classified`.

And what happens when a class cannot be constructed
==================================================

``make_instance(...) is None`` becomes a skip, but only for a class named in
:data:`UNCONSTRUCTIBLE`, and :func:`TestMatrixIntegrity.test_unconstructible_list_is_exact`
pins that tuple in both directions. A class that starts needing an exemption
fails CI instead of turning into a skip, and a stale entry fails too.
"""

import inspect
from typing import Dict

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import graph as graph_mod
from rhosocial.activerecord.backend.expression.advanced_functions import (
    CaseExpression,
    WindowClause,
    WindowDefinition,
    WindowSpecification,
)
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.datetime import (
    TemporalOptionsExpression,
)
from rhosocial.activerecord.backend.expression.objects import (
    Database,
    Domain,
    EdgeTable as EdgeTableObject,
    Function,
    Index,
    MaterializedView,
    NodeTable,
    Procedure,
    PropertyGraph,
    Sequence,
    Schema,
    Table,
    Trigger,
    Type,
    View,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import JoinClause
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionRegistry,
    deserialize,
    deserialize_json,
    deserialize_xml,
    serialize,
    serialize_json,
    serialize_xml,
)
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.statements import (
    ddl_alter,
    ddl_comment,
    ddl_database,
    ddl_domain,
    ddl_function,
    ddl_index,
    ddl_schema,
    ddl_table,
    ddl_trigger,
    ddl_truncate,
    ddl_type,
    ddl_view,
    dml,
)
from rhosocial.activerecord.backend.expression.statements.ddl_database import (
    AlterDatabaseAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_domain import (
    DomainCheckConstraint,
    RenameDomainAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ForeignKeyConstraint,
    IndexDefinition,
    ReferencesClause,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
    TriggerEvent,
    TriggerTiming,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.statements.dml import (
    MergeAction,
    MergeActionType,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    VarCharType,
)
from rhosocial.activerecord.backend.expression.xml import (
    XMLAttribute,
    XMLAttributesExpression,
    XMLConcatExpression,
    XMLForestExpression,
    XMLForestItem,
)
from rhosocial.activerecord.backend.impl.dummy.expression import (
    _DummyTypeAlterAction,
    _DummyTypeDefinition,
)
from rhosocial.activerecord.backend.impl.mariadb.expression import routine as maria_routine
from rhosocial.activerecord.backend.impl.mariadb.expression.dml import (
    MariaDBInsertExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.json import (
    MariaDBJSONArrayExpression,
    MariaDBJSONContainsExpression,
    MariaDBJSONExtractExpression,
    MariaDBJSONObjectExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.match_against import (
    MariaDBMatchAgainstExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBExchangePartitionExpression,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.spatial import (
    MariaDBSTDistanceExpression,
)
from rhosocial.activerecord.testsuite.utils.expression import (
    assert_params_equal,
    collect_expression_classes,
    make_instance,
    register_special_constructor,
)

MARIADB_EXPR_PKG = "rhosocial.activerecord.backend.impl.mariadb.expression"
CORE_EXPR_PKG = "rhosocial.activerecord.backend.expression"


def _collect(package: str) -> Dict[str, type]:
    """Every concrete expression class *package* defines, by fully qualified name.

    Collected by walking the package, not by reading ``ExpressionRegistry``:
    the registry is process-global and *grows* as other test modules import
    their own backends, so reading it would make this matrix's contents depend
    on which files pytest happened to import first. Sibling backends' classes
    would then be rendered with the MariaDB dialect, which is not a meaningful
    thing to assert.

    ``ddl_alter`` exports four aliases of two classes (``AlterConstraint`` and
    ``ValidateConstraint`` each have two spellings). They are the same objects,
    so the first name wins and the matrix does not test a class four times.
    """
    ExpressionRegistry._auto_register_builtins()
    collected = collect_expression_classes(package)
    by_identity: Dict[int, str] = {}
    for fqn, cls in sorted(collected.items()):
        by_identity.setdefault(id(cls), fqn)
    return {
        fqn: cls
        for cls in collected.values()
        if not inspect.isabstract(cls)
        for fqn in [by_identity[id(cls)]]
    }


def _matrix_classes() -> Dict[str, type]:
    """Both packages merged, and registered so deserialization can resolve them.

    Deserialization looks a class up by name in ``ExpressionRegistry``, so a
    class the matrix renders must be findable there or the round-trip resolves
    to the wrong thing.
    """
    merged: Dict[str, type] = {}
    for package in (MARIADB_EXPR_PKG, CORE_EXPR_PKG):
        for fqn, cls in _collect(package).items():
            ExpressionRegistry.register(cls)
            merged[fqn] = cls
    return merged


REGISTERED = _matrix_classes()


# ---------------------------------------------------------------------------
# Special constructors: a real value where the introspective guess is a lie
# ---------------------------------------------------------------------------
#
# ``make_instance`` reads each required parameter's annotation and guesses:
# ``"x"`` for a string, ``[]`` for a list, ``IntegerType()`` for a type. That is
# right for a name and wrong for every parameter that wants a catalogue object --
# a Table, an Index, a Sequence, a PropertyGraph -- because a bare ``"x"`` is
# not one, and the formatter now refuses it by name. It is also wrong for the
# containers that require at least one member (CASE, WINDOW, JOIN, temporal
# options) and for the predicates that must render without bind parameters.
#
# Every registration below replaces a guess that would otherwise have produced an
# instance the dialect cannot render. Suffixes are spelled relative to the
# expression package because ``make_instance`` matches with ``str.endswith`` and
# several modules export identically named classes.


def _table_obj(dialect, name="t"):
    """A table with a bare name and no namespace."""
    return Table(dialect, name)


def _column_predicate(dialect):
    """A predicate comparing two columns, so it renders with no bind parameters."""
    return ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))


def _one_column_query(dialect):
    """A single-column ``SELECT`` over a table."""
    return QueryExpression(
        dialect, select=[Column(dialect, "id")], from_=_table_obj(dialect)
    )


def _integer_column(dialect, name="col"):
    """A column definition carrying a *dialect-bound* type.

    The binding is load-bearing, not cosmetic: ``to_sql()`` dispatches on the
    type through its own dialect, so an unbound ``IntegerType()`` raises
    ``ValueError: ... has no dialect bound`` the moment anything renders it.
    """
    return ddl_table.ColumnDefinition(dialect, name, IntegerType(dialect))


def register_specials():
    """Replace every introspective guess that would cost a real assertion."""
    # -- the FROM side ------------------------------------------------------
    register_special_constructor(
        "sources.relation.NamedRelationRef",
        lambda d: NamedRelationRef(d, _table_obj(d)),
    )
    register_special_constructor(
        "query_parts.JoinClause",
        lambda d: JoinClause(
            d,
            left_table=NamedRelationRef(d, _table_obj(d)),
            right_table=NamedRelationRef(d, Table(d, "other")),
            condition=_column_predicate(d),
        ),
    )

    # -- tables -------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_table.CreateTableExpression",
        lambda d: ddl_table.CreateTableExpression(d, _table_obj(d), [_integer_column(d)]),
    )
    register_special_constructor(
        "statements.ddl_table.DropTableExpression",
        lambda d: ddl_table.DropTableExpression(d, _table_obj(d)),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableLikeExpression",
        lambda d: ddl_table.CreateTableLikeExpression(
            d, _table_obj(d), Table(d, "other")
        ),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableCloneExpression",
        lambda d: ddl_table.CreateTableCloneExpression(
            d, _table_obj(d), Table(d, "other")
        ),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableAsExpression",
        lambda d: ddl_table.CreateTableAsExpression(d, _table_obj(d), _one_column_query(d)),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableFromTemplateExpression",
        lambda d: ddl_table.CreateTableFromTemplateExpression(
            d, _table_obj(d), _one_column_query(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_truncate.TruncateExpression",
        lambda d: ddl_truncate.TruncateExpression(d, _table_obj(d)),
    )
    # Overrides the shared testsuite factory, which binds no dialect to its type.
    register_special_constructor(
        "statements.ddl_table.ColumnDefinition", _integer_column
    )

    # -- indexes ------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_index.CreateIndexExpression",
        lambda d: ddl_index.CreateIndexExpression(
            d, index=Index(d, "i"), table=_table_obj(d), columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_index.DropIndexExpression",
        lambda d: ddl_index.DropIndexExpression(d, index=Index(d, "i")),
    )
    register_special_constructor(
        "statements.ddl_index.CreateFulltextIndexExpression",
        lambda d: ddl_index.CreateFulltextIndexExpression(
            d, index=Index(d, "i"), table=_table_obj(d), columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_index.DropFulltextIndexExpression",
        lambda d: ddl_index.DropFulltextIndexExpression(
            d, index=Index(d, "i"), table=_table_obj(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_alter.DropIndex",
        lambda d: ddl_alter.DropIndex(d, Index(d, "i")),
    )
    register_special_constructor(
        "statements.ddl_alter.AddColumn",
        lambda d: ddl_alter.AddColumn(d, _integer_column(d)),
    )
    register_special_constructor(
        "statements.ddl_alter.ModifyColumn",
        lambda d: ddl_alter.ModifyColumn(d, _integer_column(d)),
    )
    # CHANGE needs both the old name and the new definition.
    register_special_constructor(
        "statements.ddl_alter.ChangeColumn",
        lambda d: ddl_alter.ChangeColumn(d, "old_col", _integer_column(d)),
    )
    register_special_constructor(
        "statements.ddl_alter.AddIndex",
        lambda d: ddl_alter.AddIndex(d, IndexDefinition(d, "i", ["a"])),
    )
    register_special_constructor(
        "statements.ddl_alter.AddTableConstraint",
        lambda d: ddl_alter.AddTableConstraint(
            d,
            TableConstraint(
                d, TableConstraintType.PRIMARY_KEY, name="c", columns=["a"]
            ),
        ),
    )

    # -- databases, schemas, domains, types --------------------------------
    register_special_constructor(
        "statements.ddl_database.CreateDatabaseExpression",
        lambda d: ddl_database.CreateDatabaseExpression(d, Database(d, "db")),
    )
    register_special_constructor(
        "statements.ddl_database.DropDatabaseExpression",
        lambda d: ddl_database.DropDatabaseExpression(d, Database(d, "db")),
    )
    register_special_constructor(
        "statements.ddl_database.AlterDatabaseExpression",
        lambda d: ddl_database.AlterDatabaseExpression(
            d,
            Database(d, "db"),
            action=AlterDatabaseAction.RENAME_TO,
            target="renamed_db",
        ),
    )
    register_special_constructor(
        "statements.ddl_schema.CreateSchemaExpression",
        lambda d: ddl_schema.CreateSchemaExpression(d, Schema(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_schema.DropSchemaExpression",
        lambda d: ddl_schema.DropSchemaExpression(d, Schema(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_domain.CreateDomainExpression",
        lambda d: ddl_domain.CreateDomainExpression(d, Domain(d, "dom"), IntegerType(d)),
    )
    register_special_constructor(
        "statements.ddl_domain.DropDomainExpression",
        lambda d: ddl_domain.DropDomainExpression(d, Domain(d, "dom")),
    )
    register_special_constructor(
        "statements.ddl_domain.AlterDomainExpression",
        lambda d: ddl_domain.AlterDomainExpression(
            d, Domain(d, "dom"), [RenameDomainAction(d, "other")]
        ),
    )
    # A DOMAIN CHECK is DDL: it must render without bind parameters, so its
    # condition compares two columns rather than a column and a literal.
    register_special_constructor(
        "statements.ddl_domain.DomainCheckConstraint",
        lambda d: DomainCheckConstraint(d, _column_predicate(d), name="chk"),
    )
    # `_DummyTypeDefinition` is the type body every core CREATE TYPE needs, and
    # its body is a type, which must be bound to a dialect.
    register_special_constructor(
        "dummy.expression._DummyTypeDefinition",
        lambda d: _DummyTypeDefinition(d, IntegerType(d)),
    )
    register_special_constructor(
        "statements.ddl_type.CreateTypeExpression",
        lambda d: ddl_type.CreateTypeExpression(
            d, type=Type(d, "t"), definition=_DummyTypeDefinition(d, IntegerType(d))
        ),
    )
    register_special_constructor(
        "statements.ddl_type.AlterTypeExpression",
        lambda d: ddl_type.AlterTypeExpression(
            d, type=Type(d, "t"), actions=[_DummyTypeAlterAction(d, new_name="u")]
        ),
    )
    register_special_constructor(
        "statements.ddl_type.DropTypeExpression",
        lambda d: ddl_type.DropTypeExpression(d, type=Type(d, "t")),
    )

    # -- routines, triggers, comments --------------------------------------
    register_special_constructor(
        "statements.ddl_function.CreateFunctionExpression",
        lambda d: ddl_function.CreateFunctionExpression(
            d, Function(d, "fn"), returns="integer", body="SELECT 1"
        ),
    )
    register_special_constructor(
        "statements.ddl_function.DropFunctionExpression",
        lambda d: ddl_function.DropFunctionExpression(d, Function(d, "fn")),
    )
    register_special_constructor(
        "statements.ddl_trigger.CreateTriggerExpression",
        lambda d: ddl_trigger.CreateTriggerExpression(
            d,
            trigger=Trigger(d, "trg"),
            table=_table_obj(d),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT],
            function=Function(d, "fn"),
        ),
    )
    register_special_constructor(
        "statements.ddl_trigger.DropTriggerExpression",
        lambda d: ddl_trigger.DropTriggerExpression(d, trigger=Trigger(d, "trg")),
    )
    register_special_constructor(
        "statements.ddl_comment.CommentOnExpression",
        lambda d: ddl_comment.CommentOnExpression(d, "table", _table_obj(d), comment="c"),
    )

    # -- views --------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_view.DropViewExpression",
        lambda d: ddl_view.DropViewExpression(d, View(d, "v")),
    )
    register_special_constructor(
        "statements.ddl_view.CreateMaterializedViewExpression",
        lambda d: ddl_view.CreateMaterializedViewExpression(
            d, MaterializedView(d, "mv"), _one_column_query(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_view.DropMaterializedViewExpression",
        lambda d: ddl_view.DropMaterializedViewExpression(d, MaterializedView(d, "mv")),
    )
    register_special_constructor(
        "statements.ddl_view.RefreshMaterializedViewExpression",
        lambda d: ddl_view.RefreshMaterializedViewExpression(
            d, MaterializedView(d, "mv")
        ),
    )

    # -- DML ----------------------------------------------------------------
    register_special_constructor(
        "statements.dml.InsertExpression",
        lambda d: dml.InsertExpression(
            d, into=_table_obj(d), source=ValuesSource(d, [[Literal(d, 1)]])
        ),
    )
    register_special_constructor(
        "statements.dml.DeleteExpression",
        lambda d: dml.DeleteExpression(d, _table_obj(d)),
    )
    register_special_constructor(
        "statements.dml.MergeExpression",
        lambda d: dml.MergeExpression(
            d,
            target_table=_table_obj(d),
            source=NamedRelationRef(d, Table(d, "src")),
            on_condition=_column_predicate(d),
            when_matched=[
                MergeAction(
                    d,
                    MergeActionType.UPDATE,
                    {"a": Literal(d, 1)},
                    _column_predicate(d),
                    "matched",
                )
            ],
        ),
    )
    register_special_constructor(
        "statements.dml.MergeAction",
        lambda d: MergeAction(
            d,
            MergeActionType.UPDATE,
            {"a": Literal(d, 1)},
            _column_predicate(d),
            "matched",
        ),
    )

    # -- constraints and column pieces --------------------------------------
    register_special_constructor(
        "statements.ddl_table.ColumnConstraint",
        lambda d: ColumnConstraint(d, ColumnConstraintType.NOT_NULL, name="c"),
    )
    register_special_constructor(
        "statements.ddl_table.TableConstraint",
        lambda d: TableConstraint(
            d, TableConstraintType.PRIMARY_KEY, name="c", columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_table.ForeignKeyConstraint",
        lambda d: ForeignKeyConstraint(
            d,
            columns=["a"],
            foreign_key_table=Table(d, "other"),
            foreign_key_columns=["b"],
            name="fk",
        ),
    )
    register_special_constructor(
        "statements.ddl_table.ReferencesClause",
        lambda d: ReferencesClause(d, Table(d, "other"), ["b"]),
    )

    # -- expressions that need at least one member --------------------------
    register_special_constructor(
        "advanced_functions.CaseExpression",
        lambda d: CaseExpression(
            d,
            cases=[(_column_predicate(d), Literal(d, 1))],
            else_result=Literal(d, 0),
        ),
    )
    register_special_constructor(
        "advanced_functions.WindowSpecification",
        lambda d: WindowSpecification(d, partition_by=["a"]),
    )
    register_special_constructor(
        "advanced_functions.WindowDefinition",
        lambda d: WindowDefinition(d, "w", WindowSpecification(d, partition_by=["a"])),
    )
    register_special_constructor(
        "advanced_functions.WindowClause",
        lambda d: WindowClause(
            d, [WindowDefinition(d, "w", WindowSpecification(d, partition_by=["a"]))]
        ),
    )
    # An empty options dict is refused by the formatter, so a time-travel clause
    # needs an actual option.
    register_special_constructor(
        "datetime.TemporalOptionsExpression",
        lambda d: TemporalOptionsExpression(d, {"as_of": "2020-01-01"}),
    )

    # -- property graphs ----------------------------------------------------
    def node_table(d):
        return NodeTable(d, "people")

    def edge_table(d):
        return EdgeTableObject(d, "knows")

    def path_pattern(d):
        return graph_mod.PathPattern(
            d, graph_mod.GraphVertex(d, "n", node_table(d))
        )

    register_special_constructor(
        "graph.GraphVertex", lambda d: graph_mod.GraphVertex(d, "n", node_table(d))
    )
    register_special_constructor(
        "graph.GraphEdge", lambda d: graph_mod.GraphEdge(d, "e", edge_table(d))
    )
    register_special_constructor(
        "graph.VertexTable",
        lambda d: graph_mod.VertexTable(d, node_table(d), key_columns=["id"]),
    )
    register_special_constructor(
        "graph.EdgeTable",
        lambda d: graph_mod.EdgeTable(d, edge_table(d), ["src"], ["dst"]),
    )
    register_special_constructor(
        "graph.QuantifiedPath",
        lambda d: graph_mod.QuantifiedPath(
            d, graph_mod.GraphEdge(d, "e", edge_table(d)), min_repeats=1, max_repeats=3
        ),
    )
    register_special_constructor("graph.PathPattern", path_pattern)
    register_special_constructor(
        "graph.MatchClause", lambda d: graph_mod.MatchClause(d, path_pattern(d))
    )
    register_special_constructor(
        "graph.ColumnsClause",
        lambda d: graph_mod.ColumnsClause(d, graph_mod.GraphColumn("n", "id")),
    )
    register_special_constructor(
        "graph.GraphTableExpression",
        lambda d: graph_mod.GraphTableExpression(
            d,
            graph=PropertyGraph(d, "g"),
            match=graph_mod.MatchClause(d, path_pattern(d)),
            columns=graph_mod.ColumnsClause(d, graph_mod.GraphColumn("n", "id")),
        ),
    )
    register_special_constructor(
        "graph.CreatePropertyGraphExpression",
        lambda d: graph_mod.CreatePropertyGraphExpression(
            d, graph=PropertyGraph(d, "g"),
            vertex_tables=[graph_mod.VertexTable(d, node_table(d))],
        ),
    )
    # The formatter accepts "add"/"drop" against "vertex tables"/"edge tables"/
    # "tables"; anything else is refused.
    register_special_constructor(
        "graph.AlterPropertyGraphExpression",
        lambda d: graph_mod.AlterPropertyGraphExpression(
            d,
            graph=PropertyGraph(d, "g"),
            action="add",
            target="vertex tables",
            vertex_tables=[graph_mod.VertexTable(d, node_table(d))],
        ),
    )
    register_special_constructor(
        "graph.DropPropertyGraphExpression",
        lambda d: graph_mod.DropPropertyGraphExpression(d, graph=PropertyGraph(d, "g")),
    )

    # -- SQL/XML ------------------------------------------------------------
    register_special_constructor(
        "xml.XMLAttributesExpression",
        lambda d: XMLAttributesExpression(d, [XMLAttribute(Literal(d, "v"), "a")]),
    )
    register_special_constructor(
        "xml.XMLForestExpression",
        lambda d: XMLForestExpression(d, [XMLForestItem(Literal(d, "v"), "a")]),
    )
    register_special_constructor(
        "xml.XMLConcatExpression",
        lambda d: XMLConcatExpression(d, [Literal(d, "a"), Literal(d, "b")]),
    )

    # -- MariaDB's own expressions ------------------------------------------
    # Each of these guesses a bare string where the formatter wants an object.
    # `MariaDBFlushExpression` and friends are absent from this list on purpose:
    # their one-line constructors are guessed correctly, and the three that
    # refuse an empty collection are pinned in LEGITIMATE_NON_RENDERS with the
    # reason, because an instance with no options is not a statement.
    register_special_constructor(
        "routine.MariaDBCreateProcedureExpression",
        lambda d: maria_routine.MariaDBCreateProcedureExpression(
            d, Procedure(d, "pr"), params=["IN a INT"], body="BEGIN END"
        ),
    )
    register_special_constructor(
        "routine.MariaDBDropProcedureExpression",
        lambda d: maria_routine.MariaDBDropProcedureExpression(d, Procedure(d, "pr")),
    )
    register_special_constructor(
        "routine.MariaDBCallExpression",
        lambda d: maria_routine.MariaDBCallExpression(
            d, Procedure(d, "pr"), args=[Literal(d, 1)]
        ),
    )
    # Suffixed without a `statements.` prefix on purpose: `make_instance` matches
    # with `str.endswith`, and this class lives in `mariadb.expression.dml`, so
    # the core `statements.dml.InsertExpression` spelling would not reach it.
    register_special_constructor(
        "dml.MariaDBInsertExpression",
        lambda d: MariaDBInsertExpression(
            d,
            into=_table_obj(d),
            source=ValuesSource(d, [[Literal(d, 1)]]),
            columns=["a"],
        ),
    )
    register_special_constructor(
        "match_against.MariaDBMatchAgainstExpression",
        lambda d: MariaDBMatchAgainstExpression(
            d, columns=["title"], search_string="x"
        ),
    )
    register_special_constructor(
        "json.MariaDBJSONObjectExpression",
        lambda d: MariaDBJSONObjectExpression(d, {"a": 1}),
    )
    register_special_constructor(
        "json.MariaDBJSONArrayExpression",
        lambda d: MariaDBJSONArrayExpression(d, 1, 2, alias="arr"),
    )
    register_special_constructor(
        "json.MariaDBJSONExtractExpression",
        lambda d: MariaDBJSONExtractExpression(d, "data", "$.a", alias="n"),
    )
    register_special_constructor(
        "json.MariaDBJSONContainsExpression",
        lambda d: MariaDBJSONContainsExpression(d, "data", "x", "$.a"),
    )
    register_special_constructor(
        "spatial.MariaDBSTDistanceExpression",
        lambda d: MariaDBSTDistanceExpression(d, "g1", "g2"),
    )
    register_special_constructor(
        "partition.MariaDBExchangePartitionExpression",
        lambda d: MariaDBExchangePartitionExpression(
            d, _table_obj(d, "probe_part"), "p0", _table_obj(d, "probe_exch")
        ),
    )


register_specials()


# ---------------------------------------------------------------------------
# Lists that cannot grow or shrink silently
# ---------------------------------------------------------------------------

#: Classes the generic introspective constructor cannot build.
#:
#: Each is a real coverage gap, named here so it is visible rather than lost.
#: ``test_unconstructible_list_is_exact`` pins the tuple, so a class that gains a
#: constructor fails here until this entry is removed, and a class that starts
#: failing to build fails here too -- neither can become a quiet skip.
#:
#: The registered constructors in this module bring the total down from
#: twenty-six to thirteen. What remains is a shape the introspective guess
#: cannot satisfy: a keyword-only parameter hidden behind a defaulted positional,
#: or a collection the class requires to be non-empty and does not itself
#: default.
#:
#: XMLTABLE used to be pinned here. The gap it named was never in XMLTABLE but in
#: the harness: ``columns`` is annotated ``Sequence[XMLTableColumn]``, and the
#: introspective guess read the annotation's own ``__name__`` -- ``"Sequence"``
#: -- matched it against the Table/View/Sequence relation pattern, and handed the
#: parameter a catalogue ``Sequence`` object instead of a list of columns. The
#: guess now decides a parameterised alias before testing for a relation name, so
#: XMLTableExpression builds and is pinned in LEGITIMATE_NON_RENDERS instead,
#: against the formatter MariaDB declares no name for.
#:
#: Sorted, because the integrity test compares this against a sorted tuple of
#: what it observes. The reasons below are grouped by cause, not by module.
UNCONSTRUCTIBLE = (
    # ---- this backend's own expressions ------------------------------------
    # MariaDBColumnDefinition. The generic guess supplies a column name and no
    # data type; the class needs a dialect-bound type to render, and the guess's
    # type placeholder is not one.
    "rhosocial.activerecord.backend.impl.mariadb.expression.column.MariaDBColumnDefinition",
    # The six partition classes. Each takes a keyword-only `columns` / `expr`
    # list behind a defaulted positional, so the introspective constructor skips
    # it and the class is left declaring no members, which it refuses.
    "rhosocial.activerecord.backend.impl.mariadb.expression.partition.MariaDBPartitionByHash",
    "rhosocial.activerecord.backend.impl.mariadb.expression.partition.MariaDBPartitionByList",
    "rhosocial.activerecord.backend.impl.mariadb.expression.partition.MariaDBPartitionByListColumns",
    "rhosocial.activerecord.backend.impl.mariadb.expression.partition.MariaDBPartitionByRange",
    "rhosocial.activerecord.backend.impl.mariadb.expression.partition.MariaDBPartitionByRangeColumns",
    "rhosocial.activerecord.backend.impl.mariadb.expression.partition.MariaDBPartitionClause",
    # ENUM and SET. `values` is keyword-only behind a defaulted positional, so
    # the introspective constructor skips it and the type declares no members.
    "rhosocial.activerecord.backend.impl.mariadb.expression.types.MariaDBEnumType",
    "rhosocial.activerecord.backend.impl.mariadb.expression.types.MariaDBSetType",
    # ---- core expressions --------------------------------------------------
    # ALTER CONSTRAINT. `name` and `constraint_type` sit behind defaulted
    # positionals and are keyword-only, so the introspective constructor skips
    # them and the class refuses an incomplete action.
    "rhosocial.activerecord.backend.expression.statements.ddl_alter.AlterConstraint",
    # VALIDATE CONSTRAINT. Same shape as AlterConstraint: the required `name` is
    # keyword-only behind a defaulted positional.
    "rhosocial.activerecord.backend.expression.statements.ddl_alter.ValidateConstraint",
    # ADD DOMAIN CHECK. Widens a SQLPredicate into a DomainCheckConstraint and
    # needs one; the guess supplies a bare comparison whose literal would have to
    # render as a bind parameter, which DDL cannot carry.
    "rhosocial.activerecord.backend.expression.statements.ddl_domain.AddDomainCheckAction",
    # Core ENUM type. Its `values` list is keyword-only behind a defaulted
    # positional, so the introspective constructor skips it and the type declares
    # no members.
    "rhosocial.activerecord.backend.expression.types.enum_.EnumType",
)

#: Classes that construct but cannot render, for a reason belonging to their own
#: tree rather than to a defect. Each entry pins the exception type and a message
#: fragment, so a class that starts failing for a *different* reason fails here.
#:
#: Two distinct causes appear below, and they are not interchangeable:
#:
#: * **bases with no formatter of their own** -- a base class that names an
#:   expression category rather than a renderable thing. These are not
#:   ``inspect.isabstract`` (they are concrete enough to construct), so the
#:   collector keeps them, and each is pinned to its exact message so a base that
#:   started rendering fails here instead of passing quietly.
#: * **features MariaDB does not have** -- core statements MariaDB declares no
#:   formatter for. ``BaseExpression.to_sql()`` reports those as
#:   ``UnsupportedFeatureError`` naming the missing ``format_*`` method, which is
#:   the same type a dialect raises when it *knows* the statement and refuses it.
#:   The type stopped separating the two when core unified the spelling, so the
#:   **message fragment** is what carries the distinction, and that is why every
#:   entry below pins the formatter's name rather than a phrase: the dispatch
#:   says ``does not support the 'format_x' statement``, a refusal does not name
#:   a missing method. Pinning it is still the point -- it says "MariaDB has not
#:   implemented this", not "MariaDB has decided against it" -- which is why
#:   :func:`assert_sql_roundtrip_classified` consults this dict *before* the
#:   catch-all ``UnsupportedFeatureError`` branch instead of after it.
_NO_FORMATTER = "does not declare its dialect formatting method name"
_NO_METHOD = "Subclasses must implement to_sql() method"

LEGITIMATE_NON_RENDERS = {
    # ---- bases that name an expression category, not a renderable thing ----
    # Each of these is a base class that deliberately declares no `format_method`,
    # so `to_sql()` reports that there is nothing to dispatch.
    "rhosocial.activerecord.backend.expression.bases.SQLPredicate": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.bases.SQLValueExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    # The roots of the object tree. Each concrete object overrides `format_method`
    # with its own `format_*_object`; the base names only what every catalogue
    # object has in common.
    "rhosocial.activerecord.backend.expression.objects.base.SchemaObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.objects.relation.RelationObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.objects.routine.RoutineObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.objects.type_.TypeObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    # Expression-category bases whose concrete members each name their own
    # formatter: an ALTER TABLE action, an INSERT row source, a transaction step,
    # a temporal value, an introspection query.
    "rhosocial.activerecord.backend.expression.statements.ddl_alter.AlterTableAction": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.statements.dml.InsertDataSource": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.transaction.TransactionExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.datetime._TemporalValueExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.introspection.IntrospectionExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    # MariaDB's own equivalent bases, reached the same way: `SHOW`'s two roots
    # and the shared routine-DDL root declare no `format_method` because each
    # concrete subclass spells its own.
    "rhosocial.activerecord.backend.impl.mariadb.expression.show.ShowExpression": (
        NotImplementedError, _NO_METHOD
    ),
    "rhosocial.activerecord.backend.impl.mariadb.expression.show.ShowRelationExpression": (
        NotImplementedError, _NO_METHOD
    ),
    "rhosocial.activerecord.backend.impl.mariadb.expression.routine.MariaDBRoutineExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    # Two introspection roots that ask a subclass to name its own query, rather
    # than dispatching on a `format_method` property the way the other bases do.
    "rhosocial.activerecord.backend.expression.introspection.TableInfoExpression": (
        NotImplementedError, "Subclass must implement format_table_info_query"
    ),
    "rhosocial.activerecord.backend.expression.introspection.TriggerInfoExpression": (
        NotImplementedError, "Subclass must implement format_trigger_info_query"
    ),

    # ---- instances the generic constructor builds that are not statements ---
    # Each of these is a class the guess can construct and the formatter
    # correctly refuses, because the guessed instance is empty of whatever the
    # statement needs. The refusal is the point: an ANALYZE with no operation or
    # a RENAME with no pairs is not a statement, and rendering one would emit
    # SQL the server would reject with a far worse message.
    "rhosocial.activerecord.backend.impl.mariadb.expression.admin.MariaDBFlushExpression": (
        ValueError, "FLUSH requires at least one option"
    ),
    "rhosocial.activerecord.backend.impl.mariadb.expression.rename_table.MariaDBRenameTableExpression": (
        ValueError, "RENAME TABLE requires at least one <table> TO <table> pair"
    ),
    # The guess supplies the operation as its bare string; the enum member is
    # what the formatter dispatches on, so it refuses the string by name.
    "rhosocial.activerecord.backend.impl.mariadb.expression.maintenance.MariaDBTableMaintenanceExpression": (
        TypeError, "operation must be a TableMaintenanceOperation"
    ),
    # COLLATE validates its collation against MariaDB's own list; the guess's
    # placeholder collation is not one of them, which is the check working.
    "rhosocial.activerecord.backend.expression.collation.CollateExpression": (
        ValueError, "Unsupported MariaDB collation"
    ),

    # ---- features MariaDB has no formatter for -----------------------------
    # Every entry in this group is the *dispatch* failing, not a formatter
    # refusing: MariaDB declares no `format_*` for these, so
    # `BaseExpression.to_sql()` never gets as far as calling anything. Core
    # spells that `UnsupportedFeatureError` (it used to raise
    # `AttributeError`, which was the one capability gap in the tree reported
    # differently from every other), so the pins below re-typed to match. The
    # fragment is unchanged and is the load-bearing half of each pin: it is the
    # missing method's own name, which only the dispatch message carries.
    #
    # SQL/XML. Thirteen separate statements, no MariaDB implementation of any
    # of them. Grouped because they share one cause.
    "rhosocial.activerecord.backend.expression.xml.XMLAggExpression": (
        UnsupportedFeatureError, "format_xmlagg_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLAttributesExpression": (
        UnsupportedFeatureError, "format_xmlattributes_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLCommentExpression": (
        UnsupportedFeatureError, "format_xmlcomment_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLConcatExpression": (
        UnsupportedFeatureError, "format_xmlconcat_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLElementExpression": (
        UnsupportedFeatureError, "format_xmlelement_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLExistsExpression": (
        UnsupportedFeatureError, "format_xmlexists_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLForestExpression": (
        UnsupportedFeatureError, "format_xmlforest_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLPIExpression": (
        UnsupportedFeatureError, "format_xmlpi_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLParseExpression": (
        UnsupportedFeatureError, "format_xmlparse_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLQueryExpression": (
        UnsupportedFeatureError, "format_xmlquery_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLRootExpression": (
        UnsupportedFeatureError, "format_xmlroot_expression"
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLSerializeExpression": (
        UnsupportedFeatureError, "format_xmlserialize_expression"
    ),
    # XMLTABLE. Pinned in UNCONSTRUCTIBLE until the harness stopped reading
    # `Sequence[XMLTableColumn]` as a request for a catalogue Sequence; the
    # class itself never had a construction gap, so it belongs here with the
    # other twelve SQL/XML statements rather than back in the tuple.
    "rhosocial.activerecord.backend.expression.xml.XMLTableExpression": (
        UnsupportedFeatureError, "format_xmltable_expression"
    ),
    # Property graphs. MariaDB has a MATCH *predicate* but no property-graph DDL
    # and no GRAPH_TABLE row source; these are the eight pieces of that feature.
    "rhosocial.activerecord.backend.expression.graph.AlterPropertyGraphExpression": (
        UnsupportedFeatureError, "format_alter_property_graph_statement"
    ),
    "rhosocial.activerecord.backend.expression.graph.CreatePropertyGraphExpression": (
        UnsupportedFeatureError, "format_create_property_graph_statement"
    ),
    "rhosocial.activerecord.backend.expression.graph.DropPropertyGraphExpression": (
        UnsupportedFeatureError, "format_drop_property_graph_statement"
    ),
    "rhosocial.activerecord.backend.expression.graph.GraphTableExpression": (
        UnsupportedFeatureError, "format_graph_table_expression"
    ),
    "rhosocial.activerecord.backend.expression.graph.ColumnsClause": (
        UnsupportedFeatureError, "format_graph_columns_clause"
    ),
    "rhosocial.activerecord.backend.expression.graph.TablePropertiesClause": (
        UnsupportedFeatureError, "format_table_properties_clause"
    ),
    "rhosocial.activerecord.backend.expression.graph.VertexTable": (
        UnsupportedFeatureError, "format_vertex_table"
    ),
    "rhosocial.activerecord.backend.expression.graph.EdgeTable": (
        UnsupportedFeatureError, "format_edge_table"
    ),
    # PIVOT / UNPIVOT. Not MariaDB syntax, and no formatter.
    "rhosocial.activerecord.backend.expression.pivot.PivotExpression": (
        UnsupportedFeatureError, "format_pivot_expression"
    ),
    "rhosocial.activerecord.backend.expression.pivot.UnpivotExpression": (
        UnsupportedFeatureError, "format_unpivot_expression"
    ),
    # COMMENT ON. MariaDB's COMMENT is a table option and a column attribute,
    # both of which this dialect renders; the standalone statement is not
    # implemented. Worth pinning by name because it is a real gap rather than a
    # MariaDB refusal, and the table-option path renders today.
    "rhosocial.activerecord.backend.expression.statements.ddl_comment.CommentOnExpression": (
        UnsupportedFeatureError, "format_comment_statement"
    ),
    # The root of the row-source tree. No concrete source renders through
    # `format_table_source`; each overrides `format_method`. This is a base that
    # does name a formatter and no dialect here implements it, so it lands in the
    # dispatch-failure group rather than the no-`format_method` group above.
    "rhosocial.activerecord.backend.expression.sources.base.TableSource": (
        UnsupportedFeatureError, "format_table_source"
    ),

    # ---- core types MariaDB spells under its own class names ---------------
    # Type rendering dispatches on the type's *generic* name, looking for
    # ``format_data_type_<generic>``. MariaDB's implementations are registered
    # under MariaDB class names instead -- ``format_data_type_mariadb_binary``
    # rather than ``format_data_type_binary`` -- so core's generic types cannot
    # dispatch and the backend's own classes must be used:
    #
    #   core BinaryType      -> MariaDBBinaryType
    #   core VarBinaryType   -> MariaDBVarBinaryType
    #   core UUIDType        -> MariaDBUUIDType
    #
    # Pinned rather than "fixed", because the dispatch is a naming contract in
    # core's type registry and changing it here would be a core change. The
    # MariaDB equivalents are in the matrix and do render.
    "rhosocial.activerecord.backend.expression.types.array.ArrayType": (
        TypeError, "does not support the generic type 'array'"
    ),
    "rhosocial.activerecord.backend.expression.types.binary.BinaryType": (
        TypeError, "does not support the generic type 'binary'"
    ),
    "rhosocial.activerecord.backend.expression.types.binary.VarBinaryType": (
        TypeError, "does not support the generic type 'varbinary'"
    ),
    "rhosocial.activerecord.backend.expression.types.datetime_.IntervalType": (
        TypeError, "does not support the generic type 'interval'"
    ),
    "rhosocial.activerecord.backend.expression.types.uuid_.UUIDType": (
        TypeError, "does not support the generic type 'uuid'"
    ),
    # The root of the type tree. Every concrete type declares its own generic
    # name, which is what dispatch reads; the root declares none, so there is
    # nothing to dispatch on. TypeError, not UnsupportedFeatureError, because the
    # class is incomplete rather than the dialect being unable.
    "rhosocial.activerecord.backend.expression.types._base.DataType": (
        TypeError, "does not declare a valid generic type name"
    ),

    # MariaDB's trigger formatter reads ``or_replace``, ``ordering`` and
    # ``body``, none of which core's ``CreateTriggerExpression`` carries -- it
    # has ``if_not_exists`` and ``update_columns`` instead. So the MariaDB
    # formatter and the core expression disagree about the same hook, and the
    # expression reaches the formatter and then fails on a missing attribute.
    #
    # This is a real gap rather than a MariaDB refusal: MariaDB does support
    # CREATE TRIGGER (its own ``MariaDBTriggerMixin`` renders the OR REPLACE
    # form), but only for an expression shaped the way it expects, and this
    # repository has no such expression class. Named here so the gap is
    # recorded rather than swallowed.
    "rhosocial.activerecord.backend.expression.statements.ddl_trigger.CreateTriggerExpression": (
        AttributeError, "has no attribute 'or_replace'"
    ),
}


# ---------------------------------------------------------------------------
# The local SQL assertion: classify the outcome instead of swallowing it
# ---------------------------------------------------------------------------


def assert_sql_roundtrip_classified(fqn, instance, dialect):
    """Assert an expression's SQL survives the round-trip, or say precisely why not.

    Four outcomes, each asserted:

    * **renders** -- all three encodings must restore byte-identical SQL *and*
      byte-identical bind parameters.
    * a member of :data:`LEGITIMATE_NON_RENDERS` -- unrenderable by design,
      asserted as its exact type *and* message fragment.
    * ``UnsupportedFeatureError`` from a class *not* named in the dict -- MariaDB
      does not model the feature. Asserted as exactly that type, so a subclass
      raised for an unrelated reason is still visible rather than passing.
    * **anything else** -- a failure naming the class and the exception.

    The dict is consulted before the ``UnsupportedFeatureError`` branch, not
    after. Core reports a missing formatter as ``UnsupportedFeatureError`` too,
    so with the ``except`` clause in front a pinned entry naming a *missing*
    formatter would never be looked up: its type and message would go unasserted
    on this path and the table would have stopped saying which of the two causes
    each class has. Checking the pin first keeps both halves of it load-bearing.

    Returns a short string naming the branch taken, so a caller can report the
    classification distribution if it wants to.

    Raises:
        AssertionError: On a round-trip mismatch, on an unexpected exception
            type, or when a class's rendering outcome changed.
    """
    try:
        expected_sql, expected_params = instance.to_sql()
    except Exception as exc:
        if fqn in LEGITIMATE_NON_RENDERS:
            expected_type, fragment = LEGITIMATE_NON_RENDERS[fqn]
            assert type(exc) is expected_type, (
                f"{fqn}: LEGITIMATE_NON_RENDERS pins this class as a legitimate "
                f"non-render raising {expected_type.__name__}, but it raised "
                f"{type(exc).__name__}: {exc}"
            )
            assert fragment in str(exc), (
                f"{fqn}: expected {expected_type.__name__} and was expected to say "
                f"{fragment!r}, but it said: {exc}"
            )
            return "non-render"
        if type(exc) is UnsupportedFeatureError:
            return "unsupported"
        raise AssertionError(
            f"{fqn}: to_sql() raised {type(exc).__name__}, which is neither a "
            f"render nor a classified non-render, and this is a defect.\n"
            f"  UnsupportedFeatureError means MariaDB lacks the feature and "
            f"is always allowed.\n"
            f"  A class that cannot render for a reason belonging to its own "
            f"tree belongs in LEGITIMATE_NON_RENDERS.\n"
            f"  Exception: {exc}"
        ) from exc

    for channel, decoded in (
        ("dict", deserialize(serialize(instance), dialect)),
        ("json", deserialize_json(serialize_json(instance), dialect)),
        ("xml", deserialize_xml(serialize_xml(instance), dialect)),
    ):
        decoded_sql, decoded_params = decoded.to_sql()
        assert decoded_sql == expected_sql, (
            f"{fqn}: {channel} round-trip changed the SQL.\n"
            f"  original: {expected_sql!r}\n"
            f"  {channel}: {decoded_sql!r}"
        )
        assert decoded_params == expected_params, (
            f"{fqn}: {channel} round-trip changed the bind parameters.\n"
            f"  original: {expected_params!r}\n"
            f"  {channel}: {decoded_params!r}"
        )
    return "rendered"


@pytest.fixture(params=[fqn for fqn in sorted(REGISTERED)], ids=sorted(REGISTERED))
def expr_case(request, mariadb_dialect):
    fqn = request.param
    cls = REGISTERED[fqn]
    instance, source = make_instance(cls, mariadb_dialect)
    if instance is None:
        assert fqn in UNCONSTRUCTIBLE, (
            f"{fqn} cannot be built by the generic constructor ({source}) and is "
            f"not in UNCONSTRUCTIBLE. Either register a special constructor for "
            f"it or add it to the tuple with a reason -- do not let it disappear "
            f"into a skip."
        )
        pytest.skip(f"{fqn}: pinned in UNCONSTRUCTIBLE, cannot be constructed ({source})")
    return fqn, instance


class TestExpressionRoundtripAll:
    """All constructible expression classes round-trip through all encodings."""

    def test_get_params_roundtrip_across_encodings(self, expr_case, mariadb_dialect):
        fqn, instance = expr_case
        original = instance.get_params()

        spec_dict = serialize(instance)
        restored_d = deserialize(spec_dict, mariadb_dialect)
        assert_params_equal(restored_d.get_params(), original, fqn)

        json_str = serialize_json(instance)
        restored_j = deserialize_json(json_str, mariadb_dialect)
        assert_params_equal(restored_j.get_params(), original, fqn)

        xml_bytes = serialize_xml(instance)
        restored_x = deserialize_xml(xml_bytes, mariadb_dialect)
        assert_params_equal(restored_x.get_params(), original, fqn)

    def test_to_sql_roundtrip_classified(self, expr_case, mariadb_dialect):
        """A render must survive the round-trip; a non-render must be classified."""
        fqn, instance = expr_case
        assert_sql_roundtrip_classified(fqn, instance, mariadb_dialect)


class TestMariaDBNamespaceShape:
    """MariaDB has one namespace level, and it is a database.

    Pinned here rather than left to a formatter's own test, because the wrong
    answer is silent: a name qualified one level too many, or a second level
    appearing, renders valid SQL that addresses a different object than the
    caller named.

    ``supports_schema`` is the live value, and it is the one that settles a
    contradiction in this backend's tree. ``mixins/schema.py`` defines a
    ``MariaDBSchemaMixin`` answering ``True``, while the dialect inherits core's
    ``SchemaMixin`` and answers ``False``; nothing mixes that class in, so it is
    dead code. Asserting the live value here means the answer is recorded in a
    place a reader will look, and the dead class's ``True`` is visibly not it.
    The dead class is *not* deleted in this change -- that is a behaviour change,
    and it does not belong in a pass whose other work is mechanical.
    """

    def test_catalog_is_the_only_level_mariadb_qualifies(self, mariadb_dialect):
        assert mariadb_dialect.supports_catalog() is True
        assert mariadb_dialect.supports_catalog_qualification() is True
        assert mariadb_dialect.supports_schema_qualification() is False

    def test_schema_is_refused_on_the_ddl_side_too(self, mariadb_dialect):
        """The live DDL-side answer is ``False``, not the dead mixin's ``True``."""
        assert mariadb_dialect.supports_schema() is False

    def test_qualified_name_is_one_level(self, mariadb_dialect):
        """A database-qualified name spells as exactly two quoted parts."""
        table = Table(mariadb_dialect, "users", catalog_name="reporting")
        sql, params = table.to_sql()
        assert sql == "`reporting`.`users`"
        assert params == ()

    def test_information_schema_is_the_outermost_level(self, mariadb_dialect):
        """``information_schema`` is a database, so it rides the catalog slot.

        Asserted through the value rather than through the argument, so this
        cannot pass by a name that happens to appear in the expected SQL: set
        the catalog to something else and the SQL has to change.
        """
        table = Table(mariadb_dialect, "TABLES", catalog_name="information_schema")
        qualified, _ = table.to_sql()
        assert qualified == "`information_schema`.`TABLES`"

        unqualified, _ = Table(mariadb_dialect, "TABLES").to_sql()
        assert unqualified == "`TABLES`"

    def test_a_schema_level_is_refused_rather_than_dropped(self, mariadb_dialect):
        """A name carrying a schema raises instead of rendering without it.

        The refusal is the assertion. Rendering ``app.users`` as ``users`` would
        address a different object than the caller asked for, and MariaDB would
        accept it, so the error is the only place the mistake can surface.
        """
        table = Table(mariadb_dialect, "users", schema_name="reporting")
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            table.to_sql()
        assert "schema" in str(exc_info.value)

    def test_no_formatter_spells_a_third_part(self, mariadb_dialect):
        """No kind of object here renders more than a database and a name.

        The negative form of the one-level claim, and the one that catches a
        regression the positive tests cannot: MariaDB reaches fifteen per-kind
        renderers, and a level added to the wrong one of them would still leave
        ``Table`` rendering correctly. So the shape is checked on every kind
        that carries a namespace slot.

        ``Database`` is absent and deliberately so. A database *is* the outermost
        container, so core's ``format_database_object`` renders its bare name by
        design and never joins anything -- qualifying a database with a database
        would name something no engine can resolve.
        """
        dialect = mariadb_dialect
        objects = [
            Domain(dialect, "dom"),
            Function(dialect, "fn"),
            Index(dialect, "idx"),
            MaterializedView(dialect, "mv"),
            Schema(dialect, "sch"),
            Sequence(dialect, "seq"),
            Table(dialect, "tbl"),
            Trigger(dialect, "trg"),
            Type(dialect, "typ"),
            View(dialect, "vw"),
        ]
        for obj in objects:
            obj.catalog_name = "app"
            sql, params = obj.to_sql()
            assert sql == f"`app`.`{obj.name}`", (
                f"{type(obj).__name__} rendered {sql!r}; MariaDB names one "
                f"database and the object, so a third part means a level this "
                f"dialect does not have"
            )
            assert params == ()

        assert Database(dialect, "db").to_sql() == ("`db`", ())

    def test_separator_is_the_dialects_own(self, mariadb_dialect):
        """The join character is a class attribute, so a dialect can override it.

        Asserted as the class attribute rather than only through rendered SQL, so
        the fact that MariaDB states its separator is what is being tested -- an
        inherited default would render identically and prove nothing.
        """
        from rhosocial.activerecord.backend.impl.mariadb.mixins.namespace import (
            MariaDBNamespaceMixin,
        )

        assert MariaDBNamespaceMixin.separator == "."
        assert mariadb_dialect.separator == "."


class TestMatrixIntegrity:
    """Guards on the matrix and its lists, so neither can quietly change."""

    def test_unconstructible_list_is_exact(self, mariadb_dialect):
        """Pin the unconstructible tuple against what the constructor really skips.

        Two directions are checked. A class named here that now builds has gained
        a constructor and the entry is stale; a class that fails to build without
        being named would become a silent skip. Both fail here.
        """
        ExpressionRegistry._auto_register_builtins()
        actual = tuple(
            sorted(
                fqn
                for fqn in REGISTERED
                if make_instance(REGISTERED[fqn], mariadb_dialect)[0] is None
            )
        )
        assert actual == tuple(sorted(UNCONSTRUCTIBLE)), (
            "the set of expression classes the generic constructor cannot build "
            "changed.\n"
            f"  now skipped but not named: "
            f"{sorted(set(actual) - set(UNCONSTRUCTIBLE))}\n"
            f"  named but now built: "
            f"{sorted(set(UNCONSTRUCTIBLE) - set(actual))}\n"
            "Each new entry needs a reason in the comment above UNCONSTRUCTIBLE."
        )

    def test_unconstructible_entries_are_real_classes(self):
        """Every entry names a class that was actually collected."""
        unknown = set(UNCONSTRUCTIBLE) - set(REGISTERED)
        assert not unknown, (
            f"UNCONSTRUCTIBLE names classes that were not registered: {sorted(unknown)}"
        )

    def test_legitimate_non_renders_are_real_classes(self):
        """Every pinned non-render names a class that was actually collected."""
        unknown = set(LEGITIMATE_NON_RENDERS) - set(REGISTERED)
        assert not unknown, (
            f"LEGITIMATE_NON_RENDERS names classes that were not registered: "
            f"{sorted(unknown)}"
        )

    def test_pinned_non_render_really_does_not_render(self, mariadb_dialect):
        """Each pinned entry still raises what it claims, for the stated reason.

        Without this, an entry could sit in the dict for a class that renders
        perfectly well, and the matrix would be asserting nothing about it.
        """
        # Every entry is checked before asserting, so a run reports all of the
        # entries that have drifted rather than stopping at the first.
        wrong_type = []
        wrong_message = []
        unconstructible = []
        for fqn, (expected_type, fragment) in LEGITIMATE_NON_RENDERS.items():
            instance, source = make_instance(REGISTERED[fqn], mariadb_dialect)
            if instance is None:
                unconstructible.append(f"{fqn} ({source})")
                continue
            try:
                instance.to_sql()
            except Exception as exc:
                if type(exc) is not expected_type:
                    wrong_type.append(
                        f"{fqn}: pinned as {expected_type.__name__}, raised "
                        f"{type(exc).__name__}: {exc}"
                    )
                elif fragment not in str(exc):
                    wrong_message.append(
                        f"{fqn}: expected the message to mention {fragment!r}, "
                        f"got: {exc}"
                    )
            else:
                wrong_type.append(
                    f"{fqn}: pinned as a non-render but to_sql() succeeded"
                )
        assert not unconstructible, (
            f"pinned non-renders that could not be constructed: {unconstructible}"
        )
        assert not wrong_type, (
            "LEGITIMATE_NON_RENDERS entries whose exception type changed:\n  "
            + "\n  ".join(wrong_type)
        )
        assert not wrong_message, (
            "LEGITIMATE_NON_RENDERS entries whose message changed:\n  "
            + "\n  ".join(wrong_message)
        )

    def test_matrix_covers_both_packages_completely(self):
        """The matrix covers every concrete class both packages define.

        Re-walked here rather than trusting the module-level collection, so a
        class that appeared after import is caught. The package walk is used
        rather than the registry because the registry also holds whatever
        backends other test modules happened to import.
        """
        ExpressionRegistry._auto_register_builtins()
        expected = _matrix_classes()
        stray = [
            fqn
            for fqn in REGISTERED
            if not fqn.startswith((f"{MARIADB_EXPR_PKG}.", f"{CORE_EXPR_PKG}."))
        ]
        assert not stray, f"classes outside the two packages are in the matrix: {stray}"
        assert set(expected) == set(REGISTERED), (
            "the set of classes the two packages define changed after collection.\n"
            f"  now defined but not covered: {sorted(set(expected) - set(REGISTERED))}\n"
            f"  covered but no longer defined: {sorted(set(REGISTERED) - set(expected))}"
        )
        # A floor, not a ceiling: the count may only rise. A walk that stopped
        # early would still satisfy an equality assertion above if the early
        # classes were the same, so this catches a partial import.
        assert len(REGISTERED) > 300, (
            f"only {len(REGISTERED)} classes collected; the package walk may "
            f"have stopped early"
        )

    def test_every_covered_class_is_registered_for_deserialization(self):
        """A class in the matrix can be found again when deserializing.

        Deserialization looks the class up by name, so a class the matrix
        renders but the registry cannot resolve would round-trip into the wrong
        thing or nothing at all.
        """
        ExpressionRegistry._auto_register_builtins()
        unresolved = sorted(set(REGISTERED) - set(ExpressionRegistry._registry))
        assert not unresolved, (
            f"the matrix covers classes the registry cannot resolve: {unresolved}"
        )

    def test_coverage_report(self, mariadb_dialect):
        """Surface what the matrix covers, so coverage stays transparent.

        Counts are printed rather than asserted. An asserted ceiling would
        absorb a new gap silently, which is the failure mode this file exists to
        remove -- so the direction of the check here is a floor in
        ``test_matrix_covers_both_packages_completely`` and nothing else.
        """
        ExpressionRegistry._auto_register_builtins()
        buckets = {"rendered": 0, "unsupported": 0, "non-render": 0, "unconstructible": 0}
        for fqn in sorted(REGISTERED):
            instance, _ = make_instance(REGISTERED[fqn], mariadb_dialect)
            if instance is None:
                buckets["unconstructible"] += 1
                continue
            buckets[assert_sql_roundtrip_classified(fqn, instance, mariadb_dialect)] += 1
        print(
            f"\nexpression matrix: {len(REGISTERED)} registered, "
            f"{buckets['rendered']} render and round-trip, "
            f"{buckets['unsupported']} UnsupportedFeatureError, "
            f"{buckets['non-render']} pinned non-render, "
            f"{buckets['unconstructible']} pinned unconstructible"
        )
