<!-- docs/en_US/transaction_support/isolation_level.md -->
# Isolation levels & transaction modes

MariaDB's default isolation level is `REPEATABLE READ`. The backend exposes
transaction setup through the connector and through SQL, depending on the
server version.

```python
from rhosocial.activerecord.backend.options import ExecutionOptions

# At the SQL layer, when the server supports it (10.2+):
backend.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED", ())
with backend.transaction():
    ...
```

The dialect's capability probes include `supports_transaction_mode()` (10.2),
`supports_isolation_level_in_begin()`, `supports_read_only_transaction()` (10.2),
`supports_deferrable_transaction()` and `supports_transaction_wait()`. Consult
them before emitting a mode clause on an older server (see
[Version gates](../mariadb_specific_features/version_gates.md)).

## Choosing a level

| Level | Effect |
|-------|--------|
| `READ UNCOMMITTED` | Dirty reads possible; rarely needed |
| `READ COMMITTED` | Each consistent read sees the latest committed snapshot |
| `REPEATABLE READ` | MariaDB default; consistent snapshot within a transaction |
| `SERIALIZABLE` | Strongest; transactions effectively serialised |

InnoDB uses next-key locking at `REPEATABLE READ` to prevent phantoms for
locking reads. For hot read/write workloads, `READ COMMITTED` reduces gap
locking at the cost of a non-repeatable snapshot.

## Read-only transactions

`SET TRANSACTION READ ONLY` (10.2+) lets the server skip writes to the undo log
for a reporting transaction. Start one explicitly when a unit of work never
writes:

```python
backend.execute("SET TRANSACTION READ ONLY", ())
with backend.transaction():
    rows = backend.execute("SELECT * FROM orders", ())
```

## Session vs transaction scope

`SET SESSION TRANSACTION ...` changes the default for subsequent transactions;
`SET TRANSACTION ...` applies only to the *next* transaction. Prefer the latter
for per-unit overrides so a pooled or long-lived connection does not leak the
setting into unrelated work.
