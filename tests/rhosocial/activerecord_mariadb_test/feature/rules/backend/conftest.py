# tests/rhosocial/activerecord_mariadb_test/feature/rules/backend/conftest.py
"""Fixtures for MariaDB's own rule suite.

MariaDB owns only its own ``impl/mariadb`` tree. Every path is derived from
the installed packages, never from a hardcoded worktree path, and
``source_roots`` names a single root: ``backend/impl/mariadb``. The shared
rule library supplies the assertions; this conftest selects the subject.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from rhosocial.activerecord.testsuite.feature.rules.backend.conftest import *  # noqa: F401,F403
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    uses_database=False,
    parallel=False,
    purpose="Executable assertions of the MariaDB backend's formal constraints",
    passes_means="MariaDB source obeys the mechanical and structural rule",
    fails_means="MariaDB source introduces a forbidden construct or dependency",
)


def mariadb_expression_package() -> object:
    """The installed MariaDB expression package."""
    return importlib.import_module("rhosocial.activerecord.backend.impl.mariadb.expression")


def mariadb_impl_root() -> Path:
    """The installed ``backend/impl/mariadb`` directory."""
    package = mariadb_expression_package()
    for search_path in vars(package).get("__path__", ()):
        current = Path(search_path).resolve()
        for candidate in [current] + list(current.parents):
            if candidate.name == "impl" and candidate.parent.name == "backend":
                return candidate / current.relative_to(candidate).parts[0]
    pytest.skip("MariaDB impl root is not discoverable from the installed package")


def mariadb_project_root() -> Path:
    """Project root inferred from the installed MariaDB package layout."""
    for candidate in [mariadb_impl_root()] + list(mariadb_impl_root().parents):
        if (candidate / "tests").is_dir() and (candidate / "src").is_dir():
            return candidate
    pytest.skip("MariaDB project root is not discoverable from the installed package")


@pytest.fixture
def backend_expression_package() -> object:
    """MariaDB's expression package."""
    return mariadb_expression_package()


@pytest.fixture
def backend_dialect() -> object:
    """An instantiated MariaDB dialect."""
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

    return MariaDBDialect()


@pytest.fixture
def backend_prefix() -> str:
    """MariaDB's own naming prefix."""
    return "MariaDB"


@pytest.fixture
def backend_impl_root() -> Path:
    """The MariaDB ``impl`` root used by file-driven shared rules."""
    return mariadb_impl_root()


@pytest.fixture
def source_roots() -> List[Tuple[str, Path]]:
    """One root only: the MariaDB backend, never core or another backend."""
    return [("mariadb", mariadb_impl_root())]


@pytest.fixture
def backend_project_root() -> Path:
    """Project root for MariaDB's tests."""
    return mariadb_project_root()


