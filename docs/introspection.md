# Database Introspection

The MariaDB backend answers three layers of questions: what the database declares (from `information_schema` and `SHOW`), what it has been doing (the operational families), and what its rows hold (three data families). `backend.introspector` is the entry point for all three, and every answer on this page is MariaDB's own: what this engine says, not the shape a cross-dialect consumer can expect.

The contract those answers fill is core's, and this page does not restate it: the probe rules live in `backend/introspection/capabilities.md`, the operational shapes in `operations.md`, the profile and coverage types in `data-profiles.md`, all under [python-activerecord/docs](https://github.com/rhosocial/python-activerecord/tree/main/docs). What follows is only where MariaDB stands against that contract, and where its answers come from.

## Overview

- **Database information**: name, version, character set and collation, from `information_schema.SCHEMATA`
- **Tables**: name, type, comment, row estimate, data/index bytes, auto-increment counter and timestamps, from `information_schema.TABLES`
- **Columns**: declared type, nullability, default, key flags, charset and collation, plus a spatial column's declared SRID
- **Indexes**: name, uniqueness, type, columns, from `information_schema.STATISTICS`
- **Foreign keys**: column mapping and update/delete actions, from `KEY_COLUMN_USAGE` joined to `REFERENTIAL_CONSTRAINTS`
- **Views and triggers**: definitions from `VIEWS` and `TRIGGERS`
- **Table options**: engine, row format, collation, auto-increment and create options — MariaDB's own `table-options` family
- **Sequences**: from 10.3, with numeric details from 11.7 — MariaDB's own `sequences` family
- **Operational answers**: runtime instruments, foreign-key dependency edges, the engine's own DDL; three counter families refused
- **Data answers**: per-column profiles, value listings and join coverage, all aggregated over the rows

## What MariaDB Answers

Every question in the introspection contract has a probe on the dialect, and a probe is a question about the server in front of you rather than about the product. This table is MariaDB's answer to all twenty-one. Read the `False` rows first: a probe that answers `False` says the question cannot be asked of this server, never that the answer was empty or zero.

| Probe | MariaDB answers | The question it gates |
|-------|-----------------|-----------------------|
| `supports_introspection()` | `True` | Anything about the schema at all |
| `supports_database_info()` | `True` | The database's name, character set and collation |
| `supports_table_introspection()` | `True` | Tables, their type and their storage bytes |
| `supports_column_introspection()` | `True` | Columns, their declared type and SRID |
| `supports_index_introspection()` | `True` | Indexes, their columns and types |
| `supports_foreign_key_introspection()` | `True` | Foreign keys and their actions |
| `supports_view_introspection()` | `True` | Views and their definitions |
| `supports_trigger_introspection()` | `True` | Triggers, timing and definition |
| `supports_table_storage_introspection()` | `True` | Per-table data and index bytes |
| `supports_runtime_stats()` | `True` from 10.5 | What the server says is being counted |
| `supports_table_stats()` | `False` on every version | Per-table usage counters |
| `supports_index_stats()` | `False` on every version | Per-index usage counters |
| `supports_unused_indexes_detection()` | `False` on every version | Indexes with no recorded access |
| `supports_object_dependencies()` | `True` | The dependency graph — foreign keys only |
| `supports_ddl_extraction()` | `True` | The text that recreates an object |
| `supports_ddl_extraction_native()` | `True` | Whether that text is the engine's own |
| `supports_column_data_profile()` | `True` | What each column of a table holds |
| `supports_column_value_sample()` | `True` | Which values occur, and how often |
| `supports_join_coverage()` | `True` | How much two columns' domains overlap |
| `supports_partition_info()` | `False` | Core's partition family |
| `supports_extensions()` | `False` | Installed add-on components |

Two switches beyond core's set are this backend's own: `supports_table_options_introspection()`, which answers `True` for the `table-options` family, and `supports_sequence_introspection()`, which answers `version_at_least((10, 3))` for `sequences`. Each CLI type is gated on its own switch. A `True` promises only that the query renders and the server accepts it; it says nothing about the shape of the answer or its price, and the price of every family is stated where the family is described.

`supports_runtime_stats()` is the only probe above whose answer depends on a version: `True` from 10.5.0, the release that introduced the performance schema and `performance_schema.setup_instruments` with it. Below that floor the statement would name a relation the server does not serve, so the accessor is asked rather than a bare `True`.

