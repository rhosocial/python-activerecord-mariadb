<!-- docs/en_US/mariadb_specific_features/indexing.md -->
# Indexing

Indexes can be declared inline in a `CREATE TABLE`, added later with
`CREATE INDEX`, or inspected from `information_schema.STATISTICS`.

## Inline indexes in CREATE TABLE

```python
from rhosocial.activerecord.backend.expression.statements.ddl_table import IndexDefinition

indexes = [
    IndexDefinition(dialect, name="idx_orders_customer", columns=["customer_id"]),
    IndexDefinition(dialect, name="idx_orders_status", columns=["status", "created_at"]),
]
```

A unique index uses the corresponding unique constraint node; primary keys are
declared as column constraints. The backend renders MariaDB's `KEY` / `UNIQUE
KEY` spelling and quotes identifiers with backticks.

## CREATE INDEX expressions

The backend's `create_index` and `unique_index` DDL expressions render
standalone `CREATE INDEX` / `CREATE UNIQUE INDEX` statements, including index
type and prefix length where applicable. See the DDL chapter and the
[DDL example script](../../examples/chapter_04_ddl/ddl.py).

## Design notes

- **Leftmost prefix** — a composite index `(status, created_at)` serves
  predicates on `status` alone as well as on both columns, but not on
  `created_at` alone.
- **Selectivity** — index columns that narrow rows early; a `BOOLEAN`/tiny-int
  flag alone is usually a poor leading column.
- **Full-text** — use MariaDB's `FULLTEXT` index and the `MATCH ... AGAINST`
  expression family instead of `LIKE '%term%'`; see the
  [dialect](dialect.md) page for the available nodes.
- **JSON** — index a generated column that extracts the JSON path rather than
  the whole document.

## Measuring index use

`information_schema.STATISTICS` reports an index's declaration and an estimated
cardinality — a fact about its shape, **not** a count of how often the optimiser
used it. The introspection probes for per-index/per-table usage counters and
unused-index detection are `False` on this backend (see
[Introspection](introspection.md)); use `EXPLAIN` to see which index a specific
query chooses.

## Inspecting indexes

```python
for index in backend.introspector.list_indexes("orders"):
    print(index.name, index.non_unique, index.columns)
```

`list_indexes()` covers primary keys and unique keys; foreign keys are reported
by `list_foreign_keys()` and CHECK constraints by `list_constraints()`.
