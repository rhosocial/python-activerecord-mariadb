<!-- docs/en_US/installation_and_configuration/charset.md -->
# Character set & collation

## Choosing a character set

Use `utf8mb4` for application data. On MariaDB the name `utf8` is an alias for
`utf8mb3`, which cannot store four-byte characters (emoji and some CJK
extensions); the backend resolves the alias to a fixed meaning before emitting
DDL so one declaration produces one schema across releases.

```python
config = MariaDBConnectionConfig(
    host="localhost",
    database="myapp",
    username="app",
    password="secret",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
)
```

`charset` is emitted as `SET NAMES <charset>` in the connector's `init_command`,
so it governs client↔server text conversion for every statement on the
connection. `collation` travels with table/column options for declarations that
accept it.

## Per-column and per-table options

Column-level `CHARACTER SET` and `COLLATE` attributes are supported by the
dialect (`supports_column_character_set()` / `supports_column_collation()`). At
table level, MariaDB-specific create options carry the engine and charset:

```python
from rhosocial.activerecord.backend.impl.mariadb.expression import MariaDBCreateTableOptions

options = MariaDBCreateTableOptions(dialect, engine="InnoDB", charset="utf8mb4")
```

## Introspection

`information_schema.COLUMNS` reports the effective `CHARACTER_SET_NAME` and
`COLLATION_NAME` for each text column, and `get_database_info()` reports the
database's defaults (`encoding`, `collation`). These are the values the server
actually stored, not the config values you supplied — useful when diagnosing a
mismatch.

## Troubleshooting

If text is mangled, verify all three layers in order: the database default, the
table/column declaration, and the connection's `SET NAMES`. See
[Troubleshooting](../troubleshooting/README.md).
