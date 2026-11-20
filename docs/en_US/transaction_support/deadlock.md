<!-- docs/en_US/transaction_support/deadlock.md -->
# Deadlocks & retry

InnoDB detects deadlocks and aborts one of the participating transactions with
an error; the other can proceed. A deadlock is a normal condition under
concurrency, not a bug in generated SQL.

## Failure handling

```python
import time

# Catch the driver's deadlock error class (or the backend error that wraps it).
for attempt in range(3):
    try:
        with backend.transaction():
            transfer_funds(from_id, to_id, amount)
        break
    except DeadlockError:  # noqa: F821 - stands for your driver's deadlock exception
        if attempt == 2:
            raise
        time.sleep(0.05 * (2 ** attempt))  # exponential backoff with jitter
```

Keep the whole unit of work inside the retry loop: rolling back must undo every
statement in the transaction before it is retried. Use exponential backoff
with a little randomness so competing workers do not retry in lockstep.

## Reducing deadlocks

- Access tables and rows in a **consistent order** across workers.
- Keep transactions **short** — do not hold a transaction open across network
  calls or user input.
- Index the columns used in `WHERE` and `JOIN` predicates so InnoDB locks only
  the rows it needs (see [Indexing](../mariadb_specific_features/indexing.md)).
- Use `FOR UPDATE` deliberately; `NOWAIT` (10.3) and `SKIP LOCKED` (10.6) let a
  transaction fail fast or skip busy rows instead of waiting.

## Integrity errors are not deadlocks

Duplicate keys, foreign-key violations and CHECK failures abort the statement,
not the transaction as a whole. Retrying them without changing the data will
fail again — handle them as validation outcomes. The backend maps the common
server error numbers (for example 1022, duplicate key) to readable labels.

## After a reconnect

The backend reopens a dropped connection on the next statement. That reconnect
ends the current transaction, so inspect the result of a failed statement
before assuming a rollback happened locally. See
[Connection management](../installation_and_configuration/pool.md).
