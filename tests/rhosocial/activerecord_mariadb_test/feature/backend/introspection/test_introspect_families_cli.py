# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspect_families_cli.py
"""The nine families the MySQL and PostgreSQL CLIs ask, as this one asks them.

No server is needed here. What is checked is the wiring the CLI owns: that
each type reaches its introspector method, that NAME and the type-specific
flags arrive as arguments rather than being parsed and dropped, and that a
family the connected server refuses is refused. Whether the answer is right
is the introspector's question, and the live tests carry it.

Three of the nine are not answered by MariaDB at all -- its performance
schema registers no table I/O summary, so there is no per-index or per-table
use counter to read -- and those probes answer ``False`` on the real dialect,
so the CLI refuses the run with exit 2. That is asserted here twice, because
a False probe is the whole point: it is what keeps a rendered statement from
naming an object this engine has never shipped. The runtime family is
answered from ``setup_instruments`` and gated on 10.5, the release that
brought the performance schema. The six answered families run their branches
against a stub whose dialect says yes, which is how the wiring is separated
from the engine's answer.
"""

import argparse
import json
from typing import Optional

import pytest

from rhosocial.activerecord.backend.impl.mariadb.cli import introspect as introspect_cli
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.introspection.types import (
    ColumnDataProfile,
    ColumnValueFrequency,
    DDLStatement,
    JoinCoverage,
)

#: The nine families this change wires, and the switch that gates each.
NEW_FAMILIES = {
    "unused-indexes": "supports_unused_indexes_detection",
    "table-stats": "supports_table_stats",
    "runtime": "supports_runtime_stats",
    "index-stats": "supports_index_stats",
    "dependencies": "supports_object_dependencies",
    "ddl": "supports_ddl_extraction",
    "column-profiles": "supports_column_data_profile",
    "value-samples": "supports_column_value_sample",
    "join-coverage": "supports_join_coverage",
}

#: The four families that answer for the whole database and take no NAME.
WHOLE_DATABASE_FAMILIES = (
    "unused-indexes",
    "table-stats",
    "runtime",
    "index-stats",
)

#: The three families MariaDB does not answer, and the reason the dialect
#: records. The probe answers False on every release this backend supports,
#: so there is no floor to assert across -- only that the dialect says no.
UNANSWERED_FAMILIES = (
    "unused-indexes",
    "table-stats",
    "index-stats",
)

#: A modern MariaDB. The runtime family's floor is the only version boundary
#: among the nine, and the matrix runs 10.2 through 13.x.
MARIA_VERSION = (11, 8, 0)

#: The last release before the performance schema, which is what the runtime
#: family reads. Below it the probe must refuse rather than render a statement
#: naming a relation the server does not serve.
PRE_PERFORMANCE_SCHEMA = (10, 4, 0)


class _RecordingIntrospector:
    """Records each introspection call, and returns what the test declared.

    ``__getattr__`` is the whole implementation: a test names the method once,
    in the assertion, and a branch that reaches a different one fails on the
    recorded name rather than on an attribute error that would hide the typo.
    """

    def __init__(self, results: Optional[dict] = None) -> None:
        self.results = results or {}
        self.calls = []

    def __getattr__(self, name: str):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.results.get(name)

        return call


class _AsyncRecordingIntrospector(_RecordingIntrospector):
    """The async shape of the same recorder: methods are awaited, calls are not."""

    def __getattr__(self, name: str):
        async def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.results.get(name)

        return call