# Measured reflection surface of ``backend/impl/mariadb``. Keys are
# (source label, path relative to that root, enclosing scope, builtin) and map
# to (exact observed count, reason). Every entry records both why the probed
# object is not a SQL expression and why a declared attribute cannot be read:
# the sites are argparse/config records, driver or capability optional
# attributes, introspection/status payloads, plan/step descriptors, and legacy
# optional qualifiers on DDL nodes. No new call site and no count growth can be
# added here without an explicit, reviewed reason.
MARIADB_REFLECTION_ALLOWLIST: Dict[Tuple[str, str, str, str], Tuple[int, str]] = {
    ("mariadb", "backend/async_backend.py", "AsyncMariaDBBackend", "getattr"): (
        2,
        "reads init_command/autocommit from a driver config record, not a SQL expression; "
        "older drivers omit those keys, so a declared attribute read would raise AttributeError",
    ),
    ("mariadb", "backend/async_backend.py", "AsyncMariaDBBackend", "hasattr"): (
        1,
        "probes the mariadb driver module for asyncConnect, not an expression field; the "
        "symbol is optional across driver releases, so no declared attribute exists",
    ),
    ("mariadb", "backend/backend.py", "MariaDBBackend", "getattr"): (
        7,
        "reads host/port/username/password/charset/options from a connection config record, "
        "not an expression; config sources omit keys, so declared access would raise",
    ),
    ("mariadb", "backend/backend.py", "MariaDBBackend", "hasattr"): (
        1,
        "errno is optional on driver exception objects, not on an expression; legacy drivers "
        "omit it, so a declared attribute cannot be used",
    ),
    ("mariadb", "cli/connection.py", "resolve_connection_config_from_args", "getattr"): (
        3,
        "argparse Namespace flags, not expression fields; flags are optional per subcommand, "
        "so declared attribute access would raise AttributeError",
    ),
    ("mariadb", "cli/info.py", "handle", "getattr"): (
        1,
        "argparse named_connection flag, not an expression; absent when the flag is omitted",
    ),
    ("mariadb", "cli/introspect.py", "_require_capability", "getattr"): (
        1,
        "dialect capability named by a CLI option, not an expression field; the method exists "
        "only on backends that advertise it, so no declared attribute is available",
    ),
    ("mariadb", "cli/introspect.py", "_serialize_for_output", "hasattr"): (
        1,
        "caller-supplied serialization object, not an expression; model_dump exists only on "
        "pydantic-style results, so declared access would raise",
    ),
    ("mariadb", "cli/introspect.py", "_validate_options", "getattr"): (
        2,
        "argparse option attributes, not expressions; options are optional per invocation, so "
        "declared access would raise AttributeError",
    ),
    ("mariadb", "cli/introspect.py", "_value_sample_arguments", "getattr"): (
        1,
        "argparse value-sample attributes, not expressions; absent unless the option is used",
    ),
    ("mariadb", "cli/introspect.py", "handle", "getattr"): (
        1,
        "argparse named_connection flag, not an expression; absent unless the flag is supplied",
    ),
    ("mariadb", "cli/named_connection.py", "handle", "getattr"): (
        2,
        "argparse output / rich_ascii flags, not expressions; optional per invocation, so "
        "declared attribute access would raise",
    ),
    ("mariadb", "cli/named_expression.py", "_get_requested_version", "getattr"): (
        1,
        "argparse dialect_version flag, not an expression; absent when the option is omitted",
    ),
    ("mariadb", "cli/named_expression.py", "handle", "getattr"): (
        1,
        "argparse is_async flag, not an expression; absent when the option is omitted",
    ),
    ("mariadb", "cli/named_migration.py", "disconnect", "getattr"): (
        1,
        "private _connection on a backend object, not an expression; absent after disconnect, "
        "so a declared attribute read would raise",
    ),
    ("mariadb", "cli/named_migration.py", "disconnect_async", "getattr"): (
        1,
        "private _connection on an async backend object, not an expression; absent after "
        "disconnect, so declared access would raise",
    ),
    ("mariadb", "cli/named_migration.py", "handle", "getattr"): (
        1,
        "argparse is_async flag, not an expression; absent when the option is omitted",
    ),
    ("mariadb", "cli/named_procedure.py", "handle", "getattr"): (
        1,
        "argparse is_async flag, not an expression; absent when the option is omitted",
    ),
    ("mariadb", "cli/named_procedure_graph.py", "handle", "getattr"): (
        1,
        "argparse is_async flag, not an expression; absent when the option is omitted",
    ),
    ("mariadb", "cli/query.py", "handle", "getattr"): (
        1,
        "logging module attribute selected by a CLI log-level string, not an expression; "
        "arbitrary level names are absent from logging, so declared access would raise",
    ),
    ("mariadb", "cli/status.py", "_display_status_rich", "getattr"): (
        2,
        "binary_log/replication fields on a status record, not an expression; some server "
        "versions omit them, so declared access would raise",
    ),
    ("mariadb", "cli/status.py", "_display_status_rich", "hasattr"): (
        3,
        "session/connections/storage sections on a status record, not an expression; some "
        "server versions omit them, so declared access would raise",
    ),
    ("mariadb", "cli/status.py", "_serialize_for_output", "hasattr"): (
        1,
        "caller-supplied serialization object, not an expression; model_dump exists only on "
        "pydantic-style results, so declared access would raise",
    ),
    ("mariadb", "cli/status.py", "handle", "getattr"): (
        1,
        "argparse named_connection flag, not an expression; absent when the flag is omitted",
    ),
    ("mariadb", "config.py", "MariaDBConnectionConfig", "getattr"): (
        3,
        "optional charset / SSL fields on a config object, not an expression; earlier config "
        "sources omit them, so declared attribute access would raise",
    ),
    ("mariadb", "dialect.py", "MariaDBDialect", "getattr"): (
        2,
        "capability method names from a probe table, not expression fields; methods exist only "
        "on backends advertising them, so no declared attribute is available",
    ),
    ("mariadb", "dialect.py", "MariaDBDialect", "hasattr"): (
        1,
        "caller-supplied explain options object, not an expression; .type is absent on plain "
        "boolean options, so a declared attribute read would raise",
    ),
    ("mariadb", "examples/named_migrations/run_basic_async.py", "_table_exists", "getattr"): (
        1,
        "driver introspection row, not an expression; .name is absent on some row shapes, so "
        "declared attribute access would raise",
    ),
    ("mariadb", "expression/partition.py", "MariaDBPartitionClause", "getattr"): (
        4,
        "constructor normalises an external strategy descriptor (word/method/value), not a SQL "
        "expression; legacy callers use three spellings, so no single declared attribute exists",
    ),
    ("mariadb", "expression/partition.py", "_subpartition_strategy_word", "getattr"): (
        1,
        "strategy is a caller-supplied enum or word token, not an expression; legacy callers "
        "carry the word in .value or directly, so no declared attribute is available",
    ),
    ("mariadb", "introspection/introspector.py", "MariaDBIntrospectorMixin", "hasattr"): (
        2,
        "backend.config/database on an introspection client, not expressions; driver "
        "connections may omit them, so declared attribute access would raise",
    ),
    ("mariadb", "mixins/backend.py", "MariaDBBackendMixin", "getattr"): (
        3,
        "autocommit / _liveness_probe_sql / errno on config, backend and error objects, not "
        "expressions; each is optional on some connections or errors",
    ),
    ("mariadb", "mixins/backend.py", "MariaDBBackendMixin", "hasattr"): (
        1,
        "_version on the backend object, not an expression; it is set only after version "
        "discovery, so a declared attribute read would raise",
    ),
    ("mariadb", "mixins/charset_collation.py", "MariaDBCharsetCollationMixin", "getattr"): (
        1,
        "_version on the backend object, not an expression; unset before version discovery, so "
        "declared access would raise AttributeError",
    ),
    ("mariadb", "mixins/concurrency.py", "AsyncMariaDBConcurrencyMixin", "getattr"): (
        1,
        "config.pool_size is a driver setting, not an expression; absent when pooling is not "
        "configured, so a declared attribute read would raise",
    ),
    ("mariadb", "mixins/concurrency.py", "MariaDBConcurrencyMixin", "getattr"): (
        1,
        "config.pool_size is a driver setting, not an expression; absent when pooling is not "
        "configured, so a declared attribute read would raise",
    ),
    ("mariadb", "mixins/ddl/column.py", "MariaDBAlterColumnModifierMixin", "getattr"): (
        2,
        "IF [NOT] EXISTS qualifiers on a DDL action node, not a value expression; declared "
        "only on the actions that carry them, so base-class declared access would raise on "
        "sibling actions",
    ),
    ("mariadb", "mixins/ddl/constraint.py", "MariaDBAlterConstraintModifierMixin", "getattr"): (
        2,
        "if_exists / cascade qualifiers on a DDL action node, not a value expression; sibling "
        "actions omit them, so no declared attribute is available",
    ),
    ("mariadb", "mixins/function.py", "MariaDBFunctionMixin", "getattr"): (
        1,
        "__all__ on a function registry module, not an expression; the attribute is optional on "
        "function modules, so declared access would raise",
    ),
    ("mariadb", "mixins/partition.py", "MariaDBPartitionMixin", "getattr"): (
        4,
        "options / subpartitions / strategy.value on partition DDL nodes, not value "
        "expressions; legacy nodes declare them inconsistently, so direct attribute access "
        "would raise",
    ),
    ("mariadb", "mixins/system_versioning.py", "MariaDBSystemVersioningMixin", "hasattr"): (
        6,
        "caller-supplied timestamp values (datetime, str or expression), not the expression "
        "being formatted; to_sql/isoformat are optional across those value shapes",
    ),
    ("mariadb", "mixins/trigger.py", "MariaDBTriggerMixin", "getattr"): (
        2,
        "or_replace / ordering qualifiers on DDL trigger nodes, not value expressions; "
        "declared only by the variants that carry them, so declared access would raise",
    ),
    ("mariadb", "mixins/types.py", "MariaDBTypeSupportMixin", "getattr"): (
        1,
        "zerofill is a flag on a data-type descriptor, not an expression; absent on other types "
        "so a declared attribute read would raise",
    ),
    ("mariadb", "show/backend_mixin.py", "AsyncMariaDBShowMixin", "getattr"): (
        1,
        "_version on a backend object, not an expression; unset until version discovery, so "
        "declared access would raise",
    ),
    ("mariadb", "show/backend_mixin.py", "AsyncMariaDBShowMixin", "hasattr"): (
        1,
        "get_server_version capability on a backend object, not an expression; optional across "
        "backend classes, so no declared attribute exists",
    ),
    ("mariadb", "show/backend_mixin.py", "MariaDBShowMixin", "getattr"): (
        1,
        "_version on a backend object, not an expression; unset until version discovery, so "
        "declared access would raise",
    ),
    ("mariadb", "show/backend_mixin.py", "MariaDBShowMixin", "hasattr"): (
        1,
        "_version optional attribute on a backend object, not an expression; absent before "
        "version discovery, so declared access would raise",
    ),
    ("mariadb", "suggestion/_change_plan_common.py", "name_of", "getattr"): (
        1,
        "plan step object, not an expression; .name is optional across step variants, so a "
        "declared attribute read would raise",
    ),
    ("mariadb", "suggestion/_change_plan_common.py", "params_of", "getattr"): (
        1,
        "get_params is an optional protocol method on a plan value, not an expression; plain "
        "values lack it, so declared access would raise",
    ),
    ("mariadb", "suggestion/_common.py", "_field", "getattr"): (
        1,
        "word/method/value spelling on a strategy token, not an expression; legacy callers "
        "vary, so no single declared attribute exists",
    ),
    ("mariadb", "suggestion/_common.py", "_keys", "hasattr"): (
        2,
        "caller-supplied key collection, not an expression; to_sql exists only on identifier "
        "objects, so declared access would raise",
    ),
    ("mariadb", "suggestion/_common.py", "_names", "getattr"): (
        2,
        "definition/name descriptor on a plan, not an expression; legacy definitions omit "
        ".name, so a declared attribute read would raise",
    ),
    ("mariadb", "suggestion/_common.py", "_word", "getattr"): (
        3,
        "word/method/value spellings on a strategy token, not an expression; legacy callers "
        "vary, so no single declared attribute exists",
    ),
    (
        "mariadb",
        "suggestion/column_reorder_suggestion.py",
        "MariaDBColumnReorderSuggestionMixin",
        "getattr",
    ): (
        2,
        "supports_modify_column capability and column.data_type on plan objects, not "
        "expressions; both are optional across dialects and column shapes",
    ),
    (
        "mariadb",
        "suggestion/data_type_suggestions.py",
        "MariaDBDataTypeSuggestionsMixin",
        "getattr",
    ): (
        1,
        "_version on a backend object, not an expression; unset until version discovery, so "
        "declared access would raise",
    ),
    (
        "mariadb",
        "suggestion/partition_add_suggestion.py",
        "MariaDBPartitionAddSuggestionMixin",
        "getattr",
    ): (
        1,
        "supports_add_partition capability on a dialect, not an expression; the method is "
        "absent where the capability is unsupported",
    ),
    (
        "mariadb",
        "suggestion/partition_drop_suggestion.py",
        "MariaDBPartitionDropSuggestionMixin",
        "getattr",
    ): (
        1,
        "supports_drop_partition capability on a dialect, not an expression; the method is "
        "absent where the capability is unsupported",
    ),
    (
        "mariadb",
        "suggestion/partition_retention_suggestion.py",
        "MariaDBPartitionRetentionSuggestionMixin",
        "getattr",
    ): (
        1,
        "definition.less_than on a partition boundary definition, not an expression; absent "
        "for non-range bounds, so declared access would raise",
    ),
    ("mariadb", "suggestion/partition_retention_suggestion.py", "_upper_bound", "getattr"): (
        2,
        ".value on a legacy boundary token, not an expression; plain values carry the bound "
        "directly, so no declared attribute is available",
    ),
    (
        "mariadb",
        "suggestion/partition_scheme_change_suggestion.py",
        "MariaDBPartitionSchemeChangeSuggestionMixin",
        "getattr",
    ): (
        1,
        "key.name on a partition key descriptor, not an expression; legacy keys omit it, so "
        "declared access would raise",
    ),
    ("mariadb", "suggestion/partition_scheme_change_suggestion.py", "_key_names", "getattr"): (
        1,
        "supports_remove_partitioning capability on a dialect, not an expression; absent where "
        "unsupported, so no declared attribute exists",
    ),
    (
        "mariadb",
        "suggestion/partition_split_suggestion.py",
        "MariaDBPartitionSplitSuggestionMixin",
        "getattr",
    ): (
        1,
        "supports_reorganize_partition capability on a dialect, not an expression; absent "
        "where unsupported, so no declared attribute exists",
    ),
    (
        "mariadb",
        "suggestion/partition_table_alter_suggestion.py",
        "MariaDBPartitionTableAlterSuggestionMixin",
        "getattr",
    ): (
        2,
        "supports_coalesce_partition / supports_remove_partitioning capabilities on a dialect, "
        "not expressions; absent where unsupported",
    ),
    (
        "mariadb",
        "suggestion/partition_table_drop_suggestion.py",
        "MariaDBPartitionTableDropSuggestionMixin",
        "getattr",
    ): (
        1,
        "supports_remove_partitioning capability on a dialect, not an expression; absent where "
        "unsupported, so no declared attribute exists",
    ),
    (
        "mariadb",
        "suggestion/string_concatenation_suggestion.py",
        "MariaDBStringConcatenationSuggestionMixin",
        "getattr",
    ): (
        1,
        "STRING_CONCATENATION constant on a mixin, not an expression; absent on mixins that do "
        "not declare it, so a declared attribute read would raise",
    ),
    (
        "mariadb",
        "suggestion/table_constraint_change_suggestion.py",
        "MariaDBTableConstraintChangeSuggestionMixin",
        "getattr",
    ): (
        1,
        "capability probe named by a string on a dialect, not an expression; probe methods are "
        "absent where unsupported",
    ),
    ("mariadb", "suggestion/table_constraint_change_suggestion.py", "_build_add", "getattr"): (
        2,
        "supports_add_constraint / supports_alter_table_index_actions capabilities on a "
        "dialect, not expressions; absent where unsupported",
    ),
    ("mariadb", "suggestion/table_constraint_change_suggestion.py", "_build_drop", "getattr"): (
        2,
        "supports_drop_constraint / supports_alter_table_index_actions capabilities on a "
        "dialect, not expressions; absent where unsupported",
    ),
    ("mariadb", "suggestion/table_constraint_change_suggestion.py", "_gated", "getattr"): (
        1,
        "supports_drop_constraint capability on a dialect, not an expression; absent where "
        "unsupported, so no declared attribute exists",
    ),
    ("mariadb", "suggestion/table_constraint_change_suggestion.py", "_traits_allowed", "getattr"): (
        2,
        "trait flags on plan values, not an expression; the flags are absent on traits that do "
        "not carry them, so declared access would raise",
    ),
    (
        "mariadb",
        "suggestion/table_index_change_suggestion.py",
        "MariaDBTableIndexChangeSuggestionMixin",
        "getattr",
    ): (
        1,
        "supports_alter_table_index_actions capability on a dialect, not an expression; absent "
        "where unsupported, so no declared attribute exists",
    ),
    ("mariadb", "suggestion/table_index_change_suggestion.py", "_drop_action", "getattr"): (
        1,
        "supports_index_if_exists capability on a dialect, not an expression; absent where "
        "unsupported, so no declared attribute exists",
    ),
    ("mariadb", "transaction.py", "MariaDBTransactionMixin", "hasattr"): (
        2,
        "self.log on a transaction object, not an expression; present only when logging is "
        "enabled, so a declared attribute read would raise",
    ),
}


@pytest.fixture
def reflection_allowlist() -> Dict[Tuple[str, str, str, str], Tuple[int, str]]:
    """MariaDB's own reason-bearing sites; shared core entries stay for probe tests."""
    from rhosocial.activerecord.testsuite.feature.rules.backend.test_no_reflection_in_expression_layer import (
        REFLECTION_ALLOWLIST as SHARED_REFLECTION_ALLOWLIST,
    )

    return {**SHARED_REFLECTION_ALLOWLIST, **MARIADB_REFLECTION_ALLOWLIST}
