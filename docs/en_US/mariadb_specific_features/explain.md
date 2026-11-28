<!-- docs/en_US/mariadb_specific_features/explain.md -->
# EXPLAIN

EXPLAIN reports the plan MariaDB's optimiser chose for a statement. The backend
returns typed rows rather than raw tuples, and supports both the tabular and the
JSON/ANALYZE forms where the server version allows.

## Basic EXPLAIN

```python
from rhosocial.activerecord.backend.expression import QueryStatement

stmt = QueryStatement(
    dialect=dialect,
    select=[Column(dialect, "*")],
    from_=Table(dialect, "orders"),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(dialect, "=", Column(dialect, "status"), Parameter(dialect, "paid")),
    ),
)
result = backend.explain(stmt)
for row in result.rows:
    print(row.select_type, row.table, row.type, row.possible_keys, row.key, row.rows)
```

`MariaDBExplainRow` carries the familiar columns (`id`, `select_type`, `table`,
`type`, `possible_keys`, `key`, `key_len`, `ref`, `rows`, `filtered`, `Extra`).
`MariaDBExplainResult` wraps the rows; the JSON shape is
`MariaDBExplainJsonResult` and the `ANALYZE FORMAT=JSON` shape is
`MariaDBExplainAnalyzeResult`.

## Reading the key columns

| Column | Meaning |
|--------|---------|
| `type` | Access method — `system` / `const` / `ref` / `range` / `index` / `ALL`; `ALL` means a full scan |
| `possible_keys` | Indexes the optimiser considered |
| `key` | The index actually chosen |
| `rows` | Estimated rows to examine |
| `Extra` | Notes such as `Using index`, `Using filesort`, `Using temporary` |

A `type` of `ALL` on a large table, or `Using filesort` / `Using temporary` on a
hot query, is the usual signal to revisit an index (see
[Indexing](indexing.md)).

## FORMAT=JSON and ANALYZE

`EXPLAIN FORMAT=JSON` is available from MariaDB 10.6 (gate
`EXPLAIN_FORMAT`). It exposes cost estimates and plan details the tabular form
does not. For measured rather than estimated figures, run
`ANALYZE FORMAT=JSON <statement>` — it executes the statement, so use it on
read-only or safely repeatable queries.

## Statement-level, not cached

An EXPLAIN is a plan for one statement as parsed against the current schema and
statistics. It is not a historical record; re-run it after index or data
changes. The [introspection](introspection.md) page explains why the backend
does not expose per-index usage counters as a substitute.