The three counter families — `unused-indexes`, `table-stats` and `index-stats` — are refused on every release in the matrix (10.2 through 13.x), and not because they are gated on a floor nobody reached: MariaDB's performance schema is a partial port of MySQL's. It has the instrument catalogue, which is what `runtime` reads, but it registers none of the table I/O summary tables (`table_io_waits_summary_by_table`, `table_io_waits_summary_by_index_usage`) that a per-table or per-index counter would be projected from. MariaDB's own `sys` schema installs views over those tables, but a view over a table the server does not serve cannot answer: executing one is `1146`, "table does not exist", which would turn a definition-time question into an execution error. There is no floor at which MariaDB starts answering, so the probes answer `False` rather than carrying a version.

What MariaDB does report about an index — `information_schema.STATISTICS` — is its declaration and an estimated cardinality. That is a fact about what an index is, and about the shape of its data; it is never a measure of how often the optimiser reached for it. Projecting a cardinality into a slot that promises a count of operations, or a zero into one that promises "no access was recorded", would be a number the engine never measured.

`supports_object_dependencies()` is `True`, and the graph it promises is foreign keys only. `information_schema.REFERENTIAL_CONSTRAINTS` holds one row per foreign key, which is one edge per constraint, and it is read on every release in the matrix. MariaDB records no view-on-table or trigger-on-table reference anywhere, so the graph is a real one and a partial one: a caller asking "what breaks if I drop this" gets the referential answer and no more.

`supports_ddl_extraction()` and `supports_ddl_extraction_native()` are both `True`, because `SHOW CREATE TABLE` is MariaDB's own retrieval of the text it holds, not an assembly that reads as authoritative.

`supports_partition_info()` and `supports_extensions()` stay `False` by inheritance. This backend declares no partition family of the kind core's probe gates and no catalogue for installable add-on components, so there is no answer behind a `True`.

## Basic Usage

```python
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend

backend = MariaDBBackend(
    host="localhost",
    port=3306,
    database="mydb",
    username="app",
    password="secret",
)
backend.connect()
backend.introspect_and_adapt()

introspector = backend.introspector

info = introspector.get_database_info()
print(info.name, info.version, info.encoding, info.collation)

for table in introspector.list_tables():
    print(table.name, table.table_type.value,
          table.data_size_bytes, table.index_size_bytes)

for column in introspector.list_columns("orders"):
    print(column.name, column.data_type_full, column.nullable.value)
```

`backend.introspect_and_adapt()` is the step that makes a version-gated probe answer for the server the handshake reached, rather than for the version the backend was constructed with. The CLI calls it at the entrance; a caller gating on a probe should do the same. `schema` is optional throughout: MariaDB has exactly one namespace level and calls it a database, so omitting it asks about the database the connection selected.

MariaDB's two own families sit beside the core API:

```python
for sequence in introspector.list_sequences():
    print(sequence.name, sequence.start_value, sequence.increment)

options = introspector.get_table_options("orders")
if options:
    print(options.engine, options.row_format,
          options.collation, options.auto_increment)
```

`get_table_options()` answers for any relation in `information_schema.TABLES` — base table, view or sequence — and the record carries the row's `table_type`, so the caller decides whether the answer is the one it wanted. `get_sequence_info()` returns `None` below 10.3, where a sequence cannot exist; its numeric fields are `None` below 11.7, where `information_schema.SEQUENCES` arrives. Above that floor a sequence is still listed from `TABLES`, because a sequence *is* a table there.

## Structure answers worth knowing

- **System schemas.** `information_schema`, `performance_schema`, `mysql` and `sys` are excluded from the table and view listings unless `include_system=True`, through one predicate over `TABLE_SCHEMA`. The list is a fixed tuple in the dialect rather than a discovery query, because `SCHEMATA` carries no flag distinguishing a system schema from a user one.
- **Storage bytes.** `DATA_LENGTH` and `INDEX_LENGTH` are read apart into `data_size_bytes` and `index_size_bytes`, and their sum into `size_bytes`, in the parser. A relation that reports neither — a view — leaves all three `None`: a value the catalogue did not report is not a zero-byte table.
- **Spatial columns.** MariaDB does not write `REF_SYSTEM_ID=` into `COLUMN_TYPE` or `SHOW CREATE`; the declared SRID exists only in `I_S.GEOMETRY_COLUMNS`, which the column statement left-joins. A non-zero `SRID` is folded back into `data_type_full` as `REF_SYSTEM_ID=n`, so the parsed type carries the declaration the differ needs to see. `SRID` 0 is MariaDB's default coordinate system and means "no declaration".
- **Sequences are tables.** A sequence appears in `information_schema.TABLES` with `TABLE_TYPE='SEQUENCE'`, so the table listing excludes that spelling on every version — a no-op below 10.3, where the type cannot exist — and `list_sequences()` stays the one answer for sequences.
- **Index types.** `BTREE`, `HASH` and `FULLTEXT` map to the member of the same name; `SPATIAL` and `RTREE` both read as `IndexType.SPATIAL`.

