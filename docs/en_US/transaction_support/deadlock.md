# Auto-Retry and Deadlock Handling

## Overview

A MariaDB deadlock is a situation where two or more transactions are waiting for each other to release locks. The MariaDB InnoDB engine automatically detects deadlocks and rolls back the cheaper transaction, returning error code **1213** to the affected side. This section covers deadlock handling and retry strategies.

## Deadlock Handling Strategies

### 1. Using Transaction Retry Decorator

```python
from functools import wraps
import time


def retry_on_deadlock(max_retries=3, delay=0.1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if "Deadlock" in str(e) or "1213" in str(e):
                        time.sleep(delay * (attempt + 1))
                        continue
                    raise
            raise last_exception
        return wrapper
    return decorator


@retry_on_deadlock(max_retries=3)
def transfer_money(from_account, to_account, amount):
    # Transfer logic
    pass
```

### 2. Catching Deadlock Errors

The retry helper checks for the MariaDB deadlock signature (errno 1213):

```python
import time

def _is_deadlock(exc: Exception) -> bool:
    """Check whether the exception is a MariaDB deadlock (errno 1213)."""
    msg = str(exc)
    return "1213" in msg or "deadlock" in msg.lower()


def transfer_safe(from_id: int, to_id: int, amount: float, max_retry: int = 3):
    for attempt in range(max_retry):
        try:
            with Account.transaction():
                first  = Account.find_one(min(from_id, to_id))
                second = Account.find_one(max(from_id, to_id))
                debit, credit = (first, second) if from_id < to_id else (second, first)
                debit.balance  -= amount
                credit.balance += amount
                debit.save()
                credit.save()
            return
        except Exception as e:
            if _is_deadlock(e) and attempt < max_retry - 1:
                time.sleep(0.05 * (attempt + 1))  # exponential back-off
                continue
            raise
```

## Deadlock Error Codes

| Error Code | Description |
|------------|-------------|
| 1213 (ER_LOCK_DEADLOCK) | Transaction was deadlocked; roll back and retry |
| 1205 (ER_LOCK_WAIT_TIMEOUT) | Lock wait timeout exceeded (`innodb_lock_wait_timeout`) |

## Recommendations for Avoiding Deadlocks

1. **Access resources in a fixed order**: Always access tables and rows in the same order (e.g., ascending primary key)
2. **Use indexes whenever possible**: Reduce the number of rows locked
3. **Keep transactions small**: Reduce lock duration
4. **Use lower isolation levels when needed**: Use READ COMMITTED when appropriate
5. **Prefer atomic claim**: Query and update status inside one transaction to avoid read-then-write races

## See Also

- [Scenarios: Parallel Workers](../scenarios/parallel_workers.md) — deadlock prevention patterns and retry examples
- [Core Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers) — general deadlock prevention principles

💡 *AI Prompt:* "What is a database deadlock? How can deadlocks be avoided?"
