# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/helpers.py
"""Small native-SQL helpers shared by the native-type tests.

Identifiers are rendered by the dialect (``Column``/``Table``) instead of being
written bare, so a column whose name is reserved on the server is still quoted
by that server's own rules (the same rule the shared contract follows).
"""

from typing import Dict

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

DML = ExecutionOptions(stmt_type=StatementType.DML)


def table_sql(model) -> str:
    """Return the model's table name rendered for this server."""
    return Table(model.backend().dialect, model.table_name()).to_sql()[0]


def column_sql(model, name: str) -> str:
    """Return one column name rendered for this server."""
    return Column(model.backend().dialect, name).to_sql()[0]


def read_raw(model, expression: str, pk: int):
    """Evaluate *expression* against the row with primary key *pk*.

    No adapter is involved: this is the original column value (or a server-side
    rendering of it such as ``HEX(...)``).
    """
    row = model.backend().fetch_one(
        f"SELECT {expression} AS v FROM {table_sql(model)} WHERE id = {int(pk)}", ()
    )
    return row["v"]


def insert_native(model, values: Dict[str, str]) -> None:
    """Insert one row through native SQL.

    Each value is a ready SQL fragment (``b'10101'``, ``ST_GeomFromText(...)``,
    ``'a,c'``), so the statement exercises the server's own literal parsing and
    never passes through a type adapter.
    """
    columns = ", ".join(column_sql(model, name) for name in values)
    literals = ", ".join(values.values())
    model.backend().execute(
        f"INSERT INTO {table_sql(model)} ({columns}) VALUES ({literals})", (), options=DML
    )