## Operational Families

MariaDB declares all six, and three of the six answer no query at all.

| Family | Method | MariaDB source | Price |
|--------|--------|----------------|-------|
| Unused indexes | `list_unused_indexes()` | none — refused by the probe | no query is run |
| Table counters | `list_table_usage_stats()` | none — refused by the probe | no query is run |
| Runtime metrics | `list_runtime_metrics()` | `performance_schema.setup_instruments` | One server-wide instrument read |
| Index counters | `list_index_usage_stats()` | none — refused by the probe | no query is run |
| Dependencies | `list_object_dependencies()` | `information_schema.REFERENTIAL_CONSTRAINTS` | One catalogue read |
| DDL | `get_ddl_statement()` | `SHOW CREATE TABLE` | One statement, engine-side |

The tense is the fact most easily lost, and here it is mostly the tense of a *state* rather than of a counter. An edge in the dependency graph and a line of DDL are what the catalogue holds now; the runtime listing says which instruments are enabled now. No family on this engine reports an access count, because the three that would are the three that are refused. A cached answer therefore ages like a schema rather than like a clock: a graph cached yesterday is probably still the graph.

### The three counter families

`unused-indexes`, `table-stats` and `index-stats` are declared gaps, and the declaration is the answer. MariaDB registers no per-index access counter and no per-table access counter, so there is nothing to project into `scans`, `rows_fetched`, `count_read` or `sequential_scans`, and no row estimate that belongs beside them either: `information_schema.TABLES` carries `TABLE_ROWS`, which is an estimate from a different source with a different refresh schedule, and putting it next to counters would look more correlated than it is.

The methods still exist on the introspector, but this backend has no rendering for the statements behind them, so an unguarded call reaches a family that was never written. The probe is what a caller reads first, and the CLI reads it too: it exits **2** with "not supported by this server" without sending a statement. That is a different answer from an empty list, and the difference matters — "this server cannot be asked" is not "no index was used".

### Runtime Metrics

The listing reads `performance_schema.setup_instruments`, which names what is actually being counted on this server. It projects `NAME` as `name`, `ENABLED` as `value` and `TIMED` as `kind`, ordered by name. The relation has no schema column and is server-wide, so no schema filter is applied — a filter here would refuse a correct query for a nonsensical reason.

This answers "what is alive" rather than "how much happened": an instrument that is not enabled produces no row, so there is no zero that could read as idle. `unit`, `description` and `source` stay `None`, because the relation names none of them. The collector is an install-time option, off by default and not enableable at runtime; on a server started without it the listing is empty, and that empty answer is the collector's silence rather than a measurement of inactivity. No row is manufactured to fill the gap.

### Object Dependencies

One row per foreign key, projected onto the slots core reads: the table that declares the constraint is the **dependent** side, the table its key points at is the **referenced** one, and `DELETE_RULE` arrives as `action`. Which side a table is on is decided by which column of `REFERENTIAL_CONSTRAINTS` the row is read from, not by the caller's question — "what breaks if I drop orders" and "what does orders need" are two readings of the same rows.

`kind`, `dependent_type` and `referenced_type` stay `None`: this catalogue covers foreign keys only and records neither the kind of relation nor the kind of object on either side. Naming a table narrows the answer to the edges it carries; omitting the name returns the whole graph for the schema. The schema filter is applied in the statement, because the catalogue is database-wide and asking about one database should not mean post-filtering the rest.

### DDL Extraction

`SHOW CREATE TABLE`, read under the engine's own result-column names: `Table` and `Create Table`. Core's generic parser looks for `ddl`, `sql` or `definition`, and none of those exists in a `SHOW CREATE` row — so this backend overrides the parser rather than letting a table the engine had just described be reported as having no DDL. Both spellings of each column are read, because the driver is not consistent about which one it keeps.

