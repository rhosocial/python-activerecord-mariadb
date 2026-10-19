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
* :class:`UnsupportedFeatureError` from a probe inside a formatter, for a class
  *not* named in the dict -- MariaDB does not model the feature. Asserted as
  exactly that type, so a subclass raised for an unrelated reason is still
  visible rather than passing.
* :class:`UnsupportedFeatureError` from the dispatch, for a class not named in
  the dict -- the dialect declares no ``format_*`` method for it at all, which
  is a wiring fact about this backend rather than a capability answer. The
  method the dispatch names must be a row in :data:`UNMODELLED_FORMATTERS`,
  so the gap is a decision with a reason rather than an omission; see
  :func:`_dispatched_formatter`.
* **anything else** -- a failure naming the class and the exception.

The dict is read before the :class:`UnsupportedFeatureError` branch, because core
reports a *missing formatter* as ``UnsupportedFeatureError`` as well; see
:func:`assert_sql_roundtrip_classified`.

Why the dispatch's refusal is no longer allowed on its type alone
=================================================================

The two ``UnsupportedFeatureError`` outcomes above were one branch until core
turned ``trim``/``lpad``/``rpad``/``repeat`` into dedicated nodes. A backend
that mixed in no formatter for one of those would have answered every
``.lpad(...)`` with a refusal this matrix read as "MariaDB lacks the feature",
and nothing here could tell that apart from a probe inside a formatter
declining a feature MariaDB genuinely does not have. The exception itself
records who is refusing: a probe names the feature, while the dispatch frames
the formatting method it could not find as ``the '<method>' statement`` --
see :func:`_dispatched_formatter`. Only the dispatch's refusal is a wiring
fact about this backend, so only it must be accounted for:
:meth:`TestMatrixIntegrity.test_unmodelled_formatter_list_is_exact` pins
:data:`UNMODELLED_FORMATTERS` in both directions, and a method nobody listed
fails the run.

And what happens when a class cannot be constructed
==================================================

``make_instance(...) is None`` becomes a skip, but only for a class named in
:data:`UNCONSTRUCTIBLE`, and :func:`TestMatrixIntegrity.test_unconstructible_list_is_exact`
pins that tuple in both directions. A class that starts needing an exemption
fails CI instead of turning into a skip, and a stale entry fails too.

And what happens when an artifact cannot travel
===============================================

Every class is also written and read back through the dict / JSON / XML
channels. A channel that fails for a class named in
:data:`SERIALIZATION_GAP` fails there -- the row says which channels and what
they raise or degrade -- and a class that starts failing *without* a row fails
its own assertion. The rows all record defects in core's serialization layer
(a parameter its vocabulary or its constructors cannot carry); none can be
fixed from this repository, and each is pinned so the run goes red the day
core fixes it and the row becomes stale.
"""

import datetime
import decimal
import inspect
import json
import uuid
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
    _ExtractBase,
    ExtractFieldExpression,
)
from rhosocial.activerecord.backend.expression import declared as declared_mod
from rhosocial.activerecord.backend.expression.functions.string import (
    LeftFunction,
    RightFunction,
    SubstringExpression,
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
from rhosocial.activerecord.backend.expression.operators import (
    ArithmeticOperation,
)
from rhosocial.activerecord.backend.expression.predicates import (
    ComparisonPredicate,
    ILikePredicate,
    LikePredicate,
)
from rhosocial.activerecord.backend.expression.query_parts import JoinClause
from rhosocial.activerecord.backend.expression.query_sources import SetOperation
from rhosocial.activerecord.backend.expression.serialization import (
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
    ForeignKeyConstraint,
    IndexDefinition,
    ReferencesClause,
    TableConstraint,
    ColumnNotNullConstraint,
    TablePrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
    TriggerEvent,
    TriggerTiming,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryStatement
from rhosocial.activerecord.backend.expression.statements.dml import (
    MergeAction,
    MergeActionType,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
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
from rhosocial.activerecord.backend.impl.mariadb.expression import show as maria_show
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
from expression_roundtrip_harness import (
    assert_params_equal,
    collect_expression_classes,
    make_instance,
    register_all,
    register_special_constructor,
)

MARIADB_EXPR_PKG = "rhosocial.activerecord.backend.impl.mariadb.expression"
CORE_EXPR_PKG = "rhosocial.activerecord.backend.expression"


def _collect(package: str) -> Dict[str, type]:
    """Every concrete expression class *package* defines, by fully qualified name.

    Collected by walking the package, not by reading the deserialization
    registry: that registry is process-global and *grows* as other test
    modules import their own backends, so reading it would make this matrix's
    contents depend on which files pytest happened to import first. Sibling
    backends' classes would then be rendered with the MariaDB dialect, which
    is not a meaningful thing to assert.

    ``ddl_alter`` once exported four aliases of two classes (``AlterConstraint``
    and ``ValidateConstraint`` each had two spellings); core settled on the
    ``*Action`` names and dropped the short ones, so each action is collected
    once now. The by-identity pass below stays: a class exported under two
    names must still not be tested twice.
    """
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

    Deserialization resolves a kind to its class through the framework's
    default registry -- which is *not* the ``(dialect, kind)`` render
    registry: the registry names classes for the artifact reader, the render
    registry names formatters. Core populates the framework's own packages
    on the registry's first use and re-registering one of those classes is a
    no-op, so the MariaDB classes collected here are what the call adds.
    """
    merged: Dict[str, type] = {}
    for package in (MARIADB_EXPR_PKG, CORE_EXPR_PKG):
        merged.update(_collect(package))
    register_all(merged)
    return merged


