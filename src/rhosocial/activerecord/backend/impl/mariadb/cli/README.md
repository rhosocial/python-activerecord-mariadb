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

| Type | Reads | `NAME` | Notes |
| :--- | :--- | :--- | :--- |
| `tables` | `information_schema.tables` | none | Base tables. `--include-system` adds MariaDB's own metadata databases. |
| `views` | `information_schema.views` | optional: one view | With a name, that view's definition, check option and updatability. |
| `columns` | `information_schema.columns` | required: a table | One table's columns: name, type, nullability, default. |
| `indexes` | `information_schema.statistics` | required: a table | One table's indexes, including the primary key. |
| `foreign-keys` | `information_schema.key_column_usage` | required: a table | One table's constraints and the columns each side names. |
| `triggers` | `information_schema.triggers` | optional: a table | Every trigger, or one table's. |
| `sequences` | `information_schema.sequences` | optional: a sequence | MariaDB's own sequences. **10.3 and later** — on an older server `sequences` is refused, not answered empty. |
| `table-options` | `information_schema.tables` | optional: a table | The storage facts about a table: engine, row format, collation, auto-increment, comment, and the byte sizes `information_schema` reports. |
| `database` | `information_schema.schemata`, `variables` | none | Server version, charset, and the databases visible to this role. |

`NAME` is required where it names the object the answer is *about*: `columns`,
`indexes` and `foreign-keys` read one table's children, so without a table
there is no question to ask. It is optional for `triggers` (all triggers, or
one table's), `sequences`, `table-options` and `views` (the list, or that one
object). `tables` and `database` answer for the whole database and **refuse**
a name, because neither can narrow its answer: `tables NAME` would have to
become the aggregate of columns, indexes and foreign keys that the removed
`table` type used to be.

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

## Exit codes

| Code | Means |
| :--- | :--- |
| `0` | The question was answered. |
| `1` | The run failed: the connection did not open, a query errored, or the object named does not exist on this server. |
| `2` | The request cannot be served here: an unknown type (argparse), a name where the type takes none, or a family this server does not support. |

The split exists so a script can tell "the server is down" from "this server
cannot answer that". Both are non-zero, and a caller that only wants to know
whether it got an answer treats them the same; a caller that retries or falls
back needs the difference.

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
    one that has them. On an older server the run prints
    `Error: sequences introspection is not supported by this server` and exits
    **2** — the question is valid here, the server is what lacks the answer.
    The refusal is decided after connecting, from the dialect's capability,
    because that is the first moment the version is known: the parser cannot
    gate it, and hiding the type from `--help` would hide it from servers that
    do support it.
*   **`SHOW` stays in the library, and is not a type here.** The backend's
    `show_introspector` exposes MariaDB's nineteen `SHOW` statements, and none
    of them is reachable through `introspect`. Three reasons:
    most of them are not catalogue metadata at all — `variables`, `status`,
    `processlist`, `warnings` and `errors` are configuration, running
    counters, and leftovers in this session; `create_table`, `create_view` and
    `create_trigger` return DDL *text*, where `columns`, `views` and `triggers`
    already answer the same thing as structured rows; and `table_status` and
    `processlist` read a moment, so two calls a second apart differ — nothing
    to do inside a command that claims to read the catalogue. Call them from
    the library, where the result is a value the caller inspects.
    `show.grants` sits at a vocabulary boundary rather than a technical one: a
    privilege listing is a family some backends have as a type and this one
    does not, so it waits for that word to be settled across backends instead
    of being invented here.
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

# One view, with its definition
python -m rhosocial.activerecord.backend.impl.mariadb introspect views user_summary --database shop

# One table's columns
python -m rhosocial.activerecord.backend.impl.mariadb introspect columns orders --database shop

# A script asks the question and reads the answer
export MARIADB_HOST=localhost MARIADB_DATABASE=shop MARIADB_USER=root MARIADB_PASSWORD=secret
python -m rhosocial.activerecord.backend.impl.mariadb introspect tables -o json | jq '.[].name'
```
