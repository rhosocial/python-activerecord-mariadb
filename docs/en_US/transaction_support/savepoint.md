# Savepoint Support

## Overview

Savepoints allow creating intermediate checkpoints within a transaction, enabling partial rollbacks without aborting the whole transaction.

MariaDB has supported savepoints since early versions, so the MariaDB backend's `supports_savepoint()` always returns `True`.

## Using Savepoints

The transaction manager exposes nested savepoints automatically. You can also create and roll back to named savepoints explicitly:

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host='localhost',
    database='myapp',
    username='user',
    password='password',
)

backend = MariaDBBackend(connection_config=config)
backend.connect()

try:
    with backend.transaction() as txn:
        # Operation 1
        User(name='Alice').save()

        # Create savepoint
        txn.create_savepoint('sp1')

        try:
            # Operation 2 (may fail)
            User(name='Bob').save()
            txn.release_savepoint('sp1')
        except Exception:
            # Rollback to savepoint, keeping operation 1
            txn.rollback_to_savepoint('sp1')
finally:
    backend.disconnect()
```

## Nested Transactions

The backend auto-generates savepoint names for nested transactions:

```python
with User.transaction() as outer:
    user = User(name='alice')
    user.save()

    with User.transaction() as inner:  # creates a nested savepoint
        user.email = 'alice@example.com'
        user.save()
        # inner raises → rollback to savepoint, outer remains valid
```

When an inner `with User.transaction()` block fails, the backend rolls back to the auto-generated savepoint name (e.g., `SAVEPOINT sp1`) instead of aborting the outer transaction.

## Sync/Async Parity

The async transaction manager (`AsyncMariaDBTransactionManager`) exposes the same methods with `await`:

```python
async with AsyncUser.transaction() as txn:
    await AsyncUser(name='Alice').save()
    await txn.create_savepoint('sp1')
    # ...
    await txn.rollback_to_savepoint('sp1')
```

## See Also

- [Core Transaction Documentation](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/transaction) — transaction manager API

💡 *AI Prompt:* "What is a database savepoint? How does it differ from a full rollback?"