def _args(type_: str, name: Optional[str] = None, **overrides) -> argparse.Namespace:
    """The attributes a parsed invocation carries, with sane defaults."""
    values = dict(
        output="json",
        rich_ascii=False,
        type=type_,
        name=name,
        database="mydb",
        is_async=False,
        named_connection=None,
        include_system=False,
        column=None,
        limit=None,
        left_table=None,
        left_column=None,
        right_table=None,
        right_column=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _run_sync(monkeypatch, introspector, args) -> None:
    """Drive the sync chain against a stub whose dialect answers yes.

    The stub installs its dialect in ``introspect_and_adapt`` the way the real
    backend does, so the capability question is answered from an adapted
    dialect rather than from a bare one.
    """
    class _Backend:
        dialect = MariaDBDialect()
        _connection = None

        def __init__(self, **_kwargs) -> None:
            self.introspector = introspector

        def connect(self) -> None:
            pass

        def introspect_and_adapt(self) -> None:
            self.dialect = _AnsweringDialect()

        def disconnect(self) -> None:
            pass

    monkeypatch.setattr(introspect_cli, "MariaDBBackend", _Backend)
    monkeypatch.setattr(
        introspect_cli, "resolve_connection_config_from_args", lambda _args: None
    )
    introspect_cli.handle(args)


def _run_async(monkeypatch, introspector, args) -> None:
    class _Backend:
        dialect = MariaDBDialect()
        _connection = None

        def __init__(self, **_kwargs) -> None:
            self.introspector = introspector

        async def connect(self) -> None:
            pass

        async def introspect_and_adapt(self) -> None:
            self.dialect = _AnsweringDialect()

        async def disconnect(self) -> None:
            pass

    monkeypatch.setattr(introspect_cli, "AsyncMariaDBBackend", _Backend)
    monkeypatch.setattr(
        introspect_cli, "resolve_connection_config_from_args", lambda _args: None
    )
    args.is_async = True
    introspect_cli.handle(args)


class _AnsweringDialect(MariaDBDialect):
    """MariaDB's dialect with the three unanswered probes turned on.

    The branch tests drive the dispatch, not the engine's answer, so the
    switches the real dialect refuses are answered here. That this is a
    *different* dialect from the one a run meets is the point:
    :class:`TestTheFourUnansweredFamilies` below asserts what the real one
    says.
    """

    def supports_unused_indexes_detection(self) -> bool:
        return True

    def supports_table_stats(self) -> bool:
        return True

    def supports_runtime_stats(self) -> bool:
        return True

    def supports_index_stats(self) -> bool:
        return True


class TestTheSchemaWideFamilies:
    """The counters and listings describe the database, so NAME is refused."""

    @pytest.mark.parametrize(
        "type_, method",
        [
            ("unused-indexes", "list_unused_indexes"),
            ("table-stats", "list_table_usage_stats"),
            ("runtime", "list_runtime_metrics"),
            ("index-stats", "list_index_usage_stats"),
        ],
    )
    def test_the_family_asks_its_method_for_the_whole_schema(
        self, type_, method, monkeypatch
    ):
        introspector = _RecordingIntrospector({method: []})

        _run_sync(monkeypatch, introspector, _args(type_))

        assert introspector.calls == [(method, (), {"schema": None})]

    @pytest.mark.parametrize("type_", WHOLE_DATABASE_FAMILIES)
    def test_a_name_is_refused(self, type_, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_name(_args(type_, "orders"))

        assert excinfo.value.code == 2
        assert "takes no name" in capsys.readouterr().err


class TestTheDependenciesBranch:
    """One optional NAME narrows the graph; omitting it asks for all of it."""

    def test_a_named_object_is_asked_for_by_name(self, monkeypatch):
        introspector = _RecordingIntrospector({"list_object_dependencies": []})

        _run_sync(monkeypatch, introspector, _args("dependencies", "posts"))

        assert introspector.calls == [
            ("list_object_dependencies", (), {"object_name": "posts", "schema": None})
        ]

    def test_an_unnamed_run_asks_for_the_whole_graph(self, monkeypatch):
        introspector = _RecordingIntrospector({"list_object_dependencies": []})

        _run_sync(monkeypatch, introspector, _args("dependencies"))

        assert introspector.calls == [
            ("list_object_dependencies", (), {"object_name": None, "schema": None})
        ]


class TestTheDdlBranch:
    """The schema object, not a name, is what a caller parses."""

    def _statement(self) -> DDLStatement:
        return DDLStatement(
            schema="mydb",
            object_type="TABLE",
            object_name="orders",
            ddl="CREATE TABLE `orders` (`id` int)",
            native=True,
        )

    def test_the_table_is_asked_for_by_name(self, monkeypatch):
        introspector = _RecordingIntrospector({"get_ddl_statement": self._statement()})

        _run_sync(monkeypatch, introspector, _args("ddl", "orders"))

        assert introspector.calls == [
            ("get_ddl_statement", ("orders",), {"schema": None})
        ]

    def test_the_engine_text_reaches_json_with_its_native_flag(
        self, monkeypatch, capsys
    ):
        introspector = _RecordingIntrospector({"get_ddl_statement": self._statement()})

        _run_sync(monkeypatch, introspector, _args("ddl", "orders"))

        payload = json.loads(capsys.readouterr().out)
        assert payload[0]["object_name"] == "orders"
        assert payload[0]["ddl"] == "CREATE TABLE `orders` (`id` int)"
        assert payload[0]["native"] is True

    def test_no_ddl_is_an_error_not_an_empty_listing(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector({"get_ddl_statement": None})

        with pytest.raises(SystemExit) as excinfo:
            _run_sync(monkeypatch, introspector, _args("ddl", "orders"))

        assert excinfo.value.code == 1
        assert "not available" in capsys.readouterr().err


class TestTheColumnProfilesBranch:
    """The aggregate label must reach the reader; the numbers are not a catalogue."""

    def _profile(self) -> ColumnDataProfile:
        return ColumnDataProfile(
            schema="mydb",
            table_name="orders",
            column_name="status",
            null_fraction=0.0,
            distinct_count=3,
            row_count=120,
            source="aggregate",
        )

    def test_the_table_is_asked_for_by_name(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector(
            {"list_column_data_profiles": [self._profile()]}
        )

        _run_sync(monkeypatch, introspector, _args("column-profiles", "orders"))

        assert introspector.calls == [
            ("list_column_data_profiles", ("orders",), {"schema": None})
        ]

    def test_the_run_says_the_numbers_are_aggregated(self, monkeypatch, capsys):
        """Exact and expensive, on stderr so the JSON on stdout stays parseable."""
        introspector = _RecordingIntrospector(
            {"list_column_data_profiles": [self._profile()]}
        )

        _run_sync(monkeypatch, introspector, _args("column-profiles", "orders"))

        captured = capsys.readouterr()
        assert "aggregate" in captured.err
        assert "full scan" in captured.err
        payload = json.loads(captured.out)
        assert payload[0]["source"] == "aggregate"

    def test_the_note_is_not_mistaken_for_a_result_row(self, monkeypatch, capsys):
        """The note belongs on stderr; a line on stdout would break every parser."""
        introspector = _RecordingIntrospector(
            {"list_column_data_profiles": [self._profile()]}
        )

        _run_sync(monkeypatch, introspector, _args("column-profiles", "orders"))

        out = capsys.readouterr().out
        assert out.lstrip().startswith("[")


class TestTheValueSamplesBranch:
    """A table and a column, and a limit that the introspector receives."""

    def test_the_table_column_and_limit_reach_the_introspector(self, monkeypatch):
        introspector = _RecordingIntrospector(
            {"sample_column_values": [ColumnValueFrequency(value="paid", count=7)]}
        )

        _run_sync(
            monkeypatch,
            introspector,
            _args("value-samples", "orders", column="status", limit=20),
        )

        assert introspector.calls == [
            (
                "sample_column_values",
                ("orders", "status"),
                {"limit": 20, "schema": None},
            )
        ]

    def test_no_limit_is_sent_when_the_flag_is_omitted(self, monkeypatch):
        introspector = _RecordingIntrospector({"sample_column_values": []})

        _run_sync(
            monkeypatch, introspector, _args("value-samples", "orders", column="status")
        )

        # Absent ``--limit`` means absent from the call: the introspector's own
        # signature answers with its own default, and the CLI does not restate
        # it. A number here would fail the day the signature's default moved.
        assert "limit" not in introspector.calls[0][2]

    def test_a_missing_column_is_an_incomplete_invocation(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_options(_args("value-samples", "orders"))

        assert excinfo.value.code == 1
        assert "--column" in capsys.readouterr().err


class TestTheJoinCoverageBranch:
    """Four names, both sides of the measurement, in the order they are asked."""

    def _coverage(self) -> JoinCoverage:
        return JoinCoverage(
            left_schema="mydb",
            left_table="orders",
            left_column="customer_id",
            right_schema="mydb",
            right_table="customers",
            right_column="id",
            left_coverage=1.0,
            right_coverage=0.75,
        )

    def test_the_four_names_reach_the_introspector(self, monkeypatch):
        introspector = _RecordingIntrospector(
            {"estimate_join_coverage": self._coverage()}
        )

        _run_sync(
            monkeypatch,
            introspector,
            _args(
                "join-coverage",
                left_table="orders",
                left_column="customer_id",
                right_table="customers",
                right_column="id",
            ),
        )

        assert introspector.calls == [
            (
                "estimate_join_coverage",
                ("orders", "customer_id", "customers", "id"),
                {"schema": None},
            )
        ]

    def test_both_fractions_are_reported(self, monkeypatch, capsys):
        introspector = _RecordingIntrospector(
            {"estimate_join_coverage": self._coverage()}
        )

        _run_sync(
            monkeypatch,
            introspector,
            _args(
                "join-coverage",
                left_table="orders",
                left_column="customer_id",
                right_table="customers",
                right_column="id",
            ),
        )

        payload = json.loads(capsys.readouterr().out)
        assert payload[0]["left_coverage"] == 1.0
        assert payload[0]["right_coverage"] == 0.75

    def test_missing_names_are_listed_together(self, capsys):
        """One run should name every absent flag, not the first one it met."""
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_options(
                _args(
                    "join-coverage",
                    left_table="orders",
                    right_table="customers",
                )
            )

        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "--left-column" in err
        assert "--right-column" in err

    def test_an_unmeasurable_pair_is_an_error(self, monkeypatch, capsys):
        """``None`` is "not measured", which is not a zero-overlap answer."""
        introspector = _RecordingIntrospector({"estimate_join_coverage": None})

        with pytest.raises(SystemExit) as excinfo:
            _run_sync(
                monkeypatch,
                introspector,
                _args(
                    "join-coverage",
                    left_table="orders",
                    left_column="customer_id",
                    right_table="customers",
                    right_column="id",
                ),
            )

        assert excinfo.value.code == 1
        assert "could not measure" in capsys.readouterr().err


class TestTheArgumentRules:
    def test_a_flag_the_type_does_not_read_is_refused(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_options(_args("tables", column="status"))

        assert excinfo.value.code == 2
        assert "takes no --column" in capsys.readouterr().err

    def test_a_required_name_is_required_for_the_new_families(self, capsys):
        for type_ in ("ddl", "column-profiles", "value-samples"):
            with pytest.raises(SystemExit) as excinfo:
                introspect_cli._validate_name(_args(type_))
            assert excinfo.value.code == 1
        assert "required" in capsys.readouterr().err


class TestTheCapabilityGate:
    """A family the dialect refuses is refused before the introspector runs."""

    @pytest.mark.parametrize("type_, switch", list(NEW_FAMILIES.items()))
    def test_a_family_the_server_refuses_exits_two(self, type_, switch, capsys):
        class _Dialect:
            pass

        setattr(_Dialect, switch, staticmethod(lambda: False))

        class _Backend:
            dialect = _Dialect()

        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._require_capability(_args(type_), _Backend())

        assert excinfo.value.code == 2
        assert "not supported by this server" in capsys.readouterr().err


class TestTheAsyncPath:
    """The second dispatch chain must ask the same question the first one does."""

    @pytest.mark.parametrize(
        "type_, method, args_kwargs, expected",
        [
            ("unused-indexes", "list_unused_indexes", {}, ((), {"schema": None})),
            (
                "dependencies",
                "list_object_dependencies",
                {"name": "orders"},
                ((), {"object_name": "orders", "schema": None}),
            ),
            (
                "ddl",
                "get_ddl_statement",
                {"name": "orders"},
                (("orders",), {"schema": None}),
            ),
            (
                "column-profiles",
                "list_column_data_profiles",
                {"name": "orders"},
                (("orders",), {"schema": None}),
            ),
            (
                "value-samples",
                "sample_column_values",
                {"name": "orders", "column": "status", "limit": 5},
                (("orders", "status"), {"limit": 5, "schema": None}),
            ),
            (
                "join-coverage",
                "estimate_join_coverage",
                {
                    "left_table": "orders",
                    "left_column": "customer_id",
                    "right_table": "customers",
                    "right_column": "id",
                },
                (
                    ("orders", "customer_id", "customers", "id"),
                    {"schema": None},
                ),
            ),
        ],
    )
    def test_the_async_branch_calls_the_same_method_with_the_same_arguments(
        self, type_, method, args_kwargs, expected, monkeypatch
    ):
        introspector = _AsyncRecordingIntrospector({method: []})

        _run_async(monkeypatch, introspector, _args(type_, **args_kwargs))

        assert introspector.calls == [(method, expected[0], expected[1])]


class TestTheTypeSurfaceExtension:
    def test_each_new_family_has_a_switch_the_dialect_declares(self):
        for type_, switch in NEW_FAMILIES.items():
            assert introspect_cli._TYPE_CAPABILITIES[type_] == switch
            assert hasattr(MariaDBDialect, switch)


class TestTheFamiliesMariaDBCannotAnswer:
    """The families MariaDB cannot answer say so, on every release.

    MySQL answers unused-indexes, table-stats and index-stats from
    ``sys``/performance-schema table I/O summaries; MariaDB carries the
    ``sys`` view definitions but its performance schema registers no
    table I/O summary table for them to select from, so there is no counter
    to read on any release and no floor to gate at. The probes answer
    ``False``, the CLI refuses at the capability question, and the roundtrip
    matrix carries the same three classes as a declared gap.

    The refusal is asserted against the real dialect, not only against a
    stub: a probe that answered True here is what would turn a
    definition-time question into a runtime ``1146``.
    """

    @pytest.mark.parametrize("type_, switch", list(NEW_FAMILIES.items()))
    def test_the_dialect_answers_the_six_it_can(self, type_, switch):
        if type_ in UNANSWERED_FAMILIES:
            pytest.skip(f"{type_} is one of the three this engine does not answer")
        dialect = MariaDBDialect(version=MARIA_VERSION)
        assert getattr(dialect, switch)() is True

    @pytest.mark.parametrize("type_", UNANSWERED_FAMILIES)
    def test_the_dialect_refuses_the_three_it_cannot(self, type_):
        dialect = MariaDBDialect(version=MARIA_VERSION)
        switch = NEW_FAMILIES[type_]
        assert getattr(dialect, switch)() is False

    @pytest.mark.parametrize("type_", UNANSWERED_FAMILIES)
    def test_the_refusal_comes_before_the_statement_is_rendered(self, type_, capsys):
        """The introspector is never reached, so no query can fail at execution."""

        class _Backend:
            dialect = MariaDBDialect(version=MARIA_VERSION)

            def __init__(self):
                self.introspector = _RecordingIntrospector()

        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._require_capability(_args(type_), _Backend())

        assert excinfo.value.code == 2
        assert "not supported by this server" in capsys.readouterr().err

    def test_the_refusing_probes_answer_false_before_adaptation_too(self):
        """An unadapted dialect is one whose version nobody has confirmed.

        ``version_at_least`` answers without raising, so a probe guarded on it
        can be called before the handshake -- and an unconfirmed version must
        not read as a capability the server has.
        """
        dialect = MariaDBDialect()
        assert dialect.version_or_none is None
        for type_ in UNANSWERED_FAMILIES:
            assert getattr(dialect, NEW_FAMILIES[type_])() is False
        assert dialect.supports_runtime_stats() is False

    def test_runtime_is_gated_on_the_performance_schema(self):
        """``setup_instruments`` arrived with the performance schema, 10.5."""
        below = MariaDBDialect(version=PRE_PERFORMANCE_SCHEMA)
        at = MariaDBDialect(version=(10, 5, 0))
        assert below.supports_runtime_stats() is False
        assert at.supports_runtime_stats() is True
        assert MariaDBDialect(version=MARIA_VERSION).supports_runtime_stats() is True

    def test_the_two_answered_branches_are_not_gated_on_a_floor(self):
        """Dependencies and DDL are answered on every release in the matrix.

        ``REFERENTIAL_CONSTRAINTS`` and ``SHOW CREATE TABLE`` predate the
        oldest server this repo tests against, so a version gate would be a
        second place to keep a boundary in step and would refuse a question
        the engine answers. Asserted on the oldest and the newest release of
        the matrix, which is what "no floor" means here.
        """
        for version in ((10, 2, 44), MARIA_VERSION, (13, 1, 1)):
            dialect = MariaDBDialect(version=version)
            assert dialect.supports_object_dependencies() is True
            assert dialect.supports_ddl_extraction() is True
