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
| `sequences` | `information_schema.sequences` | MariaDB's own sequences. **10.3 and later** — on an older server the question has nothing to answer and reports empty. |
| `table-options` | `information_schema.tables` | The storage facts about a table: engine, row format, collation, auto-increment, comment, and the byte sizes `information_schema` reports. |
| `database` | `information_schema.schemata`, `variables` | Server version, charset, and the databases visible to this role. |

`NAME` is required for `table`, `columns`, `indexes`, `foreign-keys` and, for
one sequence, `sequences`. The list types take no name.

## Options

| Option | Default | Description |
| :--- | :--- | :--- |
| `-o, --output` | `table` | `table` (rich), `json`, `csv`, `tsv`. |
| `--schema` | the connected database | The database to read. MariaDB's only namespace level above a table. |
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
*   **Sequences are version-gated.** MariaDB gained them in 10.3. The
    capability is declared per version, so a 10.2 server neither advertises
    the scope nor has the statements — asking there reports the family as
    unsupported rather than failing to parse `CREATE SEQUENCE`.
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