`native` is `True`: the text is the engine's retrieval, not an assembly. Only `TABLE` is rendered. Naming `VIEW`, `PROCEDURE`, `FUNCTION`, `TRIGGER` or `SEQUENCE` raises `UnsupportedFeatureError`, because each takes a different `SHOW CREATE` statement and a different result column, and this backend has not mapped them. When a schema is named it rides the catalog slot of the relation; left empty, the name is unqualified and MariaDB resolves it in the database the run connected to — the same answer a hand-typed `SHOW CREATE TABLE users` would get.

Every family — answered or refused — is reached through the same introspector, sync and async alike:

```python
backend.introspect_and_adapt()

if backend.dialect.supports_runtime_stats():
    for metric in backend.introspector.list_runtime_metrics():
        print(metric.name, metric.value, metric.kind)

for edge in backend.introspector.list_object_dependencies("orders"):
    print(f"{edge.dependent} -> {edge.referenced} ({edge.action})")

ddl = backend.introspector.get_ddl_statement("orders")
if ddl is not None:
    print(ddl.native, ddl.ddl)
```

## Data Families

The three data families measure the rows rather than read a catalogue. MariaDB has a per-column statistics catalogue of its own — `mysql.column_stats`, written by `ANALYZE TABLE ... PERSISTENT FOR COLUMNS` — and it was audited before it was refused. Its layout is `db_name`, `table_name`, `column_name`, `min_value`, `max_value` (both `varbinary(255)`), `nulls_ratio` (`decimal(12,4)`), `avg_length`, `avg_frequency`, `hist_size`, `hist_type` and `histogram`. Read against the five figures core promises, that is one usable field out of five:

| Family | Method | Price |
|--------|--------|-------|
| Column profiles | `list_column_data_profiles(table)` | One pass over the table per column |
| Value samples | `sample_column_values(table, column, limit=100)` | One grouped pass over the column, plus a sort |
| Join coverage | `estimate_join_coverage(left_table, left_column, right_table, right_column)` | Two sides read for their distinct domains, plus the intersection |

- `nulls_ratio` is the null fraction, already a ratio — but it is an approximation, and the table records no collection time, so the family's rule that an estimate carries its vintage cannot be met for it. The honest label would be `UNKNOWN`, never `ESTIMATE`.
- `min_value`/`max_value` hold the value in the column's *internal encoding*, not in a form SQL can read back. Strings happen to be their bytes; an `INT` is a packed integer, a `DATETIME` a packed long, a `DECIMAL` its binary decimal. Decoding those is per-type work in the client, not a cast the engine can do, so both endpoints would be mojibake.
- There is no distinct count. `avg_frequency` is the average number of rows sharing a value, so a count is only reachable by dividing the table's row count by it — a quotient of two estimates from two different tables, in a slot that promises a count.
- `histogram`/`hist_type` are the optimiser's bucket encoding, a distribution this contract does not model and does not want half of.

Two further facts decide the matter. The table is **empty** until an operator asks for statistics, so a catalogue-only answer is "not measured" on every fresh server — correct, and useless; a zero-filled profile there would be worse. And reading it needs `SELECT` on the `mysql` database, which an application account routinely lacks, so a profile that failed on privileges where the aggregate would have answered would be a regression dressed as an optimisation.

So every figure comes from one place: the rows. The `aggregate` label is projected *into* each row rather than stamped onto the result afterwards, so a consumer comparing a MariaDB profile with another engine's estimate can tell them apart without knowing which engine it asked. The empty catalogue is then not a special case at all — there is nothing to read, so nothing can be mistaken for a measurement.

### Column Profiles

One `UNION ALL` arm per column of the table, and each arm reads the table once: the null count is a `SUM` over a `CASE`, the distinct count `COUNT(DISTINCT ...)`, the endpoints the engine's `MIN`/`MAX`, and `COUNT(*)` rides the same scan as the divisor. A table of ten columns is therefore read ten times — the number of round trips stays one, the number of scans does not. `null_fraction` is derived in the parser (`null_count / row_count`), so a row count that may be zero never has to be guarded in SQL. An empty table answers `null_fraction = None` because `SUM` over no rows is NULL — absence of a measurement, not "no nulls" — while `distinct_count` and `row_count` are `0`, which are measurements.

One consequence of the compound statement is visible only in Python types. MariaDB resolves one result type per column position across every `UNION ALL` arm, so `min_value` — which holds `code`'s text in one arm and `amount`'s decimal in another — arrives as text: `'1.00'`, not `1.00`. The figures are exact; only the type is the union's. Read a decimal endpoint through `Decimal(str(value))`. One query per column would keep each native type, at the price of a round trip per column, which is the loop this family exists to avoid.

