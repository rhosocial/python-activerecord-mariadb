<!-- docs/en_US/transaction_support/README.md -->
# Transaction Support

The MariaDB backend offers ACID transactions on transactional storage engines
(use InnoDB). `MariaDBBackend.transaction()` and `AsyncMariaDBBackend.transaction()`
share the same context-manager API; the async form adds `await`.

```python
with backend.transaction():
    backend.execute(insert_sql, params)
    backend.execute(update_sql, params)
# committed on success, rolled back on exception
```

Set `autocommit=False` (the default) so commits are controlled by the
transaction context. With `autocommit=True`, each statement commits on its own
and the context manager has nothing to roll back.

## Chapters

- [Isolation levels](isolation_level.md)
- [Savepoints](savepoint.md)
- [Deadlocks & retry](deadlock.md)

## Important boundaries

- **DDL** — `CREATE`, `ALTER`, `DROP` and partition maintenance implicitly
  commit; they cannot be rolled back.
- **Engine choice** — a non-transactional engine cannot honour a rollback even
  though the SQL layer issues one.
- **Reconnect** — the backend reconnects lazily after a failed statement; a
  reconnect ends the current transaction, so retry decisions belong at the
  application level (see [Deadlocks & retry](deadlock.md)).
- **Row locks** — `FOR UPDATE` is supported; `NOWAIT` (10.3) and `SKIP LOCKED`
  (10.6) have separate version gates.

Generic transaction semantics (the backend protocol) are part of the
[core library manual](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).
