# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/dialect/test_mariadb_artifact_registry.py
"""The MariaDB backend owns its artifact registry, and nobody else's.

An expression artifact is data: parameters only, no dialect. The dialect is
only needed to render, so a read does not require one, and a registry is the
only name authority a read needs.

Ownership follows that split:

* core assembles core's kinds (``core_registry()``);
* a backend assembles its own kinds on top of core's by composition
  (``registry_for_packages(<its package>, base=core_registry())``), never by
  core listing backends and never by merging two backends;
* an assembled registry is frozen and cached, so two readers of the same
  published table cannot change each other's answers.

These tests state those facts for MariaDB directly, plus the selection
``deserialize`` uses when it has to pick a table: an explicit registry, then
``dialect.artifact_registry()``, then ``core_registry()``.
"""

import pytest

from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.operators import (
    RawSQL,
    RawSQLPredicate,
)
from rhosocial.activerecord.backend.expression.registry import (
    RegistryError,
    RegistryReason,
)
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionDeserializationError,
    core_registry,
    deserialize,
    deserialize_json,
    serialize,
    serialize_json,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.partition import (
    MariaDBExchangePartitionStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.registry import backend_registry

VERSION = (10, 6, 0)


def _dialect() -> MariaDBDialect:
    return MariaDBDialect(VERSION)


def _exchange(dialect):
    return MariaDBExchangePartitionStatement(
        dialect,
        Table(dialect, "probe_part"),
        "p0",
        Table(dialect, "probe_exch"),
        without_validation=True,
    )


# ---------------------------------------------------------------------------
# The table is core's kinds plus MariaDB's, and nothing else
# ---------------------------------------------------------------------------


def test_the_dialect_answers_with_the_backend_registry():
    """One cached, frozen instance is what every reader of MariaDB gets."""
    registry = backend_registry()
    assert registry is backend_registry()
    assert registry.is_frozen
    assert _dialect().artifact_registry() is registry


def test_core_kinds_are_the_overlap():
    """Core's kinds resolve through MariaDB's table by composition."""
    registry = backend_registry()
    assert registry.resolve_node("column") is Column
    assert registry.resolve_node("query_statement").__name__ == "QueryStatement"


def test_declaring_a_formatter_is_what_registers_a_class():
    """The assembly walk admits a node by its declaration, not a manual list.

    These are the kinds that used to render themselves through a ``to_sql``
    override, which the walk cannot see. Now each declares ``format_method``,
    so the one assembly entry point discovers it and the published table
    answers it without any registration site naming it.
    """
    from rhosocial.activerecord.backend.impl.mariadb.expression.admin import (
        MariaDBCreateUserStatement,
        MariaDBFlushStatement,
        MariaDBShutdownStatement,
    )
    from rhosocial.activerecord.backend.impl.mariadb.expression.load_data import (
        MariaDBLoadDataStatement,
    )
    from rhosocial.activerecord.backend.impl.mariadb.expression.rename_table import (
        MariaDBRenameTableStatement,
    )
    from rhosocial.activerecord.backend.impl.mariadb.expression.routine import (
        MariaDBCallStatement,
    )
    from rhosocial.activerecord.backend.impl.mariadb.expression.show import (
        MariaDBShowCreateTableStatement,
        MariaDBShowWarningsStatement,
    )

    registry = backend_registry()
    for cls in (
        MariaDBFlushStatement,
        MariaDBShutdownStatement,
        MariaDBCreateUserStatement,
        MariaDBLoadDataStatement,
        MariaDBRenameTableStatement,
        MariaDBCallStatement,
        MariaDBShowCreateTableStatement,
        MariaDBShowWarningsStatement,
    ):
        assert registry.resolve_node(cls.kind()) is cls, (
            f"{cls.__name__} declares format_method and must be discovered by "
            f"registry_for_packages; a manual registration entry is redundant"
        )


def test_a_foreign_backend_kind_is_refused_by_name():
    """SQLite's kinds are SQLite's; MariaDB's table does not list them.

    The foreign kind is named as data: importing another backend's expression
    module here would make MariaDB's tests depend on that backend's internals.
    """
    foreign = "sqlite_vacuum_statement"
    assert foreign not in backend_registry().node_kinds()
    assert foreign not in core_registry().node_kinds()

    with pytest.raises(RegistryError) as caught:
        backend_registry().resolve_node(foreign)
    assert caught.value.reason is RegistryReason.KIND_NOT_REGISTERED
    assert foreign in str(caught.value)


def test_the_published_table_refuses_mutation_by_name():
    """A published table is a value: widening it is a new registry, not an edit."""
    registry = backend_registry()

    with pytest.raises(RegistryError) as caught:
        registry.register_node(MariaDBExchangePartitionStatement)
    assert caught.value.reason is RegistryReason.REGISTRY_FROZEN
    assert "mariadb_exchange_partition_statement" in str(caught.value)
    assert "frozen" in str(caught.value)

    assert registry.freeze() is registry  # idempotent


# ---------------------------------------------------------------------------
# A MariaDB-owned kind is read through the dialect's table
# ---------------------------------------------------------------------------


def test_a_mariadb_kind_resolves_through_the_dialect():
    """The backend's own kind is the backend's own table's to answer."""
    dialect = _dialect()
    kind = MariaDBExchangePartitionStatement.kind()
    assert kind == "mariadb_exchange_partition_statement"
    assert dialect.artifact_registry().resolve_node(kind) is MariaDBExchangePartitionStatement


def test_deserialize_reads_a_mariadb_artifact_through_the_dialect():
    """A MariaDB artifact round-trips without anyone registering its class."""
    # 11.4 is the first release whose grammar accepts either EXCHANGE PARTITION
    # validation spelling, so the render comparison is measured, not assumed.
    dialect = MariaDBDialect((11, 4, 0))
    expr = _exchange(dialect)

    decoded = deserialize_json(serialize_json(expr), dialect)
    assert isinstance(decoded, MariaDBExchangePartitionStatement)
    assert decoded.without_validation is True
    assert decoded.to_sql() == expr.to_sql()


def test_without_a_dialect_core_refuses_the_mariadb_kind():
    """The fallback is core's table, which owns no backend kind."""
    dialect = _dialect()
    artifact = serialize(_exchange(dialect))

    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact)
    assert "mariadb_exchange_partition_statement" in str(caught.value)


# ---------------------------------------------------------------------------
# Trusted opt-ins are a caller's twin, never a shared table
# ---------------------------------------------------------------------------


def test_trusted_opt_ins_are_registered_on_a_twin():
    """``RawSQL``/``RawSQLPredicate`` are caller-vouched, so the caller copies."""
    published = backend_registry()
    for cls in (RawSQL, RawSQLPredicate):
        assert cls.kind() not in published.node_kinds(), (
            "core keeps raw SQL out of the assembled tables because the SQL is "
            "the caller's, not the artifact's"
        )

    view = published.twin()
    assert not view.is_frozen
    for cls in (RawSQL, RawSQLPredicate):
        view.register_node(cls)
        assert view.resolve_node(cls.kind()) is cls

    view.freeze()
    assert view.is_frozen
    # The widening lives in the caller's copy: the published table is unchanged.
    for cls in (RawSQL, RawSQLPredicate):
        with pytest.raises(RegistryError):
            published.resolve_node(cls.kind())
