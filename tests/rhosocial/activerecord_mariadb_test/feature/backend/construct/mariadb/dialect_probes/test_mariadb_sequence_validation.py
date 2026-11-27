# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/mariadb/
# dialect_probes/test_mariadb_sequence_validation.py
"""MariaDB's sequence formatters opt into core's reusable pair validation.

Core's constructors only collect CYCLE/NO CYCLE, CACHE/NO CACHE and
ORDER/NO ORDER. The MariaDB mixin overrides the CREATE/ALTER formatters, so it
must call the expression's public ``validate()`` before spelling the clause:
a malformed node renders as before when valid and refuses at ``to_sql()``.
"""

import pytest

from rhosocial.activerecord.backend.expression.objects import Sequence
from rhosocial.activerecord.backend.expression.statements.ddl_sequence import (
    AlterSequenceStatement,
    CreateSequenceStatement,
)
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect


@pytest.fixture
def dialect():
    return MariaDBDialect((10, 6, 0))


@pytest.mark.parametrize(
    ("statement", "kwargs", "sql"),
    [
        (
            CreateSequenceStatement,
            dict(start=1, no_cycle=True, cache=10),
            "CREATE SEQUENCE `validation_seq` START = 1 CACHE = 10 NOCYCLE",
        ),
        (
            AlterSequenceStatement,
            dict(restart=1, no_cycle=True, cache=10),
            "ALTER SEQUENCE `validation_seq` RESTART WITH 1 CACHE = 10 NOCYCLE",
        ),
    ],
)
def test_valid_statement_renders_unchanged(dialect, statement, kwargs, sql):
    expr = statement(dialect, Sequence(dialect, "validation_seq"), **kwargs)
    assert expr.to_sql() == (sql, ())


@pytest.mark.parametrize("statement", [CreateSequenceStatement, AlterSequenceStatement])
@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (dict(cycle=True, no_cycle=True), "cycle and no_cycle are mutually exclusive options"),
        (dict(cache=5, no_cache=True), "cache and no_cache are mutually exclusive options"),
        (dict(order=True, no_order=True), "order and no_order are mutually exclusive options"),
        (dict(cache=0), "cache must be a positive integer"),
    ],
)
def test_malformed_statement_refuses_at_to_sql(dialect, statement, kwargs, message):
    expr = statement(dialect, Sequence(dialect, "validation_seq"), **kwargs)
    with pytest.raises(ValueError, match=message):
        expr.to_sql()
