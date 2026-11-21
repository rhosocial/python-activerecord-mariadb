# MariaDB backend-specific AR migration examples (offline dry-run)

This directory complements the core `docs/examples/ar-migration/` examples.  It shows
the **same migration intent** — partitioning a table — and how MariaDB renders the
SQL differently from the other backends.  Everything runs **fully offline**: no
database, no connection, and no `ctx.apply()`.  A connection-less `MariaDBDialect`
answers the eight backend-suggestion protocols with MariaDB-owned expression nodes,
and the only SQL printed is whatever `expr.to_sql()` renders.

## Hard rules for these scripts

- No hand-built SQL strings — every printed statement comes from `expr.to_sql()`.
- No `ctx.apply()` — we render suggestions only, never execute them.
- No source/contract-test changes — these are new example files only.

## MariaDB-specific contract

- The dialect is built with no arguments: `MariaDBDialect()`.
- The plan is a **plain dict** read by many aliases (`table`, `definitions`, `keys`,
  `partition_names`, `partition`, `into`, `count`).  Attribute-style plans also work.
- `build` takes a **string strategy** — one of the eight MariaDB spellings:
  `RANGE`, `RANGE COLUMNS`, `LIST`, `LIST COLUMNS`, `HASH`, `LINEAR HASH`, `KEY`,
  `LINEAR KEY`.  An unknown strategy returns `operations is False`.
- `RANGE`/`RANGE COLUMNS` definitions use `less_than`; `LIST`/`LIST COLUMNS` use
  `in_values`; `HASH`/`KEY` use a `count`.
- `table_drop` needs **no plan**: it returns a 2-operation chain
  (`REMOVE PARTITIONING` then `DROP TABLE`).
- `table_alter`: HASH/KEY → `COALESCE PARTITION`; RANGE/LIST → `REMOVE PARTITIONING`.
- `retention`: one `DROP PARTITION` per RANGE definition carrying `less_than`;
  LIST/HASH return `False`.
- `merge` is **always** `False` — MariaDB has no `MERGE PARTITION` DDL
  (`COALESCE PARTITION` is the unrelated HASH/KEY folding operation).

## Scripts and scenarios

### `01_partition_build.py` — build (CREATE TABLE partition clause)

| Scenario | What it shows |
|----------|---------------|
| `build / RANGE` | `PARTITION BY RANGE` with `less_than` boundaries |
| `build / RANGE COLUMNS` | `PARTITION BY RANGE COLUMNS` on a column key |
| `build / LIST` | `PARTITION BY LIST` with `in_values` boundaries |
| `build / LIST COLUMNS` | `PARTITION BY LIST COLUMNS` |
| `build / HASH` / `LINEAR HASH` | `PARTITION BY HASH` / `LINEAR HASH` with a count |
| `build / KEY` / `LINEAR KEY` | `PARTITION BY KEY` / `LINEAR KEY` with a count |
| `build / unknown strategy` | explicit unsupported tri-state (`operations is False`) |

### `02_partition_lifecycle.py` — add / drop / retention and table-level changes

| Scenario | What it shows |
|----------|---------------|
| `table_drop / no plan` | 2-op chain: `REMOVE PARTITIONING` → `DROP TABLE` |
| `table_drop / with plan` | same chain, targeting the plan's table |
| `table_alter / HASH → COALESCE` | `ALTER TABLE ... COALESCE PARTITION` |
| `table_alter / RANGE → REMOVE` | `ALTER TABLE ... REMOVE PARTITIONING` |
| `add / RANGE` | `ALTER TABLE ... ADD PARTITION` |
| `drop / explicit partition_names` | `ALTER TABLE ... DROP PARTITION` (named in plan) |
| `drop / names from definitions` | `DROP PARTITION` (names read from definitions) |
| `split / RANGE` | `ALTER TABLE ... REORGANIZE PARTITION ... INTO` |
| `merge / RANGE` | always unsupported (`operations is False`) |
| `retention / RANGE` | one `DROP PARTITION` per `less_than` definition |
| `retention / LIST` | unsupported (`operations is False`) |
| `{add,drop,split,table_alter} / unknown strategy` | explicit unsupported tri-state |

## How to run

From the repository root (Python 3.14, dependencies already in `.venv3.14`):

```powershell
$env:PYTHONPATH='src'
.\.venv3.14\Scripts\python.exe docs\examples\ar-migration\01_partition_build.py
.\.venv3.14\Scripts\python.exe docs\examples\ar-migration\02_partition_lifecycle.py
```

Both scripts exit `0` and print only rendered SQL (plus section labels).  They are
examples of the **suggest → render** workflow — the same expression nodes a migration
toolchain would hand to a backend only after an operator reviews the generated SQL.
