<!-- docs/en_US/troubleshooting/performance.md -->
# Performance issues

## Start with the plan

Run [EXPLAIN](../mariadb_specific_features/explain.md) on the slow statement:

- `type = ALL` — a full scan; check that the filter columns are indexed.
- `key = NULL` with populated `possible_keys` — the optimiser chose a scan,
  often because the predicate is not sargable (for example a function applied
  to an indexed column, or a leading `%` in `LIKE`).
- `Using filesort` / `Using temporary` — ordering or grouping could not use an
  index; consider a composite index matching `WHERE` then `ORDER BY`.

## Index design

Index the columns used in `WHERE`, `JOIN` and `ORDER BY`, respecting the
leftmost-prefix rule of composite indexes. Do not add indexes speculatively —
each one costs write amplification. `information_schema.STATISTICS` reports
cardinality, not usage frequency; this backend deliberately does not expose
per-index usage counters. See [Indexing](../mariadb_specific_features/indexing.md).

## JSON and text

A predicate on a JSON path cannot use a normal index on the whole document.
Extract the path into a generated column and index that column. For text
search, use a `FULLTEXT` index with `MATCH ... AGAINST` instead of
`LIKE '%term%'`.

## Transactions and locking

- Keep transactions short; long ones hold locks and grow the undo log.
- Use the lowest isolation level that is correct for the workload (see
  [Isolation levels](../transaction_support/isolation_level.md)).
- Under contention, `NOWAIT` or `SKIP LOCKED` can fail fast instead of waiting;
  retry deadlocks with backoff (see [Deadlocks & retry](../transaction_support/deadlock.md)).

## Batches and round trips

Prefer batch inserts and set-based updates over per-row calls. Preview with
`.to_sql()` to confirm a single statement is being emitted. The core manual
documents
[batch operations](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US/performance)
at the model layer.

## Money and precision

Using `float` for money causes rounding drift, not speed gains. Use `Decimal`
with `DECIMAL(p, s)`; the adapter keeps values exact end to end (see
[Type mapping](../type_adapters/mapping.md)).
