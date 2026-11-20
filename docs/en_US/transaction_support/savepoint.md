<!-- docs/en_US/transaction_support/savepoint.md -->
# Savepoints

A savepoint is a named marker inside a transaction. Rolling back to it undoes
work done after the marker without aborting the whole transaction. The dialect
exposes `supports_savepoint()`; savepoints are available on every MariaDB
version in the supported matrix.

```python
with backend.transaction():
    backend.execute("INSERT INTO orders (total) VALUES (10)", ())

    backend.execute("SAVEPOINT before_discount", ())
    backend.execute("UPDATE orders SET total = total - 3 WHERE id = LAST_INSERT_ID()", ())

    try:
        apply_discount()  # may raise
    except DiscountError:
        backend.execute("ROLLBACK TO SAVEPOINT before_discount", ())
        backend.execute("RELEASE SAVEPOINT before_discount", ())

    backend.execute("INSERT INTO audit (event) VALUES ('order created')", ())
```

The outer transaction still commits the insert and audit row; only the
discount update is undone.

## Notes

- `ROLLBACK TO SAVEPOINT` does **not** release the savepoint; issue
  `RELEASE SAVEPOINT` when it is no longer needed.
- Creating a savepoint with a name that already exists replaces the older one.
- A full `ROLLBACK` removes all savepoints.
- Savepoints are connection-local. A reconnect (see
  [Connection management](../installation_and_configuration/pool.md)) discards
  them along with the transaction.

For application-level nesting, prefer one explicit transaction with a few
well-placed savepoints over deeply nested "transaction" helpers — each nested
helper that starts its own transaction would commit independently.
