# Transaction Isolation Levels

## Overview

MariaDB supports multiple transaction isolation levels, and different isolation levels determine the visibility between concurrent transactions.

## Isolation Level Comparison

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read |
|-----------------|------------|---------------------|--------------|
| READ UNCOMMITTED | Possible | Possible | Possible |
| READ COMMITTED | Impossible | Possible | Possible |
| REPEATABLE READ (Default) | Impossible | Impossible | Possible |
| SERIALIZABLE | Impossible | Impossible | Impossible |

> **Note**: MariaDB's default isolation level is `REPEATABLE READ`. For InnoDB, `REPEATABLE READ` uses MVCC with a consistent snapshot, effectively preventing phantom reads in most cases.

## Setting Isolation Level

You can set the isolation level on the transaction manager:

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig
from rhosocial.activerecord.backend.transaction import IsolationLevel

config = MariaDBConnectionConfig(
    host='localhost',
    database='myapp',
    username='user',
    password='password',
)

backend = MariaDBBackend(connection_config=config)
backend.connect()

with backend.transaction() as txn:
    # Set isolation level for this transaction
    txn.isolation_level = IsolationLevel.READ_COMMITTED
    # ... transaction operations ...

backend.disconnect()
```

The transaction manager validates the isolation level and rejects unsupported values, and refuses to change the level while a transaction is already active.

## Isolation Level Details

### READ UNCOMMITTED

Each read fetches data without checking for uncommitted changes; dirty reads are possible:

```sql
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
```

Suitable only for scenarios where approximate data is acceptable.

### READ COMMITTED

Each read fetches only committed data:

```sql
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

Suitable for most application scenarios, balancing concurrency and data consistency.

### REPEATABLE READ (Default)

Multiple reads of the same data within a transaction return consistent results:

```sql
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
```

MariaDB's default isolation level, implemented using MVCC mechanism.

### SERIALIZABLE

The highest isolation level, enforces sequential transaction execution:

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

Suitable for scenarios requiring extreme data consistency, but with poorer concurrency performance.

## Supported Values

The `IsolationLevel` enum exposes: `READ_UNCOMMITTED`, `READ_COMMITTED`, `REPEATABLE_READ`, `SERIALIZABLE`.

💡 *AI Prompt:* "What are dirty reads, non-repeatable reads, and phantom reads?"
