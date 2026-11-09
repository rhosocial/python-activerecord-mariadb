# src/rhosocial/activerecord/backend/impl/mariadb/cli/introspect.py
"""introspect subcommand - Database introspection.

There is no namespace flag here, and that is deliberate. MariaDB has
exactly one namespace level and calls it a *database* -- ``CREATE SCHEMA``
is a synonym for ``CREATE DATABASE`` and nothing sits inside a database
under a further name. So ``--database``, which the connection already
takes, is the whole answer: the run connects to a database and asks about
that database. An earlier version accepted ``--schema`` as well, which
named the same thing under a word MariaDB does not use; it is gone rather
than aliased, so a caller cannot quietly end up asking about a different
level than the one it is connected to.

Every family this command can ask about is offered, and each one says
which dialect capability decides whether the connected server can answer
it. Three of them MariaDB does not answer at all -- its performance schema
registers no table I/O summary, so it keeps no per-index or per-table use
counter -- so those probes answer ``False`` and the capability check
refuses them with exit 2 after connecting rather than letting a rendered
statement fail at execution. The runtime family reads
``setup_instruments`` and is gated on 10.5, the performance schema's
release.
"""

import argparse
import asyncio
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.backend.async_backend import AsyncMariaDBBackend
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError

from .connection import add_connection_args, resolve_connection_config_from_args
from .output import OUTPUT_CHOICES, create_provider

