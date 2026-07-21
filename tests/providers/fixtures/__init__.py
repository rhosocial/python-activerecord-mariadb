# tests/providers/fixtures/__init__.py
"""MariaDB-specific DDL expression fixtures for the testsuite providers.

Each module in this package exposes a ``TABLE_EXPRESSIONS`` mapping of
table name -> factory callable ``Callable[[DialectLike, str], CreateTableExpression]``.

The factory functions build :class:`CreateTableExpression` instances that emit
MariaDB-compatible DDL (ENGINE / CHARSET / COLLATE / inline indexes / FK with
ON DELETE CASCADE / TINYINT(1) / DATETIME(6) / ENUM / JSON).  The pre-existing
``.sql`` schema files under ``tests/rhosocial/activerecord_mariadb_test/feature/<feature>/schema/``
remain as the authoritative reference for what the expressions here must
produce; they are simply no longer read at runtime by the providers.

Because the MariaDB backend's ``format_storage_options`` emits quoted values
(e.g. ``ENGINE='InnoDB'``) while the reference SQL files use the unquoted
form, each factory routes its expression through :func:`to_mariadb_ddl_sql`
which post-processes the storage option clause to drop the quotes, producing
DDL equivalent to the reference ``.sql`` files.
"""
