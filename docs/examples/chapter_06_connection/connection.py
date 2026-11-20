# docs/examples/chapter_06_connection/connection.py
"""Connect to MariaDB with a declarative model and run a small CRUD example.

Requires a live MariaDB server and an existing database; see README.md.
"""

import os
from typing import Annotated, ClassVar

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.field import DefaultTimestampMixin, IntegerPKMixin
from rhosocial.activerecord.model import ActiveRecord


class User(IntegerPKMixin, DefaultTimestampMixin, ActiveRecord):
    """A model whose DDL is rendered by the MariaDB dialect."""

    name: Annotated[str, UseSqlType(VarCharType(length=100))]
    email: Annotated[str, UseSqlType(VarCharType(length=255))]
    age: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "docs_example_users"


def make_config() -> MariaDBConnectionConfig:
    return MariaDBConnectionConfig(
        host=os.getenv("MARIADB_HOST", "localhost"),
        port=int(os.getenv("MARIADB_PORT", "3306")),
        database=os.getenv("MARIADB_DATABASE", "test_db"),
        username=os.getenv("MARIADB_USERNAME", "app"),
        password=os.getenv("MARIADB_PASSWORD", ""),
        charset="utf8mb4",
    )


def main() -> None:
    config = make_config()
    User.configure(config, MariaDBBackend)

    backend = User.__backend__
    backend.connect()
    backend.introspect_and_adapt()
    print("Server:", backend.dialect.get_server_version())

    # Preview the query before executing it.
    sql, params = User.query().where(User.c.age >= 18).to_sql()
    print("SQL:", sql)
    print("Params:", params)

    User.create_table()
    try:
        # Writes run in a transaction; an exception would roll them back.
        with backend.transaction():
            alice = User(name="Alice", email="alice@example.com", age=30)
            alice.save()
            User(name="Bob", email="bob@example.com", age=17).save()

        print("Inserted id:", alice.id)
        adults = User.query().where(User.c.age >= 18).all()
        print("Adults:", [user.name for user in adults])
    finally:
        backend.execute("DROP TABLE IF EXISTS `docs_example_users`", ())
        backend.disconnect()


if __name__ == "__main__":
    main()