#: Every family the CLI asks about, mapped to the dialect capability that
#: decides whether *this* server can answer it.
#:
#: One table, not a list of names beside a map of gates: a family added to one
#: and not the other would either be offered and answered without a check, or
#: checked while the parser rejects it. `INTROSPECT_TYPES` is derived from this
#: mapping so the two cannot disagree about which families exist.
#:
#: The nine operational and data families are the same set the MySQL and
#: PostgreSQL CLIs ask for, and each one names the probe that answers for it
#: here -- which is not automatically the same answer it gives there. MariaDB
#: answers the dependency graph and the DDL question, aggregates the three
#: data families over its own rows, and answers runtime from the instrument
#: catalogue from 10.5; it keeps no per-index or per-table use counter, so
#: three of the nine are refused by their own probe rather than by an absent
#: CLI branch.
_TYPE_CAPABILITIES = {
    "tables": "supports_table_introspection",
    "views": "supports_view_introspection",
    "columns": "supports_column_introspection",
    "indexes": "supports_index_introspection",
    "foreign-keys": "supports_foreign_key_introspection",
    "triggers": "supports_trigger_introspection",
    "database": "supports_database_info",
    "sequences": "supports_sequence_introspection",  # MariaDB 10.3+
    "table-options": "supports_table_options_introspection",
    "partitions": "supports_partition_info",
    "routines": "supports_routine_introspection",
    "constraints": "supports_constraint_introspection",  # MariaDB 10.2.1+
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

INTROSPECT_TYPES = list(_TYPE_CAPABILITIES)

#: What the optional NAME positional means for each type.
#:
#: ``required`` -- the type asks about one table and cannot be answered without
#: it. ``optional`` -- a catalogue family that can also answer for one member,
#: so a given name narrows it (and a name that matches nothing is an error, not
#: an empty list). ``forbidden`` -- the family has no single-member question
#: here. ``tables`` must stay one: answering for one table would fill in its
#: columns, indexes and foreign keys, which is the aggregate this command
#: deliberately dropped.
_NAME_RULE = {
    "tables": "forbidden",
    "views": "optional",
    "columns": "required",
    "indexes": "required",
    "foreign-keys": "required",
    "triggers": "optional",
    "sequences": "optional",
    "table-options": "optional",
    "partitions": "required",
    "routines": "optional",
    "constraints": "required",
    "unused-indexes": "forbidden",
    "table-stats": "forbidden",
    "runtime": "forbidden",
    "index-stats": "forbidden",
    "dependencies": "optional",
    "ddl": "required",
    "column-profiles": "required",
    "value-samples": "required",
    "join-coverage": "forbidden",
    "database": "forbidden",
}

#: Options whose meaning depends on the type, and whether they must be given.
#:
#: ``--column`` and ``--limit`` belong to ``value-samples``, the four join
#: names to ``join-coverage``, and nothing else has an option beyond NAME. A
#: flag supplied to a type that does not read it is refused rather than
#: ignored, for the same reason a NAME nothing reads is: a silently dropped
#: argument produces a successful run that looks like it answered a narrower
#: question.
_TYPE_OPTIONS = {
    "value-samples": (
        ("column", "--column", True),
        ("limit", "--limit", False),
    ),
    "join-coverage": (
        ("left_table", "--left-table", True),
        ("left_column", "--left-column", True),
        ("right_table", "--right-table", True),
        ("right_column", "--right-column", True),
    ),
}

#: Every option in ``_TYPE_OPTIONS``, by attribute, for the stray-flag check.
_TYPE_OPTION_FLAGS = {
    attribute: flag
    for options in _TYPE_OPTIONS.values()
    for attribute, flag, _required in options
}


def create_parser(subparsers):
    """Create the introspect subcommand parser."""
    parser = subparsers.add_parser(
        'introspect',
        help='Database introspection',
        epilog="""Examples:
  # List all tables in database
  %(prog)s tables --database mydb

  # List all views, or describe one of them
  %(prog)s views --database mydb
  %(prog)s views users_v --database mydb

  # Get column details for a table
  %(prog)s columns users --database mydb

  # List sequences, and one sequence's own limits
  %(prog)s sequences --database mydb
  %(prog)s sequences my_seq --database mydb

  # Show storage options for every table, or for one
  %(prog)s table-options --database mydb
  %(prog)s table-options users --database mydb

  # Partitions of one table (empty when the table is not partitioned)
  %(prog)s partitions orders --database mydb

  # Stored procedures and functions, or one of them by name
  %(prog)s routines --database mydb
  %(prog)s routines app_monthly_cleanup --database mydb

  # CHECK constraints of one table
  %(prog)s constraints orders --database mydb

  # The foreign-key dependency graph, or one table's edges
  %(prog)s dependencies --database mydb
  %(prog)s dependencies orders --database mydb

  # The engine's own DDL for one table
  %(prog)s ddl orders --database mydb

  # Data profiles: exact counts, paid for with a full scan per column
  %(prog)s column-profiles orders --database mydb
  %(prog)s value-samples orders --column status --limit 20 --database mydb

  # How much two columns' value domains overlap
  %(prog)s join-coverage --left-table orders --left-column customer_id \\
      --right-table customers --right-column id --database mydb

  # The families MariaDB does not answer are refused by capability, not
  # hidden: unused-indexes, table-stats and index-stats exit 2 with "not
  # supported by this server". Runtime is answered from the performance
  # schema from 10.5 on, and refused below it.
  %(prog)s unused-indexes --database mydb

  # Output as JSON
  %(prog)s tables --database mydb -o json

  # NAME is a table for columns/indexes/foreign-keys/partitions/constraints/
  # ddl/column-profiles/value-samples, the object itself for views/triggers/
  # routines/table-options/dependencies, and is refused for the families that
  # answer for the whole database (tables, database, unused-indexes,
  # table-stats, runtime, index-stats, join-coverage).

  # Using environment variables for connection
  export MARIADB_HOST=localhost MARIADB_DATABASE=mydb MARIADB_USER=root MARIADB_PASSWORD=secret
  %(prog)s tables
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Output format
    parser.add_argument(
        '-o', '--output',
        choices=OUTPUT_CHOICES,
        default='table',
        help='Output format (default: table)',
    )

    # Connection arguments
    add_connection_args(parser)

    # Rich display options
    parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.',
    )

    # introspect-specific arguments
    # `INTROSPECT_TYPES` is the whole candidate list: it says what MariaDB can
    # be asked about, which is a fact about the engine and not about the server
    # this run will reach. The parser is built before the run connects, so it
    # has no version to consult; a family the connected server cannot answer is
    # refused by `_require_capability` instead of being hidden here, because
    # hiding it would also hide it from a server that has it.
    parser.add_argument(
        "type",
        choices=INTROSPECT_TYPES,
        help="Introspection type: " + ", ".join(INTROSPECT_TYPES),
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Table, view, sequence or routine name (required for some types)",
    )
    parser.add_argument(
        "--column",
        default=None,
        help="Column name for the value-samples type.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum values to list for value-samples "
            "(default: the introspector's own limit)."
        ),
    )
    parser.add_argument(
        "--left-table",
        dest="left_table",
        default=None,
        help="Left table for the join-coverage type.",
    )
    parser.add_argument(
        "--left-column",
        dest="left_column",
        default=None,
        help="Left column for the join-coverage type.",
    )
    parser.add_argument(
        "--right-table",
        dest="right_table",
        default=None,
        help="Right table for the join-coverage type.",
    )
    parser.add_argument(
        "--right-column",
        dest="right_column",
        default=None,
        help="Right column for the join-coverage type.",
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="Include system tables in output",
    )

    return parser


def handle(args):
    """Handle the introspect subcommand."""
    # `tables` and `database` answer for the whole database. A name after them
    # cannot narrow that answer without turning the command into the aggregate
    # of several families that `table` used to be, so it is refused -- exit 2,
    # "this request cannot be served here" -- rather than silently ignored,
    # because a caller who wrote a name believes it selected something.
    _validate_name(args)
    _validate_options(args)

    provider = create_provider(args.output, ascii_borders=args.rich_ascii)

    named_conn = getattr(args, "named_connection", None)
    if not named_conn and not args.database:
        print(
            "Error: --database is required for introspection",
            file=sys.stderr
        )
        sys.exit(1)

    config = resolve_connection_config_from_args(args)

    if args.is_async:
        backend = AsyncMariaDBBackend(connection_config=config)
        asyncio.run(
            _handle_introspect_async(args, backend, provider)
        )
    else:
        backend = MariaDBBackend(connection_config=config)
        _handle_introspect_sync(args, backend, provider)


def _require_capability(args, backend) -> None:
    """Refuse a family this server cannot answer.

    Runs once the dialect is adapted, so the switch answers for the server in
    front of us rather than for the newest release this backend knows. The
    parser offers every family MariaDB has a question for, because whether the
    *engine* can answer is a fact about the engine; which of them this server
    can answer is a fact about its version and its privileges, and only known
    after ``connect()``. So the second reading happens here, and it asks the
    dialect rather than comparing version numbers itself: the dialect is where
    the boundary for a family is recorded, and a copy of it in the CLI is a
    second place to keep in step.

    The table is read, not a list of gated families: every declared type is
    checked. On this engine four of the nine new families answer ``False`` on
    every release, which is why the check exists at all -- MariaDB keeps no
    per-index or per-table use counter to read.

    The refusal exits **2**, not 1. Exit 1 means the run failed -- a connection
    that did not open, a query that errored, an exception nobody expected. Here
    the run succeeded and the answer is that this server cannot be asked; that
    is the same kind of answer as argparse's "invalid choice", which also exits
    2, and it reads that way: the family is valid on this engine, the server is
    what lacks it.
    """
    if not getattr(backend.dialect, _TYPE_CAPABILITIES[args.type])():
        print(
            f"Error: {args.type} introspection is not supported by this server",
            file=sys.stderr,
        )
        sys.exit(2)


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------

def _serialize_for_output(obj: Any) -> Any:
    """Serialize object for JSON output, handling non-serializable types."""
    if obj is None:
        return None
    if hasattr(obj, 'model_dump'):
        try:
            result = obj.model_dump(mode='json')
            return _serialize_for_output(result)
        except TypeError:
            result = obj.model_dump()
            return _serialize_for_output(result)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize_for_output(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize_for_output(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_output(item) for item in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def _validate_name(args) -> None:
    """Refuse a NAME the type cannot use, before anything connects.

    A silently ignored argument is the worst of the three outcomes: the run
    succeeds, prints a full listing, and reads as though it had been narrowed.
    So the rule table above is applied here, once, instead of being left to
    each branch to remember.
    """
    rule = _NAME_RULE.get(args.type)
    if rule is None:
        return
    if rule == "required" and not args.name:
        # An incomplete invocation, not a request this backend refuses: 2 is
        # reserved for the two things the CLI newly declines to do -- answer
        # for a family the server cannot, and accept a NAME the type has no
        # use for.
        print(
            f"Error: Table name is required for '{args.type}' introspection",
            file=sys.stderr,
        )
        sys.exit(1)
    if rule == "forbidden" and args.name:
        print(
            f"Error: '{args.type}' introspection answers for the whole "
            f"database and takes no name",
            file=sys.stderr,
        )
        sys.exit(2)


def _validate_options(args) -> None:
    """Refuse a flag the type does not read, or a missing one it needs.

    A missing required option is an incomplete invocation (exit 1); an option
    the type has no use for is a request this command declines (exit 2), like
    a NAME it cannot use.
    """
    options = _TYPE_OPTIONS.get(args.type, ())
    accepted = {attribute for attribute, _flag, _required in options}

    missing = [
        flag
        for attribute, flag, required in options
        if required and not getattr(args, attribute, None)
    ]
    if missing:
        print(
            f"Error: {', '.join(missing)} is required for "
            f"'{args.type}' introspection",
            file=sys.stderr,
        )
        sys.exit(1)

    for attribute, flag in _TYPE_OPTION_FLAGS.items():
        if attribute in accepted:
            continue
        if getattr(args, attribute, None) not in (None, ""):
            print(
                f"Error: '{args.type}' introspection takes no {flag}",
                file=sys.stderr,
            )
            sys.exit(2)


def _display_ddl(args, provider, statement) -> None:
    """Show one object's DDL as the engine handed it back.

    A DDL text is a block, not a field of a row: a bordered cell wraps every
    one of its lines and reads worse than the text itself. So the terminal
    format prints the engine's own text, and the formats a caller parses keep
    the record -- schema, object type, object name, ``native`` and the text --
    which is what ``native`` is for: it says the engine retrieved this rather
    than the library assembling it.
    """
    record = _serialize_for_output(statement)
    if args.output != "table":
        provider.display_results([record], title=f"DDL of {args.name}")
        return
    print(f"-- {record.get('object_type') or 'OBJECT'} {record.get('object_name') or args.name}")
    print(record["ddl"])


def _value_sample_arguments(args) -> Dict[str, int]:
    """The optional arguments ``value-samples`` sends, given the parsed argument.

    ``limit`` is forwarded only when the caller supplied ``--limit``. When the
    flag is absent the introspector's signature answers with its own default,
    so a forwarder that filled in ``100`` would be a second place writing a
    number the signature already owns -- and a place no test could keep in
    step with it.
    """
    limit = getattr(args, "limit", None)
    return {} if limit is None else {"limit": limit}


def _handle_introspect_sync(args, backend: MariaDBBackend, provider):
    """Handle introspect subcommand synchronously."""
    try:
        backend.connect()
        # Connect alone leaves the dialect unadapted, and a capability probe
        # reads the version the handshake supplies: without this step every
        # version-gated family would answer for a server nobody has asked.
        # Adapted here, at the entrance, so one step answers for both halves
        # of the dispatch rather than being repeated branch by branch.
        backend.introspect_and_adapt()
        _require_capability(args, backend)

        introspector = backend.introspector

        if args.type == "tables":
            tables = introspector.list_tables(
                schema=None,
                include_system=args.include_system
            )
            data = _serialize_for_output(tables)
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            if args.name:
                info = introspector.get_view_info(args.name, schema=None)
                if info is None:
                    print(
                        f"Error: View '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"View {args.name}"
                )
            else:
                views = introspector.list_views(schema=None)
                data = _serialize_for_output(views)
                provider.display_results(data, title="Views")

        elif args.type == "columns":
            columns = introspector.list_columns(
                args.name, schema=None
            )
            data = _serialize_for_output(columns)
            provider.display_results(
                data, title=f"Columns of {args.name}"
            )

        elif args.type == "indexes":
            indexes = introspector.list_indexes(
                args.name, schema=None
            )
            data = _serialize_for_output(indexes)
            provider.display_results(
                data, title=f"Indexes of {args.name}"
            )

        elif args.type == "foreign-keys":
            fks = introspector.list_foreign_keys(
                args.name, schema=None
            )
            data = _serialize_for_output(fks)
            provider.display_results(
                data, title=f"Foreign Keys of {args.name}"
            )

        elif args.type == "triggers":
            triggers = introspector.list_triggers(
                table_name=args.name,
                schema=None
            )
            data = _serialize_for_output(triggers)
            provider.display_results(data, title="Triggers")

        elif args.type == "sequences":
            if args.name:
                info = introspector.get_sequence_info(
                    args.name, schema=None
                )
                if info is None:
                    print(
                        f"Error: Sequence '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"Sequence {args.name}"
                )
            else:
                data = _serialize_for_output(
                    introspector.list_sequences(schema=None)
                )
                provider.display_results(data, title="Sequences")

        elif args.type == "table-options":
            if args.name:
                options = introspector.get_table_options(
                    args.name, schema=None
                )
                if options is None:
                    print(
                        f"Error: Table '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(options)]
                provider.display_results(
                    data, title=f"Table Options of {args.name}"
                )
            else:
                data = _serialize_for_output(
                    introspector.list_table_options(schema=None)
                )
                provider.display_results(data, title="Table Options")

        elif args.type == "partitions":
            partitions = introspector.list_partitions(
                args.name, schema=None
            )
            provider.display_results(
                _serialize_for_output(partitions),
                title=f"Partitions of {args.name}",
            )

        elif args.type == "routines":
            if args.name:
                info = introspector.get_routine_info(args.name, schema=None)
                if info is None:
                    print(
                        f"Error: Routine '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"Routine {args.name}"
                )
            else:
                data = _serialize_for_output(
                    introspector.list_routines(schema=None)
                )
                provider.display_results(data, title="Routines")

        elif args.type == "constraints":
            constraints = introspector.list_constraints(
                args.name, schema=None
            )
            provider.display_results(
                _serialize_for_output(constraints),
                title=f"Constraints of {args.name}",
            )

        elif args.type == "database":
            info = introspector.get_database_info()
            data = _serialize_for_output(info)
            provider.display_results([data], title="Database Info")

        # ---- the families the dialect may or may not answer --------------
        # The four probe-gated ones the engine does not answer are listed
        # anyway: their branches exist so the capability check is the only
        # thing standing between a caller and a statement naming an object
        # MariaDB has never shipped. On an engine that answers them, the
        # branch is one method away.

        elif args.type == "unused-indexes":
            indexes = introspector.list_unused_indexes(schema=None)
            provider.display_results(
                _serialize_for_output(indexes),
                title="Indexes with no recorded use",
            )

        elif args.type == "table-stats":
            stats = introspector.list_table_usage_stats(schema=None)
            provider.display_results(
                _serialize_for_output(stats),
                title="Table usage counters",
            )

        elif args.type == "runtime":
            metrics = introspector.list_runtime_metrics(schema=None)
            provider.display_results(
                _serialize_for_output(metrics),
                title="Runtime metrics",
            )

        elif args.type == "index-stats":
            stats = introspector.list_index_usage_stats(schema=None)
            provider.display_results(
                _serialize_for_output(stats),
                title="Index usage counters",
            )

        elif args.type == "dependencies":
            dependencies = introspector.list_object_dependencies(
                object_name=args.name, schema=None
            )
            provider.display_results(
                _serialize_for_output(dependencies),
                title=(
                    f"Dependencies of {args.name}" if args.name
                    else "Object dependencies"
                ),
            )

        elif args.type == "ddl":
            statement = introspector.get_ddl_statement(args.name, schema=None)
            if statement is None:
                print(
                    f"Error: DDL for '{args.name}' is not available from this server",
                    file=sys.stderr,
                )
                sys.exit(1)
            _display_ddl(args, provider, statement)

        elif args.type == "column-profiles":
            print(
                "Note: column profiles are aggregated from the rows themselves "
                "(source='aggregate') -- exact, and paid for with a full scan per column.",
                file=sys.stderr,
            )
            profiles = introspector.list_column_data_profiles(args.name, schema=None)
            provider.display_results(
                _serialize_for_output(profiles),
                title=f"Column profiles of {args.name}",
            )

        elif args.type == "value-samples":
            samples = introspector.sample_column_values(
                args.name,
                args.column,
                schema=None,
                **_value_sample_arguments(args),
            )
            provider.display_results(
                _serialize_for_output(samples),
                title=f"Most frequent values of {args.name}.{args.column}",
            )

        elif args.type == "join-coverage":
            coverage = introspector.estimate_join_coverage(
                args.left_table,
                args.left_column,
                args.right_table,
                args.right_column,
                schema=None,
            )
            if coverage is None:
                print(
                    "Error: this server could not measure the overlap of "
                    f"{args.left_table}.{args.left_column} and "
                    f"{args.right_table}.{args.right_column}",
                    file=sys.stderr,
                )
                sys.exit(1)
            provider.display_results(
                _serialize_for_output([coverage]), title="Join coverage"
            )

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error during introspection: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            backend.disconnect()


async def _handle_introspect_async(args, backend: AsyncMariaDBBackend, provider):
    """Handle introspect subcommand asynchronously."""
    try:
        await backend.connect()
        # Same reason as the sync half: the dialect must know the server
        # before a capability switch -- or a formatter -- can answer.
        await backend.introspect_and_adapt()
        _require_capability(args, backend)

        introspector = backend.introspector

        if args.type == "tables":
            tables = await introspector.list_tables(
                schema=None,
                include_system=args.include_system
            )
            data = _serialize_for_output(tables)
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            if args.name:
                info = await introspector.get_view_info(args.name, schema=None)
                if info is None:
                    print(
                        f"Error: View '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"View {args.name}"
                )
            else:
                views = await introspector.list_views(
                    schema=None
                )
                data = _serialize_for_output(views)
                provider.display_results(data, title="Views")

        elif args.type == "columns":
            columns = await introspector.list_columns(
                args.name, schema=None
            )
            data = _serialize_for_output(columns)
            provider.display_results(
                data, title=f"Columns of {args.name}"
            )

        elif args.type == "indexes":
            indexes = await introspector.list_indexes(
                args.name, schema=None
            )
            data = _serialize_for_output(indexes)
            provider.display_results(
                data, title=f"Indexes of {args.name}"
            )

        elif args.type == "foreign-keys":
            fks = await introspector.list_foreign_keys(
                args.name, schema=None
            )
            data = _serialize_for_output(fks)
            provider.display_results(
                data, title=f"Foreign Keys of {args.name}"
            )

        elif args.type == "triggers":
            triggers = await introspector.list_triggers(
                table_name=args.name,
                schema=None
            )
            data = _serialize_for_output(triggers)
            provider.display_results(data, title="Triggers")

        elif args.type == "sequences":
            if args.name:
                info = await introspector.get_sequence_info(
                    args.name, schema=None
                )
                if info is None:
                    print(
                        f"Error: Sequence '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"Sequence {args.name}"
                )
            else:
                data = _serialize_for_output(
                    await introspector.list_sequences(schema=None)
                )
                provider.display_results(data, title="Sequences")

        elif args.type == "table-options":
            if args.name:
                options = await introspector.get_table_options(
                    args.name, schema=None
                )
                if options is None:
                    print(
                        f"Error: Table '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(options)]
                provider.display_results(
                    data, title=f"Table Options of {args.name}"
                )
            else:
                data = _serialize_for_output(
                    await introspector.list_table_options(schema=None)
                )
                provider.display_results(data, title="Table Options")

        elif args.type == "partitions":
            partitions = await introspector.list_partitions(
                args.name, schema=None
            )
            provider.display_results(
                _serialize_for_output(partitions),
                title=f"Partitions of {args.name}",
            )

        elif args.type == "routines":
            if args.name:
                info = await introspector.get_routine_info(args.name, schema=None)
                if info is None:
                    print(
                        f"Error: Routine '{args.name}' not found",
                        file=sys.stderr
                    )
                    sys.exit(1)
                data = [_serialize_for_output(info)]
                provider.display_results(
                    data, title=f"Routine {args.name}"
                )
            else:
                data = _serialize_for_output(
                    await introspector.list_routines(schema=None)
                )
                provider.display_results(data, title="Routines")

        elif args.type == "constraints":
            constraints = await introspector.list_constraints(
                args.name, schema=None
            )
            provider.display_results(
                _serialize_for_output(constraints),
                title=f"Constraints of {args.name}",
            )

        elif args.type == "database":
            info = await introspector.get_database_info()
            data = _serialize_for_output(info)
            provider.display_results([data], title="Database Info")

        # ---- the families the dialect may or may not answer --------------
        # The async twins of the branches above: same method, same argument and
        # same title, awaited. They are written out rather than shared with the
        # sync chain because the executor is the only thing that differs, and a
        # shared body would have to carry an ``await`` flag that reads worse
        # than the duplicate.

        elif args.type == "unused-indexes":
            indexes = await introspector.list_unused_indexes(schema=None)
            provider.display_results(
                _serialize_for_output(indexes),
                title="Indexes with no recorded use",
            )

        elif args.type == "table-stats":
            stats = await introspector.list_table_usage_stats(schema=None)
            provider.display_results(
                _serialize_for_output(stats),
                title="Table usage counters",
            )

        elif args.type == "runtime":
            metrics = await introspector.list_runtime_metrics(schema=None)
            provider.display_results(
                _serialize_for_output(metrics),
                title="Runtime metrics",
            )

        elif args.type == "index-stats":
            stats = await introspector.list_index_usage_stats(schema=None)
            provider.display_results(
                _serialize_for_output(stats),
                title="Index usage counters",
            )

        elif args.type == "dependencies":
            dependencies = await introspector.list_object_dependencies(
                object_name=args.name, schema=None
            )
            provider.display_results(
                _serialize_for_output(dependencies),
                title=(
                    f"Dependencies of {args.name}" if args.name
                    else "Object dependencies"
                ),
            )

        elif args.type == "ddl":
            statement = await introspector.get_ddl_statement(args.name, schema=None)
            if statement is None:
                print(
                    f"Error: DDL for '{args.name}' is not available from this server",
                    file=sys.stderr,
                )
                sys.exit(1)
            _display_ddl(args, provider, statement)

        elif args.type == "column-profiles":
            print(
                "Note: column profiles are aggregated from the rows themselves "
                "(source='aggregate') -- exact, and paid for with a full scan per column.",
                file=sys.stderr,
            )
            profiles = await introspector.list_column_data_profiles(
                args.name, schema=None
            )
            provider.display_results(
                _serialize_for_output(profiles),
                title=f"Column profiles of {args.name}",
            )

        elif args.type == "value-samples":
            samples = await introspector.sample_column_values(
                args.name,
                args.column,
                schema=None,
                **_value_sample_arguments(args),
            )
            provider.display_results(
                _serialize_for_output(samples),
                title=f"Most frequent values of {args.name}.{args.column}",
            )

        elif args.type == "join-coverage":
            coverage = await introspector.estimate_join_coverage(
                args.left_table,
                args.left_column,
                args.right_table,
                args.right_column,
                schema=None,
            )
            if coverage is None:
                print(
                    "Error: this server could not measure the overlap of "
                    f"{args.left_table}.{args.left_column} and "
                    f"{args.right_table}.{args.right_column}",
                    file=sys.stderr,
                )
                sys.exit(1)
            provider.display_results(
                _serialize_for_output([coverage]), title="Join coverage"
            )

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error during introspection: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if backend._connection:  # type: ignore
            await backend.disconnect()