An empty column list answers with no rows. It cannot arise from a real table — MariaDB requires at least one column — but the branch renders as a statement that selects no rows rather than a special-cased string.

### Value Samples

A `GROUP BY` over the column plus a sort of the groups — the same order of cost as the profile, which is why the two are separate calls: a caller wanting only the listing does not pay for the profile's distinct counts and endpoints. `ORDER BY COUNT(*) DESC` is what makes the answer "the most frequent values" rather than "the first values", and ties break by the value so two runs of the same query agree. The limit is bound as a parameter, so the caller's integer is never spliced into statement text. Only `value` and `count` are projected; `frequency` stays `None`, because the engine reports a count and the denominator is the row count the profile carries.

`GROUP BY` groups NULLs, so a column that contains NULL has an entry whose `value` is `None`, and it is usually the most frequent one. NULL is a member of the domain in this listing, and the parser does not skip it — unlike address rows elsewhere, which skip a row with no identity. A caller reading this as "the values in this column" must not assume every entry is a value; the profile's `null_fraction` is the cross-engine measure of the same fact.

### Join Coverage

Both fractions come from one statement. For each side, the numerator counts the distinct values that also occur on the other side — a `COUNT(*)` over a derived `DISTINCT` — and the denominator counts that side's distinct non-NULL values. Distinct on both sides is what makes the figure a coverage of values rather than of rows: a key repeated a thousand times that matches once would otherwise read as well covered. NULLs are excluded from both halves explicitly; a `DISTINCT` would count NULL as one value and credit a match that can never join. `NULLIF(..., 0)` makes a column with nothing to match answer NULL rather than `0.0`, so "nothing matched" and "nothing to match" stay distinct.

There is no `* 1.0` here: MariaDB's division of two integer counts already answers a fractional `DECIMAL`. Collations are not reconciled — the engine compares the two columns under whichever collation applies, so values the database would treat as equal may be counted as distinct, and across mismatched collations the fractions are a *lower* bound, never an upper one. The price is the two sides read for their distinct domains plus the intersection, with each side's fraction paying a second pass for its denominator, which is why this is a call of its own and never part of a profile.

```python
profiles = backend.introspector.list_column_data_profiles("orders")
for profile in profiles:
    print(profile.column_name, profile.null_fraction, profile.distinct_count,
          profile.row_count, profile.source)

samples = backend.introspector.sample_column_values("orders", "status", limit=20)
for sample in samples:
    print(sample.value, sample.count)    # value is None when NULL is a group

coverage = backend.introspector.estimate_join_coverage(
    "orders", "customer_id",
    "customers", "id",
)
print(coverage.left_coverage, coverage.right_coverage)
```

## Version and Availability Floors

Two limits decide whether an operational or data family can answer at all, and neither is a property of the query text.