REGISTERED = _matrix_classes()
# Enums need no registration of their own: a member travels as its scalar
# value (a str enum is a str) and the constructor normalises on read, which
# is the conversion §4.11.2 puts in the constructor rather than the reader.
# A dataclass parameter cannot travel at all -- it is neither a language-
# neutral scalar nor an expression instance, so serialization refuses it by
# name and the classes that carry one are registered below with that reason.


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
    return QueryStatement(
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
    # -- the predicate the whole file is built on ----------------------------
    # ``op`` normalises through the operator enum at construction, so the
    # guess's bare ``"x"`` is refused there and the class reported as
    # unbuildable. Two columns over a table is the shape every DDL position
    # wants as well: it renders with no bind parameters at all.
    register_special_constructor(
        "predicates.ComparisonPredicate",
        lambda d: _column_predicate(d),
    )

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
        "statements.ddl_table.CreateTableStatement",
        lambda d: ddl_table.CreateTableStatement(d, _table_obj(d), [_integer_column(d)]),
    )
    register_special_constructor(
        "statements.ddl_table.DropTableStatement",
        lambda d: ddl_table.DropTableStatement(d, _table_obj(d)),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableLikeStatement",
        lambda d: ddl_table.CreateTableLikeStatement(
            d, _table_obj(d), Table(d, "other")
        ),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableCloneStatement",
        lambda d: ddl_table.CreateTableCloneStatement(
            d, _table_obj(d), Table(d, "other")
        ),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableAsStatement",
        lambda d: ddl_table.CreateTableAsStatement(d, _table_obj(d), _one_column_query(d)),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableFromTemplateStatement",
        lambda d: ddl_table.CreateTableFromTemplateStatement(
            d, _table_obj(d), _one_column_query(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_truncate.TruncateStatement",
        lambda d: ddl_truncate.TruncateStatement(d, _table_obj(d)),
    )
    # Overrides the shared testsuite factory, which binds no dialect to its type.
    register_special_constructor(
        "statements.ddl_table.ColumnDefinition", _integer_column
    )

    # -- indexes ------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_index.CreateIndexStatement",
        lambda d: ddl_index.CreateIndexStatement(
            d, index=Index(d, "i"), table=_table_obj(d), columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_index.DropIndexStatement",
        lambda d: ddl_index.DropIndexStatement(d, index=Index(d, "i")),
    )
    register_special_constructor(
        "statements.ddl_index.CreateFulltextIndexStatement",
        lambda d: ddl_index.CreateFulltextIndexStatement(
            d, index=Index(d, "i"), table=_table_obj(d), columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_index.DropFulltextIndexStatement",
        lambda d: ddl_index.DropFulltextIndexStatement(
            d, index=Index(d, "i"), table=_table_obj(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_alter.DropIndexAction",
        lambda d: ddl_alter.DropIndexAction(d, Index(d, "i")),
    )
    register_special_constructor(
        "statements.ddl_alter.AddColumnAction",
        lambda d: ddl_alter.AddColumnAction(d, _integer_column(d)),
    )
    register_special_constructor(
        "statements.ddl_alter.ModifyColumnAction",
        lambda d: ddl_alter.ModifyColumnAction(d, _integer_column(d)),
    )
    # CHANGE needs both the old name and the new definition.
    register_special_constructor(
        "statements.ddl_alter.ChangeColumnAction",
        lambda d: ddl_alter.ChangeColumnAction(d, "old_col", _integer_column(d)),
    )
    register_special_constructor(
        "statements.ddl_alter.AddIndexAction",
        lambda d: ddl_alter.AddIndexAction(d, IndexDefinition(d, "i", ["a"])),
    )
    register_special_constructor(
        "statements.ddl_alter.AddTableConstraintAction",
        lambda d: ddl_alter.AddTableConstraintAction(
            d,
            TableConstraint(d, branch=TablePrimaryKeyConstraint(d, ["a"]), name="c"),
        ),
    )

    # -- databases, schemas, domains, types --------------------------------
    register_special_constructor(
        "statements.ddl_database.CreateDatabaseStatement",
        lambda d: ddl_database.CreateDatabaseStatement(d, Database(d, "db")),
    )
    register_special_constructor(
        "statements.ddl_database.DropDatabaseStatement",
        lambda d: ddl_database.DropDatabaseStatement(d, Database(d, "db")),
    )
    register_special_constructor(
        "statements.ddl_database.AlterDatabaseStatement",
        lambda d: ddl_database.AlterDatabaseStatement(
            d,
            Database(d, "db"),
            action=AlterDatabaseAction.RENAME_TO,
            target="renamed_db",
        ),
    )
    register_special_constructor(
        "statements.ddl_schema.CreateSchemaStatement",
        lambda d: ddl_schema.CreateSchemaStatement(d, Schema(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_schema.DropSchemaStatement",
        lambda d: ddl_schema.DropSchemaStatement(d, Schema(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_domain.CreateDomainStatement",
        lambda d: ddl_domain.CreateDomainStatement(d, Domain(d, "dom"), IntegerType(d)),
    )
    register_special_constructor(
        "statements.ddl_domain.DropDomainStatement",
        lambda d: ddl_domain.DropDomainStatement(d, Domain(d, "dom")),
    )
    register_special_constructor(
        "statements.ddl_domain.AlterDomainStatement",
        lambda d: ddl_domain.AlterDomainStatement(
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
        "statements.ddl_type.CreateTypeStatement",
        lambda d: ddl_type.CreateTypeStatement(
            d, type=Type(d, "t"), definition=_DummyTypeDefinition(d, IntegerType(d))
        ),
    )
    register_special_constructor(
        "statements.ddl_type.AlterTypeStatement",
        lambda d: ddl_type.AlterTypeStatement(
            d, type=Type(d, "t"), actions=[_DummyTypeAlterAction(d, new_name="u")]
        ),
    )
    register_special_constructor(
        "statements.ddl_type.DropTypeStatement",
        lambda d: ddl_type.DropTypeStatement(d, type=Type(d, "t")),
    )

    # -- routines, triggers, comments --------------------------------------
    register_special_constructor(
        "statements.ddl_function.CreateFunctionStatement",
        lambda d: ddl_function.CreateFunctionStatement(
            d, Function(d, "fn"), returns="integer", body="SELECT 1"
        ),
    )
    register_special_constructor(
        "statements.ddl_function.DropFunctionStatement",
        lambda d: ddl_function.DropFunctionStatement(d, Function(d, "fn")),
    )
    register_special_constructor(
        "statements.ddl_trigger.CreateTriggerStatement",
        lambda d: ddl_trigger.CreateTriggerStatement(
            d,
            trigger=Trigger(d, "trg"),
            table=_table_obj(d),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT],
            function=Function(d, "fn"),
        ),
    )
    register_special_constructor(
        "statements.ddl_trigger.DropTriggerStatement",
        lambda d: ddl_trigger.DropTriggerStatement(d, trigger=Trigger(d, "trg")),
    )
    register_special_constructor(
        "statements.ddl_comment.CommentOnStatement",
        lambda d: ddl_comment.CommentOnStatement(d, "table", _table_obj(d), comment="c"),
    )

    # -- views --------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_view.DropViewStatement",
        lambda d: ddl_view.DropViewStatement(d, View(d, "v")),
    )
    register_special_constructor(
        "statements.ddl_view.CreateMaterializedViewStatement",
        lambda d: ddl_view.CreateMaterializedViewStatement(
            d, MaterializedView(d, "mv"), _one_column_query(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_view.DropMaterializedViewStatement",
        lambda d: ddl_view.DropMaterializedViewStatement(d, MaterializedView(d, "mv")),
    )
    register_special_constructor(
        "statements.ddl_view.RefreshMaterializedViewStatement",
        lambda d: ddl_view.RefreshMaterializedViewStatement(
            d, MaterializedView(d, "mv")
        ),
    )

    # -- DML ----------------------------------------------------------------
    register_special_constructor(
        "statements.dml.InsertStatement",
        lambda d: dml.InsertStatement(
            d, into=_table_obj(d), source=ValuesSource(d, [[Literal(d, 1)]])
        ),
    )
    register_special_constructor(
        "statements.dml.DeleteStatement",
        lambda d: dml.DeleteStatement(d, _table_obj(d)),
    )
    register_special_constructor(
        "statements.dml.MergeStatement",
        lambda d: dml.MergeStatement(
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
        lambda d: ColumnConstraint(d, branch=ColumnNotNullConstraint(d), name="c"),
    )
    register_special_constructor(
        "statements.ddl_table.TableConstraint",
        lambda d: TableConstraint(d, branch=TablePrimaryKeyConstraint(d, ["a"]), name="c"),
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
        "graph.edge_table_definition",
        lambda d: graph_mod.EdgeTableDefinition(d, edge_table(d), ["src"], ["dst"]),
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
        "graph.CreatePropertyGraphStatement",
        lambda d: graph_mod.CreatePropertyGraphStatement(
            d, graph=PropertyGraph(d, "g"),
            vertex_tables=[graph_mod.VertexTable(d, node_table(d))],
        ),
    )
    # The formatter accepts "add"/"drop" against "vertex tables"/"edge tables"/
    # "tables"; anything else is refused.
    register_special_constructor(
        "graph.AlterPropertyGraphStatement",
        lambda d: graph_mod.AlterPropertyGraphStatement(
            d,
            graph=PropertyGraph(d, "g"),
            action="add",
            target="vertex tables",
            vertex_tables=[graph_mod.VertexTable(d, node_table(d))],
        ),
    )
    register_special_constructor(
        "graph.DropPropertyGraphStatement",
        lambda d: graph_mod.DropPropertyGraphStatement(d, graph=PropertyGraph(d, "g")),
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

    # -- predicates whose operand slots are expressions ---------------------
    # ``LikePredicate`` carries the operator as a parameter and takes its two
    # operands as value nodes, so the generic guess puts plain strings in both
    # positions and the instance cannot render (``'str' object has no attribute
    # 'to_sql'``). ``ILikePredicate`` takes its column as ``Any`` for the same
    # reason. Core's own dummy2 matrix registers these two shapes; this is the
    # same registration, so the contract the core states is the one measured
    # here. MariaDB spells LIKE with core's own formatter and refuses ILIKE
    # through its ``supports_ilike`` probe, so neither needs a matrix row.
    register_special_constructor(
        "predicates.LikePredicate",
        lambda d: LikePredicate(d, "LIKE", Column(d, "a"), Literal(d, "%x%")),
    )
    register_special_constructor(
        "predicates.ILikePredicate",
        lambda d: ILikePredicate(d, Column(d, "a"), "%x%"),
    )

    # -- nodes whose operation is a closed set of *words* ---------------------
    # ``ArithmeticOperation`` and ``SetOperation`` both carry their operation as
    # a word (``add``/``sub``/``mul``/``div``/``mod`` and
    # ``union``/``union_all``/``intersect``/``except``) and refuse anything else
    # at construction. The introspective guess reads ``op: str`` and supplies
    # ``"x"``, which is not one of them, so both need a real word handed in.
    register_special_constructor(
        "operators.ArithmeticOperation",
        lambda d: ArithmeticOperation(d, "add", Column(d, "a"), Column(d, "b")),
    )
    register_special_constructor(
        "query_sources.SetOperation",
        lambda d: SetOperation(
            d,
            op="union",
            left=QueryStatement(d, select=[Column(d, "id")], from_=_table_obj(d)),
            right=QueryStatement(
                d, select=[Column(d, "id")], from_=_table_obj(d, "other")
            ),
        ),
    )

    # -- MariaDB's own expressions ------------------------------------------
    # Each of these guesses a bare string where the formatter wants an object.
    # `MariaDBFlushExpression` and friends are absent from this list on purpose:
    # their one-line constructors are guessed correctly, and the three that
    # refuse an empty collection are pinned in LEGITIMATE_NON_RENDERS with the
    # reason, because an instance with no options is not a statement.
    #
    # SHOW. `relation` is annotated `Union[RelationObject, str]`, and the
    # heuristic reads a union's members when it asks what a parameter is, so it
    # finds the `RelationObject` arm and supplies a Literal -- which the
    # constructor refuses, because a SHOW target is a relation or a name, never
    # an expression. Each statement gets the relation object it names, so the
    # rendered SQL is one this backend actually accepts.
    register_special_constructor(
        "show.ShowRelationExpression",
        lambda d: maria_show.ShowRelationExpression(d, _table_obj(d, "probe_rel")),
    )
    register_special_constructor(
        "show.ShowColumnsExpression",
        lambda d: maria_show.ShowColumnsExpression(d, _table_obj(d, "probe_cols")),
    )
    register_special_constructor(
        "show.ShowCreateTableExpression",
        lambda d: maria_show.ShowCreateTableExpression(d, _table_obj(d, "probe_ct")),
    )
    register_special_constructor(
        "show.ShowCreateViewExpression",
        lambda d: maria_show.ShowCreateViewExpression(d, View(d, "probe_cv")),
    )
    register_special_constructor(
        "show.ShowCreateTriggerExpression",
        lambda d: maria_show.ShowCreateTriggerExpression(d, Trigger(d, "probe_trg")),
    )
    register_special_constructor(
        "show.ShowIndexExpression",
        lambda d: maria_show.ShowIndexExpression(d, _table_obj(d, "probe_idx")),
    )
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
    # the core `statements.dml.InsertStatement` spelling would not reach it.
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

    # -- declared-result annotations -----------------------------------------
    # An annotation renders what it annotates, and ``format_declared_result``
    # reads an alias off both the source and the annotation itself. The ten
    # surface classes each gain one through their value-type base, so they
    # render; the shared base ``_Annotation`` declares no alias and the
    # formatter reads one anyway, which is pinned in
    # LEGITIMATE_NON_RENDERS rather than papered over here. One aliasable
    # source serves the base and every surface class.
    from rhosocial.activerecord.backend.expression.core import FunctionCall

    def _aliasable_source(d):
        return FunctionCall(d, "FUNC", niladic=True)

    register_special_constructor(
        "declared._Annotation",
        lambda d: declared_mod._Annotation(d, _aliasable_source(d)),
    )
    for _name in (
        "ArrayAnnotation",
        "BinaryAnnotation",
        "BooleanAnnotation",
        "IntegerAnnotation",
        "JSONAnnotation",
        "NumberAnnotation",
        "TemporalAnnotation",
        "TextAnnotation",
        "UUIDAnnotation",
        "XMLAnnotation",
    ):
        register_special_constructor(
            f"declared.{_name}",
            lambda d, _n=_name: getattr(declared_mod, _n)(d, _aliasable_source(d)),
        )

    # -- string functions with declared operands ------------------------------
    # ``LEFT`` / ``RIGHT`` count their characters, so the count has to be a
    # whole number: the guess hands the string-annotated slot the bare string
    # ``"x"``, which serializes into a Literal the reconstruction then
    # compares with 0 -- a TypeError that is the guess's, not MariaDB's.
    # ``SUBSTRING`` bounds its positions at construction and the guess cannot
    # satisfy them either. Real operands, and each renders.
    register_special_constructor(
        "functions.string.LeftFunction",
        lambda d: LeftFunction(d, Column(d, "t"), Literal(d, 3)),
    )
    register_special_constructor(
        "functions.string.RightFunction",
        lambda d: RightFunction(d, Column(d, "t"), Literal(d, 3)),
    )
    register_special_constructor(
        "functions.string.SubstringExpression",
        lambda d: SubstringExpression(d, Column(d, "t"), Literal(d, 1), Literal(d, 2)),
    )

    # -- the extract spellings -------------------------------------------------
    # Both extract nodes normalize their ``field`` through the datetime-field
    # enum and the guess's bare string is refused there. The field-named class
    # is asked for the ``YEAR`` spelling it exists to carry; the shared base
    # keeps the standard ``EXTRACT`` default.
    register_special_constructor(
        "datetime._ExtractBase",
        lambda d: _ExtractBase(d, "year", Column(d, "ts")),
    )
    register_special_constructor(
        "datetime.ExtractFieldExpression",
        lambda d: ExtractFieldExpression(d, "year", Column(d, "ts"), spelling="YEAR"),
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
    # ---- core expressions, arrived with the typed-column work ----------------
    # UUID constant. `which` must name 'nil' or 'max' and __init__ rejects
    # anything else, so the filler's guess is refused at construction.
    "rhosocial.activerecord.backend.expression.uuid.UUIDConstantExpression",
    # UUID generation. Takes only a dialect and a keyword-only alias, so there
    # is no parameter the filler can supply a value for.
    "rhosocial.activerecord.backend.expression.uuid.UUIDGenerationExpression",
    # UUID cast. `expression` is annotated Any, so the filler hands it a string
    # where the node needs an expression to cast.
    "rhosocial.activerecord.backend.expression.uuid.UUIDCastFunction",
    # ---- core expressions --------------------------------------------------
    # ALTER CONSTRAINT. `name` and `constraint_type` sit behind defaulted
    # positionals and are keyword-only, so the introspective constructor skips
    # them and the class refuses an incomplete action.
    "rhosocial.activerecord.backend.expression.statements.ddl_alter.AlterConstraintAction",
    # ADD DOMAIN CHECK. Widens a SQLPredicate into a DomainCheckConstraint and
    # needs one; the guess supplies a bare comparison whose literal would have to
    # render as a bind parameter, which DDL cannot carry.
    "rhosocial.activerecord.backend.expression.statements.ddl_domain.AddDomainCheckAction",
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
    "rhosocial.activerecord.backend.expression.bases.SQLValue": (
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
    "rhosocial.activerecord.backend.expression.datetime._TemporalValue": (
        NotImplementedError, _NO_FORMATTER
    ),
    # The DDL column-clause base and the two constraint-branch bases. Each names
    # the *category* rather than a renderable node and deliberately overrides no
    # ``format_method``: a column clause is one of collation / charset / identity
    # / auto-increment / comment / generated, and a constraint branch is one of
    # primary key / unique / not null / nullable / check / default / foreign key
    # / generated. The concrete members each name their own formatter and are in
    # the matrix; the bases have nothing to dispatch, so this is the same
    # no-formatter outcome as the bases above. S3 introduced the two branch
    # bases, and the wildcard split did not touch these.
    "rhosocial.activerecord.backend.expression.statements.ddl_table.ColumnClause": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.statements.ddl_table.ColumnConstraintBranch": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.statements.ddl_table.TableConstraintBranch": (
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
    # The declared-result base. ``format_declared_result`` reads ``expr.alias``
    # on the node it renders, and this base declares none: ``alias`` belongs to
    # ``AliasableMixin``, which the ten surface classes each gain through their
    # value-type base and this shared root does not. So the base cannot render
    # in *any* dialect, while every surface class beside it renders here. A
    # formatter reading a field its own node does not declare is the defect
    # (the reflection ban says which side has to move), and it is core's to
    # fix; pinned so the row goes away the day it is.
    "rhosocial.activerecord.backend.expression.declared._Annotation": (
        AttributeError, "has no attribute 'alias'"
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
    "rhosocial.activerecord.backend.expression.collation.CollateFunction": (
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
    "rhosocial.activerecord.backend.expression.xml.XMLExistsPredicate": (
        UnsupportedFeatureError, "format_xmlexists_predicate"
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
    "rhosocial.activerecord.backend.expression.graph.AlterPropertyGraphStatement": (
        UnsupportedFeatureError, "format_alter_property_graph_statement"
    ),
    "rhosocial.activerecord.backend.expression.graph.CreatePropertyGraphStatement": (
        UnsupportedFeatureError, "format_create_property_graph_statement"
    ),
    "rhosocial.activerecord.backend.expression.graph.DropPropertyGraphStatement": (
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
    # EdgeTable used to be pinned here as ``graph.EdgeTable``. Core moved the
    # relation object to ``objects.relation``, where it is an ordinary
    # ``Table`` subclass and renders through the table formatter; what is left
    # in ``graph`` is the DDL piece, ``EdgeTableDefinition``, pinned above
    # against the formatter MariaDB declares no name for.
    # PIVOT / UNPIVOT. Not MariaDB syntax, and no formatter.
    "rhosocial.activerecord.backend.expression.pivot.Pivot": (
        UnsupportedFeatureError, "format_pivot"
    ),
    "rhosocial.activerecord.backend.expression.pivot.Unpivot": (
        UnsupportedFeatureError, "format_unpivot"
    ),
    # COMMENT ON. MariaDB's COMMENT is a table option and a column attribute,
    # both of which this dialect renders; the standalone statement is not
    # implemented. Worth pinning by name because it is a real gap rather than a
    # MariaDB refusal, and the table-option path renders today.
    "rhosocial.activerecord.backend.expression.statements.ddl_comment.CommentOnStatement": (
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
    #
    # Pinned rather than "fixed", because the dispatch is a naming contract in
    # core's type registry and changing it here would be a core change. The
    # MariaDB equivalents are in the matrix and do render.

    # UUIDType was on that list once and is not any more. Unlike the two
    # above it does have ``format_data_type_uuid``, and that delegates to
    # ``format_data_type_mariadb_uuid``, which version-gates on MariaDB 10.7:
    # below it the answer is UnsupportedFeatureError, from 10.7 up the column
    # renders as UUID. One static pin cannot say both halves, and the pin is
    # consulted before the UnsupportedFeatureError branch, so any entry here
    # fails on one end of the matrix. Left unpinned: each outcome is already
    # classified -- unsupported on the old servers, rendered on the new ones.
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
    # REAL is a synonym for DOUBLE in the default SQL mode, and every wired
    # server reports the column back as ``double``, so the single-precision
    # concept cannot round-trip. Declare DoubleType instead, or FloatType for
    # 4-byte single precision.
    "rhosocial.activerecord.backend.expression.types.numeric.RealType": (
        TypeError, "does not support the generic type 'real'"
    ),
    # No SQL/XML type either, and the same naming contract as the three above.
    "rhosocial.activerecord.backend.expression.types.xml_.XmlType": (
        TypeError, "does not support the generic type 'xml'"
    ),
    # The root of the type tree. Every concrete type declares its own generic
    # name, which is what dispatch reads; the root declares none, so the
    # dialect is asked for ``format_data_type_None`` and answers by naming the
    # generic name it was given -- ``None``. TypeError, not
    # UnsupportedFeatureError, because the class is incomplete rather than the
    # dialect being unable. The message moved from "does not declare a valid
    # generic type name" to naming the absent generic name when core started
    # reporting the dispatch's own lookup instead.
    "rhosocial.activerecord.backend.expression.types._base.DataType": (
        TypeError, "does not support the generic type None"
    ),

    # MariaDB's trigger formatter reads ``or_replace``, ``ordering`` and
    # ``body``, none of which core's ``CreateTriggerStatement`` carries -- it
    # has ``if_not_exists`` and ``update_columns`` instead. So the MariaDB
    # formatter and the core expression disagree about the same hook, and the
    # expression reaches the formatter and then fails on a missing attribute.
    #
    # This is a real gap rather than a MariaDB refusal: MariaDB does support
    # CREATE TRIGGER (its own ``MariaDBTriggerMixin`` renders the OR REPLACE
    # form), but only for an expression shaped the way it expects, and this
    # repository has no such expression class. Named here so the gap is
    # recorded rather than swallowed.
    "rhosocial.activerecord.backend.expression.statements.ddl_trigger.CreateTriggerStatement": (
        AttributeError, "has no attribute 'or_replace'"
    ),
}


# ---------------------------------------------------------------------------
# The round-trip gap: an artifact core cannot carry is not a pass
# ---------------------------------------------------------------------------
#
# ``to_sql()`` above classifies what happens when a class is *rendered*. This
# table classifies the other half: what happens when its artifact is written
# and read back. Both halves are per-class assertions here, and both refuse to
# swallow a failure.
#
# Every row is a defect in **core's serialization layer**, not in this backend
# and not in the harness: the classes below construct, render, and pin their
# parameters like any other, and the artifact writer or the reader cannot
# carry one of those parameters anyway. Three shapes appear, and the shape is
# the reason the row exists:
#
# * **the writer refuses the parameter** -- ``encode_artifact`` asks
#   ``LiteralKind.of`` what kind a value belongs to, and that vocabulary is
#   the closed set of *value* types. A plain (non-``str``) enum member is not
#   in it and is refused by name, and neither is a host object that is
#   neither an expression nor a scalar (``XMLAttribute``, ``GraphColumn``).
#   Every channel fails, including the dict one, because the failure is on
#   the write.
# * **the constructor refuses its own wire form** -- the JSON and XML
#   channels write the member's *value*, a plain ``str``, and the
#   constructor answers "must be a <Enum>". The artifact is unreadable by
#   the node that produced it.
# * **the constructor does not normalise on read** -- same write, same read,
#   and the value survives while the host type does not: the parameter comes
#   back as a ``str`` where an enum member went in. ``assert_params_equal``
#   reports it as a type mismatch naming the member type, which is the
#   witness these rows pin.
#
# A fourth, narrower shape: the XML channel spells a ``str``-enum member as
# ``str(member)`` -- ``"DateTimeField.YEAR"`` rather than ``"year"`` -- so the
# reader hands the constructor a word that is neither a member's value nor a
# member's name and the normaliser refuses it. Only that channel fails; the
# dict channel carries the member untouched and JSON carries its value.
#
# The writer and the reader are core's, so a row in the first block cannot be
# fixed from a backend repository. The normalisation rows name whichever
# constructor declines to convert the word back -- core's for the classes above,
# and this backend's own for the one MariaDB row, which is pinned here rather
# than changed there because its node's read contract is a decision of its own.
# Each row is pinned exactly -- the channel(s) that fail and the exception or
# mismatch they fail with -- so that the day the owning side fixes one,
# ``test_pinned_serialization_\
# gap_really_fails`` reports the row as stale and the row is deleted. A class
# that starts failing *without* a row fails its per-class assertion instead.
#
# Shape: ``fqn -> (channels, witness)``. ``channels`` is the tuple, in
# ``("dict", "json", "xml")`` order, of the channels that cannot round-trip;
# every channel not named must round-trip. ``witness`` is either a
# ``(exception type, message fragment)`` pair -- the channel raises it -- or a
# string, which is the fragment of the parameter comparison the channel fails
# instead.
SERIALIZATION_GAP = {
    # ---- the writer refuses the parameter (all three channels) -------------
    # A plain enum or a host object is not in the value vocabulary, so
    # ``encode_artifact`` refuses it by name. The members of each pair are
    # pinned by the offending type's own name, which is what disappears when
    # the writer learns to carry one.
    "rhosocial.activerecord.backend.expression.graph.ColumnsClause": (
        ("dict", "json", "xml"),
        (TypeError, "GraphColumn is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.expression.graph.GraphTableExpression": (
        ("dict", "json", "xml"),
        (TypeError, "GraphColumn is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.expression.statements.ddl_table.ColumnGeneratedConstraint": (
        ("dict", "json", "xml"),
        (TypeError, "GeneratedColumnType is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.expression.statements.ddl_table.ForeignKeyConstraint": (
        ("dict", "json", "xml"),
        (TypeError, "ReferentialAction is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.expression.statements.ddl_trigger.CreateTriggerStatement": (
        ("dict", "json", "xml"),
        (TypeError, "TriggerEvent is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.expression.statements.ddl_view.CreateViewStatement": (
        ("dict", "json", "xml"),
        (TypeError, "ViewOptions is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLAttributesExpression": (
        ("dict", "json", "xml"),
        (TypeError, "XMLAttribute is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLForestExpression": (
        ("dict", "json", "xml"),
        (TypeError, "XMLForestItem is not one of the value kinds"),
    ),
    "rhosocial.activerecord.backend.impl.mariadb.expression.load_data.MariaDBLoadDataExpression": (
        ("dict", "json", "xml"),
        (TypeError, "LoadDataOptions is not one of the value kinds"),
    ),
    # ---- the constructor refuses its own wire form (json and xml) ----------
    "rhosocial.activerecord.backend.expression.statements.ddl_table.CreateTableCloneStatement": (
        ("json", "xml"),
        (TypeError, "mode must be a CreateTableCloneMode"),
    ),
    # ---- the constructor does not normalise on read (json and xml) ---------
    # The value survives and the host type does not, so the witness is the
    # comparison the harness reports rather than an exception.
    "rhosocial.activerecord.backend.expression.graph.GraphEdge": (
        ("json", "xml"),
        "type mismatch str vs GraphEdgeDirection",
    ),
    "rhosocial.activerecord.backend.expression.graph.QuantifiedPath": (
        ("json", "xml"),
        "type mismatch str vs GraphEdgeDirection",
    ),
    "rhosocial.activerecord.backend.expression.statements.ddl_database.AlterDatabaseStatement": (
        ("json", "xml"),
        "type mismatch str vs AlterDatabaseAction",
    ),
    "rhosocial.activerecord.backend.expression.statements.dml.MergeAction": (
        ("json", "xml"),
        "type mismatch str vs MergeActionType",
    ),
    "rhosocial.activerecord.backend.expression.statements.dml.MergeStatement": (
        ("json", "xml"),
        "type mismatch str vs MergeActionType",
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLParseExpression": (
        ("json", "xml"),
        "type mismatch str vs XMLParseDocumentType",
    ),
    "rhosocial.activerecord.backend.expression.xml.XMLSerializeExpression": (
        ("json", "xml"),
        "type mismatch str vs XMLSerializeDocumentType",
    ),
    # This backend's own ``KillTarget`` takes the org's enum spelling -- a
    # ``str`` base with ``__str__`` pinned -- so the member *is* a string and
    # the writer carries it as ``string_value`` instead of refusing it by name.
    # The word survives the JSON and XML payloads and the node's constructor
    # does not normalise it back into a member, so the parameter comes back
    # as the ``str`` the wire carried. The dict channel hands the member
    # through untouched and still round-trips.
    "rhosocial.activerecord.backend.impl.mariadb.expression.admin.MariaDBKillExpression": (
        ("json", "xml"),
        "type mismatch str vs KillTarget",
    ),
    # ---- the XML channel spells a str-enum member as str(member) -----------
    # ``DateTimeField`` and ``IntervalUnit`` are str-enums, so JSON writes the
    # value and round-trips. The XML writer calls ``str()`` on the member and
    # gets the repr-shaped spelling back, which the normaliser refuses.
    "rhosocial.activerecord.backend.expression.datetime.DatePartExpression": (
        ("xml",),
        (ValueError, "unsupported datetime field: 'DateTimeField.YEAR'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime.DateTruncExpression": (
        ("xml",),
        (ValueError, "unsupported datetime field: 'DateTimeField.YEAR'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime.ExtractExpression": (
        ("xml",),
        (ValueError, "unsupported datetime field: 'DateTimeField.YEAR'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime.ExtractFieldExpression": (
        ("xml",),
        (ValueError, "unsupported datetime field: 'DateTimeField.YEAR'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime._ExtractBase": (
        ("xml",),
        (ValueError, "unsupported datetime field: 'DateTimeField.YEAR'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime.DateTimeAddExpression": (
        ("xml",),
        (ValueError, "unsupported interval unit: 'IntervalUnit.DAY'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime.DateTimeDiffExpression": (
        ("xml",),
        (ValueError, "unsupported interval unit: 'IntervalUnit.DAY'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime.DateTimeSubtractExpression": (
        ("xml",),
        (ValueError, "unsupported interval unit: 'IntervalUnit.DAY'"),
    ),
    "rhosocial.activerecord.backend.expression.datetime.IntervalExpression": (
        ("xml",),
        (ValueError, "unsupported interval unit: 'IntervalUnit.DAY'"),
    ),
}

_CHANNELS = ("dict", "json", "xml")


def _serialization_gap(fqn):
    """The pinned round-trip gap for *fqn*, or ``None`` when it has none."""
    return SERIALIZATION_GAP.get(fqn)


def _restore_channel(channel, instance, dialect):
    """Serialize *instance* and read it back through one channel."""
    if channel == "dict":
        return deserialize(serialize(instance), dialect)
    if channel == "json":
        return deserialize_json(serialize_json(instance), dialect)
    return deserialize_xml(serialize_xml(instance), dialect)


def _run_channel(fqn, channel, instance, dialect):
    """One channel's round-trip, as an outcome a caller can classify.

    Returns ``("ok", restored)``, ``("raises", exception)`` or
    ``("degrades", message)``. A channel that is not named in a class's
    :data:`SERIALIZATION_GAP` row must return the first; a channel that is
    named must return one of the other two, and the row's witness says which
    and what it must look like.
    """
    try:
        restored = _restore_channel(channel, instance, dialect)
    except Exception as exc:  # noqa: BLE001 -- classified by the caller
        return "raises", exc
    try:
        assert_params_equal(restored.get_params(), instance.get_params(), fqn)
    except AssertionError as exc:
        return "degrades", str(exc)
    return "ok", restored


def _assert_roundtrip_or_gap(fqn, instance, dialect):
    """Assert all three channels, against the pinned gap table.

    Returns ``{channel: restored}`` for the channels that round-tripped. A
    channel whose class has no pinned gap must round-trip, and a pinned
    channel must fail exactly the way its witness says -- so neither a new
    failure nor a stale row can pass quietly.
    """
    gap = _serialization_gap(fqn)
    restored_ok = {}
    failing = []
    for channel in _CHANNELS:
        outcome, detail = _run_channel(fqn, channel, instance, dialect)
        if outcome == "ok":
            restored_ok[channel] = detail
            continue
        failing.append(channel)
        if outcome == "raises":
            what = f"raised {type(detail).__name__}: {detail}"
        else:
            what = f"lost a parameter type: {detail}"
        assert gap is not None, (
            f"{fqn}: the {channel} channel {what}, and the class is not in "
            f"SERIALIZATION_GAP. If core's writer or reader learned to carry "
            f"the parameter, the row is no longer needed; if it has not, the "
            f"class needs a row naming the channel and the witness."
        )
        channels, witness = gap
        assert channel in channels, (
            f"{fqn}: the {channel} channel failed but the pinned gap names "
            f"{channels}. Either the pin is wrong about which channels fail, or "
            f"core's behaviour changed and the row must be re-measured."
        )
        if isinstance(witness, tuple):
            expected_type, fragment = witness
            assert outcome == "raises", (
                f"{fqn}: the pinned gap says the {channel} channel raises "
                f"{expected_type.__name__} saying {fragment!r}, but it {what}."
            )
            assert type(detail) is expected_type and fragment in str(detail), (
                f"{fqn}: the {channel} channel was pinned to raise "
                f"{expected_type.__name__} saying {fragment!r}, but it {what}."
            )
        else:
            assert outcome == "degrades" and witness in str(detail), (
                f"{fqn}: the pinned gap says the {channel} channel loses the "
                f"parameter type reported as {witness!r}, but it {what}."
            )
    if gap is not None:
        channels, _witness = gap
        assert set(failing) == set(channels), (
            f"{fqn}: the pinned gap names {channels} as the channels that fail, "
            f"but {failing} failed. A row that names a channel which now works "
            f"is stale and must go."
        )
    return restored_ok


# ---------------------------------------------------------------------------
# The dispatch gap: a missing formatter is a decision, not an omission
# ---------------------------------------------------------------------------
#
# ``to_sql()`` reports a dialect that names no formatter for a class through
# the same ``UnsupportedFeatureError`` a capability probe uses, so the type
# alone cannot say "this backend never wired the feature in". The frame the
# dispatch puts around the method name can, and it is the only place in the
# tree that opens it -- see :func:`_dispatched_formatter`.

#: The two ends of the frame ``to_sql()`` puts around a formatting method name
#: in the ``feature_name`` of the ``UnsupportedFeatureError`` it raises for a
#: dialect that has no such formatter.
_DISPATCH_FEATURE_PREFIX = "the '"
_DISPATCH_FEATURE_SUFFIX = "' statement"


def _dispatched_formatter(exc):
    """The formatting method *exc* says the dialect does not have, or ``None``.

    ``None`` means *exc* is not the dispatch reporting a missing formatter --
    it is a probe inside a formatter that refused a feature, which is the
    ``"unsupported"`` branch and needs no row anywhere.

    Args:
        exc: An :class:`UnsupportedFeatureError` raised out of ``to_sql()``.

    Returns:
        The method name out of the ``feature_name`` frame, or ``None`` when
        *exc* came from a probe rather than from the dispatch.
    """
    feature = exc.feature_name
    if not feature.startswith(_DISPATCH_FEATURE_PREFIX):
        return None
    if not feature.endswith(_DISPATCH_FEATURE_SUFFIX):
        return None
    method = feature[len(_DISPATCH_FEATURE_PREFIX) : len(feature) - len(_DISPATCH_FEATURE_SUFFIX)]
    return method if method else None


#: Formatters MariaDB declares no implementation of, grouped by the feature
#: that is absent, each group naming every method the matrix's classes need.
#:
#: A class needing one of these fails with ``UnsupportedFeatureError`` naming
#: the method it wanted, and :func:`assert_sql_roundtrip_classified` asserts
#: that method is a row here. :meth:`TestMatrixIntegrity.\
#: test_unmodelled_formatter_list_is_exact` pins the table in both directions:
#: a formatter that starts existing moves its classes out of the table and the
#: pin fails until the entry goes, and a class that starts needing a method
#: outside the table fails outright instead of passing as "unsupported".
#:
#: These are not defects: they are features MariaDB does not have, which the
#: shared renderer reports by naming the method it could not find. The
#: grouping is the point -- "25 methods" says nothing, "no SQL/XML, no
#: property graphs, no COMMENT ON, no PIVOT" says what the dialect is.
UNMODELLED_FORMATTERS = {
    "SQL/XML (MariaDB implements no part of SQL/XML)": (
        "format_xmlagg_expression",
        "format_xmlattributes_expression",
        "format_xmlcomment_expression",
        "format_xmlconcat_expression",
        "format_xmlelement_expression",
        "format_xmlexists_predicate",
        "format_xmlforest_expression",
        "format_xmlpi_expression",
        "format_xmlparse_expression",
        "format_xmlquery_expression",
        "format_xmlroot_expression",
        "format_xmlserialize_expression",
        "format_xmltable_expression",
        # S1-c's PASSING clause belongs to the same absent family: it carries the
        # BY VALUE / BY REF argument list the XML querying expressions pass with,
        # and MariaDB has none of them, so the dialect declares no
        # ``format_passing_clause`` either.
        "format_passing_clause",
    ),
    "SQL/PGQ property graphs (MariaDB has a MATCH predicate but no "
    "property-graph DDL and no GRAPH_TABLE)": (
        "format_alter_property_graph_statement",
        "format_create_property_graph_statement",
        "format_drop_property_graph_statement",
        "format_graph_table_expression",
        "format_graph_columns_clause",
        "format_table_properties_clause",
        "format_vertex_table",
        "format_edge_table_definition",
    ),
    "COMMENT ON (MariaDB's COMMENT is a table option and a column attribute, "
    "both rendered by this dialect; the standalone statement is not "
    "implemented)": ("format_comment_statement",),
    "PIVOT / UNPIVOT (not MariaDB syntax, and no formatter for either)": (
        "format_pivot",
        "format_unpivot",
    ),
    "the TableSource root (every concrete row source overrides its formatter; "
    "the root carries nothing but an alias and is never rendered)": ("format_table_source",),
}


def _unmodelled_methods():
    """The flat set of formatter names in :data:`UNMODELLED_FORMATTERS`."""
    return {method for methods in UNMODELLED_FORMATTERS.values() for method in methods}


# ---------------------------------------------------------------------------
# The local SQL assertion: classify the outcome instead of swallowing it
# ---------------------------------------------------------------------------


def assert_sql_roundtrip_classified(fqn, instance, dialect):
    """Assert an expression's SQL survives the round-trip, or say precisely why not.

    Four outcomes, each asserted:

    * **renders** -- every encoding whose parameters round-trip (see
      :func:`_assert_roundtrip_or_gap` for the other two) must restore
      byte-identical SQL *and* byte-identical bind parameters.
    * a member of :data:`LEGITIMATE_NON_RENDERS` -- unrenderable by design,
      asserted as its exact type *and* message fragment.
    * ``UnsupportedFeatureError`` from a class *not* named in the dict -- MariaDB
      does not model the feature. Asserted as exactly that type, so a subclass
      raised for an unrelated reason is still visible rather than passing.
    * ``UnsupportedFeatureError`` naming a formatting method, for a class not
      named in the dict -- the dispatch found nothing, which is a wiring fact
      about this backend rather than a capability answer. The method must be
      in :data:`UNMODELLED_FORMATTERS`; the table entry is the reason.
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
    # The artifact half first, and it decides which channels the SQL half may
    # compare: a channel whose parameters cannot round-trip cannot be asked
    # whether the *SQL* survived, and pretending otherwise would fail the
    # render assertion for a defect the gap table already names. Both halves
    # classify rather than swallow -- see :data:`SERIALIZATION_GAP`.
    restored_ok = _assert_roundtrip_or_gap(fqn, instance, dialect)

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
            method = _dispatched_formatter(exc)
            if method is not None:
                assert method in _unmodelled_methods(), (
                    f"{fqn}: to_sql() reported that {exc.dialect_name} declares no "
                    f"{method!r}, which is not in UNMODELLED_FORMATTERS.\n"
                    f"  Either MariaDB now needs that formatter -- in which case "
                    f"the class should render and this entry should go -- or the "
                    f"feature is absent and the method belongs in that table with "
                    f"its reason."
                )
                return "unmodelled"
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

    for channel in _CHANNELS:
        if channel not in restored_ok:
            continue
        decoded = _restore_channel(channel, instance, dialect)
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
        """Every parameter survives all three channels -- or its gap is pinned.

        A channel that fails for a class with no row in
        :data:`SERIALIZATION_GAP` fails here, and so does a row that names a
        channel which now round-trips. See the table's comment for what the
        rows are and whose defect they record.
        """
        fqn, instance = expr_case
        _assert_roundtrip_or_gap(fqn, instance, mariadb_dialect)

    def test_to_sql_roundtrip_classified(self, expr_case, mariadb_dialect):
        """A render must survive the round-trip; a non-render must be classified."""
        fqn, instance = expr_case
        assert_sql_roundtrip_classified(fqn, instance, mariadb_dialect)


class TestLiteralValueKinds:
    """One node carries every value, and the value names the kind.

    The twelve ``*Value`` classes are gone from core; what replaced them is a
    single :class:`Literal` whose *kind* is derived from the value it carries,
    so the artifact says ``{"kind": "integer_value", ...}`` rather than naming
    a class. That makes the value vocabulary the artifact's contract, and this
    is where it is pinned: every kind travels as a plain JSON scalar with the
    spelling its own kind declares -- ``bytes`` as base64 text, ``timedelta``
    as ISO 8601 duration text, ``Decimal`` as exact text -- and a kind that
    has no scalar spelling is refused rather than guessed at.
    """

    #: (member value, wire spelling of its payload) for each of the fourteen
    #: value kinds, plus the two non-finite kinds that split off ``float``.
    CASES = [
        (None, None, "null_value"),
        (True, True, "boolean_value"),
        (42, 42, "integer_value"),
        (1.5, 1.5, "float_value"),
        (float("nan"), "nan", "nan_value"),
        (float("inf"), "+inf", "infinity_value"),
        (float("-inf"), "-inf", "infinity_value"),
        (decimal.Decimal("1.25"), "1.25", "decimal_value"),
        ("x'y", "x'y", "string_value"),
        (b"\x01\x02\xff", "AQL/", "binary_value"),
        (datetime.datetime(2026, 10, 17, 10, 0, 0),
         "2026-10-17 10:00:00", "timestamp_value"),
        (datetime.date(2026, 10, 17), "2026-10-17", "date_value"),
        (datetime.time(10, 30), "10:30:00", "time_value"),
        (datetime.timedelta(days=1, seconds=2, microseconds=3),
         "P1DT2.000003S", "interval_value"),
        ([1, 2], [1, 2], "list_value"),
        ((1, 2), [1, 2], "tuple_value"),
        (uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
         "550e8400-e29b-41d4-a716-446655440000", "uuid_value"),
    ]

    @pytest.mark.parametrize(
        "value, wire, kind",
        CASES,
        ids=[case[2] for case in CASES],
    )
    def test_each_kind_travels_as_its_own_scalar(
        self, mariadb_dialect, value, wire, kind
    ):
        expr = Literal(mariadb_dialect, value)
        artifact = serialize(expr)
        assert set(artifact) == {"kind", "params"}, (
            f"{kind}: a bare node carries exactly 'kind' and 'params', got "
            f"{sorted(artifact)}"
        )
        assert artifact["kind"] == kind
        # ``inline`` rides as a plain parameter, like every other one: the
        # bind-or-inline decision belongs to the node, not to the artifact.
        assert artifact["params"] == {"value": wire, "inline": False}
        json.loads(serialize_json(expr))  # the scalar is JSON-native, so this holds

    def test_the_vocabulary_is_closed(self, mariadb_dialect):
        """A host type no kind names is refused, not guessed at."""
        from rhosocial.activerecord.backend.expression.values import LiteralKind

        declared = {member.wire for member in LiteralKind}
        pinned = {case[2] for case in self.CASES}
        assert declared == pinned, (
            "the value vocabulary moved: the pinned kinds are "
            f"{sorted(pinned)}, the enum declares {sorted(declared)}. Add or "
            f"remove a case here rather than letting the two drift."
        )

    def test_a_value_without_a_kind_is_refused_by_name(self, mariadb_dialect):
        """A host type no kind names builds and binds, but writes no artifact.

        Construction asks which kind the value *could* be and is refused only
        when that is answerable and wrong; serialization is the layer that
        actually cannot proceed, and it says so by naming the type. A value
        the artifact cannot carry must not reach the wire under a guessed
        spelling.
        """

        class _Unmodelled:
            pass

        from rhosocial.activerecord.backend.expression.serialization import (
            ArtifactError,
        )

        expr = Literal(mariadb_dialect, _Unmodelled())
        assert expr.to_sql() == ("%s", (expr.value,))
        with pytest.raises(ArtifactError, match="has no value kind"):
            serialize(expr)

    def test_non_finite_floats_bind_and_never_inline(self, mariadb_dialect):
        """NaN and +/-Inf carry, and no spelling of them reaches SQL text."""
        for value in (float("nan"), float("inf"), float("-inf")):
            bound = Literal(mariadb_dialect, value)
            assert bound.to_sql() == ("%s", (value,))
            with pytest.raises(ValueError):
                Literal(mariadb_dialect, value, inline=True).to_sql()


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

    def test_serialization_gap_entries_are_real_classes(self):
        """Every pinned round-trip gap names a class that was collected."""
        unknown = set(SERIALIZATION_GAP) - set(REGISTERED)
        assert not unknown, (
            f"SERIALIZATION_GAP names classes that were not registered: "
            f"{sorted(unknown)}"
        )

    def test_pinned_serialization_gap_really_fails(self, mariadb_dialect):
        """Each pinned row still fails the way it claims, on the channels it names.

        The mirror of :meth:`test_pinned_non_render_really_does_not_render`,
        for the artifact half. A row whose class now round-trips -- because
        core's writer, reader or constructor was fixed -- is stale, and this
        is where that is said. Every entry is checked before asserting, so a
        run reports all of the rows that have drifted.
        """
        stale = []
        for fqn, (channels, witness) in SERIALIZATION_GAP.items():
            instance, source = make_instance(REGISTERED[fqn], mariadb_dialect)
            if instance is None:
                stale.append(f"{fqn} ({source})")
                continue
            observed = {
                channel: _run_channel(fqn, channel, instance, mariadb_dialect)
                for channel in _CHANNELS
            }
            failing = tuple(
                channel
                for channel in _CHANNELS
                if observed[channel][0] != "ok"
            )
            if set(failing) != set(channels):
                stale.append(
                    f"{fqn}: pinned as failing on {channels}, but {failing} fail"
                )
                continue
            for channel in channels:
                outcome, detail = observed[channel]
                if isinstance(witness, tuple):
                    expected_type, fragment = witness
                    if outcome != "raises" or type(detail) is not expected_type:
                        stale.append(
                            f"{fqn}: {channel} pinned to raise "
                            f"{expected_type.__name__}, gave {outcome}"
                        )
                    elif fragment not in str(detail):
                        stale.append(
                            f"{fqn}: {channel} pinned to say {fragment!r}, "
                            f"said: {detail}"
                        )
                elif outcome != "degrades" or witness not in str(detail):
                    stale.append(
                        f"{fqn}: {channel} pinned to lose the type reported as "
                        f"{witness!r}, gave {outcome}: {detail}"
                    )
        assert not stale, (
            "SERIALIZATION_GAP rows that no longer describe reality:\n  "
            + "\n  ".join(stale)
            + "\n  Delete the rows that now round-trip -- core was fixed -- and "
            "re-measure the ones whose channels changed."
        )

    def test_unmodelled_formatter_list_is_exact(self, mariadb_dialect):
        """Pin the unmodelled-formatter table against what the dialect lacks.

        Observed rather than assumed: for each class the matrix covers, either
        it renders or it fails, and every dispatch refusal is attributed to the
        method it named -- including the classes pinned in
        :data:`LEGITIMATE_NON_RENDERS`, whose dispatch failures those pins
        record class by class. Then the table is compared with the set
        observed, in both directions, so:

        * a method in the table that MariaDB now implements fails here,
          because its classes render and are no longer attributed to it --
          which is the moment to delete the entry rather than leave a lie in
          the table;
        * a class that starts needing a method outside the table fails the
          per-class assertion in :func:`assert_sql_roundtrip_classified`
          instead of being absorbed into "unsupported".

        This is the regression test for the pad/trim incident. Core turned
        ``trim``/``lpad``/``rpad``/``repeat`` into dedicated nodes, and a
        backend that mixed in no formatter for one of them would have shipped
        a silent ``UnsupportedFeatureError`` on every ``.lpad(...)`` while this
        matrix stayed green, because the blanket ``unsupported`` branch
        allowed the dispatch's refusal exactly as it allows a probe's. The
        dispatch names the method it wanted; this test makes that name
        load-bearing on both sides of the table.
        """
        observed = set()
        for fqn in sorted(REGISTERED):
            instance, source = make_instance(REGISTERED[fqn], mariadb_dialect)
            if instance is None:
                continue
            try:
                instance.to_sql()
            except UnsupportedFeatureError as exc:
                method = _dispatched_formatter(exc)
                if method is not None:
                    observed.add(method)
                continue
            except Exception:
                continue

        declared = _unmodelled_methods()
        assert not (observed - declared), (
            "classes need formatters that are not in UNMODELLED_FORMATTERS: "
            f"{sorted(observed - declared)}. Add each with the feature that is "
            f"absent and why -- or mix the formatter in, in which case the "
            f"classes render and the entry is not needed."
        )
        assert not (declared - observed), (
            "UNMODELLED_FORMATTERS names formatters no class actually needs: "
            f"{sorted(declared - observed)}. MariaDB may have gained one of "
            f"these, in which case the classes needing it now render and the "
            f"entry should go."
        )

    def test_matrix_covers_both_packages_completely(self):
        """The matrix covers every concrete class both packages define.

        Re-walked here rather than trusting the module-level collection, so a
        class that appeared after import is caught. The package walk is used
        rather than the registry because the registry also holds whatever
        backends other test modules happened to import.
        """
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

        Deserialization resolves a kind to its class through the framework's
        default registry, so a class the matrix covers but the registry
        cannot resolve would round-trip into nothing.
        """
        from rhosocial.activerecord.backend.expression.registry import (
            RegistryError,
        )
        from rhosocial.activerecord.backend.expression.serialization import (
            default_registry,
        )

        registry = default_registry()
        unresolved = []
        for fqn, cls in REGISTERED.items():
            try:
                registry.resolve_node(cls.kind())
            except RegistryError:
                unresolved.append(fqn)
        assert not unresolved, (
            f"the matrix covers classes the registry cannot resolve: "
            f"{sorted(unresolved)}"
        )

    def test_coverage_report(self, mariadb_dialect):
        """Surface what the matrix covers, so coverage stays transparent.

        Counts are printed rather than asserted. An asserted ceiling would
        absorb a new gap silently, which is the failure mode this file exists to
        remove -- so the direction of the check here is a floor in
        ``test_matrix_covers_both_packages_completely`` and nothing else.
        """
        buckets = {
            "rendered": 0,
            "unsupported": 0,
            "unmodelled": 0,
            "non-render": 0,
            "unconstructible": 0,
            "serialization-gap": 0,
        }
        for fqn in sorted(REGISTERED):
            instance, _ = make_instance(REGISTERED[fqn], mariadb_dialect)
            if instance is None:
                buckets["unconstructible"] += 1
                continue
            buckets[assert_sql_roundtrip_classified(fqn, instance, mariadb_dialect)] += 1
            if _serialization_gap(fqn) is not None:
                # Counted beside the render verdict rather than instead of it:
                # these classes do render, and what they cannot do is carry
                # their own artifact on the channels the gap names.
                buckets["serialization-gap"] += 1
        print(
            f"\nexpression matrix: {len(REGISTERED)} registered, "
            f"{buckets['rendered']} render and round-trip, "
            f"{buckets['unsupported']} UnsupportedFeatureError from a probe, "
            f"{buckets['unmodelled']} from the dispatch (pinned in "
            f"UNMODELLED_FORMATTERS), "
            f"{buckets['non-render']} pinned non-render, "
            f"{buckets['serialization-gap']} with a pinned round-trip gap "
            f"(SERIALIZATION_GAP), "
            f"{buckets['unconstructible']} pinned unconstructible"
        )
        for feature, methods in sorted(UNMODELLED_FORMATTERS.items()):
            print(f"  not modelled: {feature} ({len(methods)} formatters)")
