# `introspect` — MariaDB metadata, from the command line

The `introspect` subcommand asks a live MariaDB server what it holds, and
prints the answer. Every question runs through the backend's introspector, so
what the CLI reports is what the library sees — the same objects, the same
types, the same parsing — rather than a second implementation that can drift
from it.

```bash
python -m rhosocial.activerecord.backend.impl.mariadb introspect <TYPE> [NAME] [OPTIONS]
```

## What it can ask about

| Type | Reads | Notes |
| :--- | :--- | :--- |
| `tables` | `information_schema.tables` | Base tables. `--include-system` adds MariaDB's own metadata databases. |
| `views` | `information_schema.views` | Views, with their definitions. |
| `table` | several | One table by name, with its columns, indexes and foreign keys filled in. |
| `columns` | `information_schema.columns` | One table's columns: name, type, nullability, default. |
| `indexes` | `information_schema.statistics` | One table's indexes, including the primary key. |
| `foreign-keys` | `information_schema.key_column_usage` | One table's constraints and the columns each side names. |
| `triggers` | `information_schema.triggers` | Triggers, optionally narrowed to one table. |
| `sequences` | `information_schema.sequences` | MariaDB's own sequences. **10.3 and later** — on an older server `sequences` is refused as an unsupported capability, not answered empty. |
| `table-options` | `information_schema.tables` | The storage facts about a table: engine, row format, collation, auto-increment, comment, and the byte sizes `information_schema` reports. |
| `database` | `information_schema.schemata`, `variables` | Server version, charset, and the databases visible to this role. |

`NAME` is required for `table`, `columns`, `indexes`, `foreign-keys` and, for
one sequence, `sequences`. The list types take no name.

## Options

| Option | Default | Description |
| :--- | :--- | :--- |
| `-o, --output` | `table` | `table` (rich), `json`, `csv`, `tsv`. |
| `--database` | required (env: `MARIADB_DATABASE`) | The database to connect to **and** the database to read. MariaDB has one namespace level and calls it a database, so there is no second flag. |
| `--include-system` | off | Include system tables. |
| `--host`, `--port`, `--database`, `--user`, `--password` | env or defaults | Connection. `MARIADB_*` env vars are honoured, and arguments override them. |
| `--charset` | _None_ | Connection charset. |
| `--ssl` | off | Use SSL for the connection. |
| `--async` | off | Drive the asynchronous backend. |
| `--named-connection` | _None_ | A connection saved by the `named-connection` subcommand. |
| `--conn-param` | _None_ | Extra `key=value` connection parameters; repeatable. |
| `--rich-ascii` | off | ASCII characters for table borders. |

## Notes

*   **Read-only.** `introspect` never writes. It does not create, drop, or
    alter anything, so it is safe to run against a database whose schema
    matters.
*   **There is no namespace flag, and that is deliberate.** MariaDB has one
    namespace level and calls it a database, so `--database` is the whole
    answer: the run connects to a database and asks about that database. No
    `--schema`, and no alias for it, so a caller cannot name a level that does
    not exist here.
*   **Sequences are version-gated.** MariaDB gained them in 10.3, so
    `sequences` is listed among the types on every server but only answered by
    one that has them. On an older server the run refuses it with an
    unsupported-capability error naming the dialect and the family, and exits
    non-zero — the question is valid here, the server is what lacks the answer.
    The refusal is decided after connecting, from the dialect's capability,
    because that is the first moment the version is known: the parser cannot
    gate it, and hiding the type from `--help` would hide it from servers that
    do support it.
*   **`data_length` and `index_length` are estimates.** InnoDB reports
    approximate byte sizes for the clustered index, not exact file sizes.
*   **One question per invocation.** A CLI process is one connection that
    opens, answers, and closes — there is no cache carried between runs, so
    the answer reflects the server as it is *now*.

## Examples

```bash
# Sequences and storage facts, the two MariaDB-specific families
python -m rhosocial.activerecord.backend.impl.mariadb introspect sequences --database shop
python -m rhosocial.activerecord.backend.impl.mariadb introspect table-options --database shop

# One table in full
python -m rhosocial.activerecord.backend.impl.mariadb introspect table orders --database shop

# A script asks the question and reads the answer
export MARIADB_HOST=localhost MARIADB_DATABASE=shop MARIADB_USER=root MARIADB_PASSWORD=secret
python -m rhosocial.activerecord.backend.impl.mariadb introspect tables -o json | jq '.[].name'
```
