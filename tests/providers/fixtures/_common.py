# tests/providers/fixtures/_common.py
"""Shared helpers for the MariaDB DDL expression fixtures.

The MariaDB backend's :meth:`format_storage_options` quotes string option
values (``ENGINE='InnoDB'``).  The authoritative ``.sql`` schema files under
``tests/rhosocial/activerecord_mariadb_test/feature/<feature>/schema/``
use the unquoted storage form.

Rather than modifying the MariaDB backend library source, :func:`to_mariadb_ddl_sql`
post-processes the SQL produced by ``CreateTableExpression.to_sql()`` so that
the generated DDL matches the reference files:

* ``KEY='value'`` storage options become ``KEY=value``.

The MariaDB dialect already emits ``ON DELETE`` / ``ON UPDATE`` referential
actions inline for ``FOREIGN KEY`` constraints, so no FK action re-injection
is needed (unlike the MySQL backend).
"""

from __future__ import annotations

import re
from typing import Tuple

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
)


_STORAGE_OPTION_RE = re.compile(r"([A-Z_ ]+=)'([^']*)'")


def _strip_storage_option_quotes(sql: str) -> str:
    """Drop single quotes around storage option values (``ENGINE='InnoDB'`` -> ``ENGINE=InnoDB``)."""
    return _STORAGE_OPTION_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}", sql)


def to_mariadb_ddl_sql(expr: CreateTableExpression) -> Tuple[str, tuple]:
    """Generate canonical MariaDB DDL for a :class:`CreateTableExpression`.

    Post-processes the dialect output to drop quotes around storage option
    values.  The MariaDB dialect already emits ``ON DELETE`` / ``ON UPDATE``
    referential actions inline for ``FOREIGN KEY`` constraints.

    Returns the ``(sql, params)`` tuple suitable for ``backend.execute``.
    """
    sql, params = expr.to_sql()
    sql = _strip_storage_option_quotes(sql)
    return sql, params


def to_mysql_ddl_sql(expr: CreateTableExpression) -> Tuple[str, tuple]:
    """Backward-compatible alias for :func:`to_mariadb_ddl_sql`."""
    return to_mariadb_ddl_sql(expr)


def create_table_sql(expr: CreateTableExpression) -> Tuple[str, tuple]:
    """Public alias for :func:`to_mariadb_ddl_sql`."""
    return to_mariadb_ddl_sql(expr)


def drop_table(dialect, table_name: str) -> DropTableExpression:
    """Build a canonical ``DROP TABLE IF EXISTS`` expression."""
    return DropTableExpression(
        dialect=dialect,
        table=TableExpression(dialect, table_name),
        if_exists=True,
    )