| Family | Floor | What a missing floor looks like |
|--------|-------|---------------------------------|
| `runtime` | MariaDB 10.5.0, where the performance schema and `setup_instruments` arrive | probe `False`; the CLI exits 2 without running the query |
| `unused-indexes`, `table-stats`, `index-stats` | none — no release answers them | probe `False` on every version; the CLI exits 2 without running the query |
| `sequences` (MariaDB's own family) | 10.3, where a sequence can exist; numeric details from 11.7 | empty list / `None` below 10.3; detail fields `None` below 11.7 |
| every other family | none established here | — |

The performance schema is a version floor for `runtime` and an install-time option for what it reports. The probe cannot see the server's startup options, so it answers `True` from 10.5 on, where the relation exists; on a server started with the collector off the listing returns nothing, and that empty answer is not a measurement of idleness.

A probe answering `False` is "the question cannot be asked here", not "nothing was used". It does not say that no index was used, that no table was read, or that the database has no indexes: it says the server cannot be asked. `False` lets a caller take its fallback knowingly; the empty list is reserved for a question that was asked and had nothing to report.

The probes do not test grants. No privilege floor is established here: a probe answers about the server and its settings, not about the account's privileges. If the connected account may not read a relation the engine does expose, the engine's own error arrives at execution; the probe said `True` because the server can answer, not because this account may ask. The three refused families are refused for the shape of the catalogue, not for a grant: `mysql.column_stats` would have needed privileges an application account lacks, but that is one of the reasons the profile does not read it, not a probe.

## Command Line Introspection

```bash
# One database, one namespace level: --database is the whole answer.
python -m rhosocial.activerecord.backend.impl.mariadb introspect tables \
  --host localhost --database mydb --user app --password secret

# One table, or one sequence
python -m rhosocial.activerecord.backend.impl.mariadb introspect columns orders --database mydb
python -m rhosocial.activerecord.backend.impl.mariadb introspect sequences my_seq --database mydb

# The engine's own DDL, and exact profiles over the rows
python -m rhosocial.activerecord.backend.impl.mariadb introspect ddl orders --database mydb
python -m rhosocial.activerecord.backend.impl.mariadb introspect column-profiles orders --database mydb
python -m rhosocial.activerecord.backend.impl.mariadb introspect value-samples orders \
  --column status --limit 20 --database mydb

# The families this engine does not answer are refused after connecting, exit 2
python -m rhosocial.activerecord.backend.impl.mariadb introspect unused-indexes --database mydb
```

There is no `--schema` flag, and that is deliberate: MariaDB has one namespace level and calls it a database, so `--database`, which the connection already takes, is the whole answer. An earlier flag naming the same thing under a word MariaDB does not use is gone rather than aliased, so a caller cannot quietly end up asking about a different level than the one it is connected to.

### Introspection Types

| Type | Description | Name |
|------|-------------|------|
| `tables` | Every relation in the database, minus sequences | not accepted |
| `views` | List all views, or describe one | optional (view) |
| `columns` | Column information of one table | required (table) |
| `indexes` | Index information of one table | required (table) |
| `foreign-keys` | Foreign keys of one table | required (table) |
| `triggers` | All triggers, or one table's | optional (table) |
| `database` | Name, charset, collation and version | not accepted |
| `sequences` | List sequences, or describe one | optional (sequence) |
| `table-options` | Engine, row format, collation, auto-increment, create options | optional (relation) |
| `unused-indexes` | Indexes with no recorded access — refused on every version | not accepted |
| `table-stats` | Per-table usage counters — refused on every version | not accepted |
| `runtime` | Live instrument listing, from 10.5 | not accepted |
| `index-stats` | Per-index usage counters — refused on every version | not accepted |
| `dependencies` | Foreign-key dependency edges | optional (table) |
| `ddl` | `SHOW CREATE TABLE` text of one table | required (table) |
| `column-profiles` | What each column of a table holds | required (table) |
| `value-samples` | Most frequent values of one column | required (table), plus `--column` |
| `join-coverage` | Overlap of two columns' value domains | not accepted; four flags required |

The nine operational and data families are the set the other CLIs ask for too, and each one names the probe that answers for it here — which is not automatically the same answer it gives elsewhere. A name the type cannot use is refused (exit 2) rather than ignored; a missing required name or flag is an incomplete invocation (exit 1); a flag the type does not read is refused (exit 2). `dependencies` narrows to a table's edges and answers the whole graph without a name. `--limit` is forwarded to `sample_column_values()` only when it is given; without it the introspector's own default answers (`VALUE_SAMPLE_LIMIT`, 100), so the number is not written in two places.

`ddl` prints the engine's text alone in the table format, under a one-line `-- TABLE <name>` header; in the formats a caller parses it prints the record — schema, object type, object name, `native` and the text — which is what `native` is for. `column-profiles` writes one note to stderr saying the profiles are aggregated from the rows themselves and paid for with a full scan per column, so a caller piping JSON to a consumer still sees where the numbers came from.

### Output and connection

`-o table` (default, rich), `json`, `csv` and `tsv` are available for every type; `--rich-ascii` switches the table borders. `--include-system` widens the table and view listings to the system schemas. Connection parameters can be given as flags or as environment variables:

| Flag | Environment variable | Default |
|------|----------------------|---------|
| `--host` | `MARIADB_HOST` | `localhost` |
| `--port` | `MARIADB_PORT` | `3306` |
| `--database` | `MARIADB_DATABASE` | required for introspection |
| `--user` | `MARIADB_USER` | `root` |
| `--password` | `MARIADB_PASSWORD` | empty |
| `--charset` | `MARIADB_CHARSET` | `utf8mb4` |

`--ssl` selects one of `auto`, `require`, `verify-ca`, `verify-full` and `disabled`, defaulting to `auto`; only `disabled` changes what this backend sends, by turning TLS off. A named connection profile (`--named-connection`) may stand in for `--database` when one is configured. `--async` runs the same command through `AsyncMariaDBBackend`; every family is asked the same way and the answers are the same.
