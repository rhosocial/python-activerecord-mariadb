# Parallel Workers: Best Practices (MariaDB)

In data processing, task queues, and bulk import scenarios, developers often run multiple workers in parallel to improve throughput. This chapter focuses on parallel worker patterns for the MariaDB backend.

For general patterns (multi-process lifecycle, async behavior, deadlock prevention principles, application separation), see [Core Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers.md).

> **Design principle throughout this chapter**: The synchronous `BaseActiveRecord` and asynchronous `AsyncBaseActiveRecord` have **identical method names** — `configure()`, `backend()`, `transaction()`, `save()`, and so on. The async version simply requires `await` or `async with`.

## Table of Contents

1. [MariaDB Concurrency Overview](#1-mariadb-concurrency-overview)
2. [Multi-process: The Recommended Approach](#2-multi-process-the-recommended-approach)
3. [MariaDB Async Backend Characteristics](#3-mariadb-async-backend-characteristics)
4. [Deadlocks: MariaDB Auto-detection and Prevention](#4-deadlocks-mariadb-auto-detection-and-prevention)
5. [Application Separation Principle](#5-application-separation-principle)

---

## 1. MariaDB Concurrency Overview

`rhosocial-activerecord` follows the core design principle of **one ActiveRecord class bound to one connection**:

- **Sync**: `Post.configure(config, MariaDBBackend)` → writes to `Post.__backend__`
- **Async**: `await Post.configure(config, AsyncMariaDBBackend)` → writes to `Post.__backend__`

The `mariadb` driver reports `threadsafety=1` — **a single connection must not be shared across threads**. Concurrent access to the same `__backend__` corrupts cursor state.

| Feature | SQLite | MariaDB |
| --- | --- | --- |
| Lock granularity | File-level lock | Row-level lock (InnoDB) |
| Concurrent writes | Requires WAL mode; writes still serialized | Supported by default; different rows write simultaneously |
| Async backend | `aiosqlite`: thread-pool simulation, no performance gain | `mariadb` native async: network I/O |
| Deadlock handling | Timeout wait, raises `OperationalError` | Auto-detection, rolls back the cheaper transaction (errno 1213) |
| Connection type | File path (local) | TCP network connection (host:port) |

> **Do not share an ActiveRecord configuration across multiple threads. Multi-process is the correct choice for parallel worker scenarios.**

---

## 2. Multi-process: The Recommended Approach

Each process has its own isolated memory space; `configure()` executes independently within each process, establishing a separate TCP connection.

```python
import multiprocessing
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig
from models import Comment, Post, User

def worker(post_ids: list[int]):
    # 1. After the process starts, configure the connection inside the process.
    #    Each process establishes its own independent TCP connection.
    config = MariaDBConnectionConfig(
        host="localhost", port=3306,
        database="mydb", username="app", password="secret",
        charset="utf8mb4", autocommit=True,
    )
    User.configure(config, MariaDBBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    try:
        for post_id in post_ids:
            post = Post.find_one(post_id)
            if post is None:
                continue
            author = post.author()          # BelongsTo relation
            approved = len([c for c in post.comments() if c.is_approved])
            post.view_count = 1 + approved
            post.save()
    finally:
        # 2. Disconnect before the process exits
        User.backend().disconnect()

if __name__ == "__main__":
    post_ids = list(range(1, 101))
    chunk_size = 25
    with multiprocessing.Pool(processes=4) as pool:
        chunks = [post_ids[i:i+chunk_size] for i in range(0, len(post_ids), chunk_size)]
        pool.map(worker, chunks)
```

**Key rules**:

- `configure()` must be called inside the child process, never before `fork`
- MariaDB connections are TCP connections; inheriting file descriptors after `fork` is more dangerous than with SQLite
- Within a single process, coroutines naturally access the database serially (event loop single-threaded scheduling)

---

## 3. MariaDB Async Backend Characteristics

`AsyncMariaDBBackend` is built on the `mariadb` driver's native async interface. Each ActiveRecord class is bound to **one connection**.

| Feature | Single-connection ORM (this project) | Connection pool approach |
| --- | --- | --- |
| `asyncio.gather` in one process | ❌ Not supported — raises `RuntimeError` | ✅ Supported — each coroutine uses a different connection |
| Configuration complexity | Low — `configure()` in one line | High — manual pool management |
| Multi-process concurrency | ✅ Independent connection per process | ✅ Also supported |
| Best use case | Batch processing, task queues, data pipelines | High-concurrency web services |

> **Async single-connection limitation**: Coroutines within the same process must execute **sequentially**. Attempting concurrent access via `asyncio.gather` raises:
> ```
> RuntimeError: read() called while another coroutine is already waiting for incoming data
> ```
> Achieve concurrency at the **multi-process** level — each process holds its own independent connection.

---

## 4. Deadlocks: MariaDB Auto-detection and Prevention

MariaDB InnoDB has a built-in deadlock detection algorithm. When a deadlock is detected, it automatically rolls back the transaction with lower cost. The rolled-back side receives an `OperationalError` (errno 1213).

### 4.1 Root Cause: Inconsistent Row Lock Order

```python
# ❌ Wrong: Different workers lock rows in opposite order
def worker_a():
    with Post.transaction():
        post1 = Post.find_one(1)  # locks id=1 first
        time.sleep(0.01)
        post2 = Post.find_one(2)  # requests id=2 (B already holds it)

def worker_b():
    with Post.transaction():
        post2 = Post.find_one(2)  # locks id=2 first
        time.sleep(0.01)
        post1 = Post.find_one(1)  # requests id=1 (A already holds it)
```

### 4.2 Prevention: Consistent Lock Order + Atomic Claim

```python
# ✅ Correct: Always lock resources in ascending primary key order
def transfer_safe(from_id: int, to_id: int, amount: float):
    first_id, second_id = min(from_id, to_id), max(from_id, to_id)
    with Account.transaction():
        first  = Account.find_one(first_id)
        second = Account.find_one(second_id)
        debit, credit = (first, second) if from_id < to_id else (second, first)
        debit.balance  -= amount
        credit.balance += amount
        debit.save()
        credit.save()
```

```python
# ✅ Correct: Atomic claim inside a transaction; row-level locking prevents duplicates
def claim_posts(batch_size: int = 5) -> list:
    with Post.transaction():
        pending = (
            Post.query()
                .where(Post.c.status == "draft")
                .order_by(Post.c.id)
                .limit(batch_size)
                .for_update()  # MariaDB supports FOR UPDATE
                .all()
        )
        if not pending:
            return []
        for post in pending:
            post.status = "processing"
            post.save()
        return pending
```

### 4.3 Catch Deadlock and Retry (Recommended for Production)

```python
import time

def _is_deadlock(exc: Exception) -> bool:
    """Check whether the exception is a MariaDB deadlock (errno 1213)."""
    msg = str(exc)
    return "1213" in msg or "deadlock" in msg.lower()

def claim_posts_with_retry(batch_size: int = 5, max_retry: int = 3) -> list:
    for attempt in range(max_retry):
        try:
            with Post.transaction():
                pending = (
                    Post.query()
                        .where(Post.c.status == "draft")
                        .order_by(Post.c.id)
                        .limit(batch_size)
                        .all()
                )
                if not pending:
                    return []
                for post in pending:
                    post.status = "processing"
                    post.save()
                return pending
        except Exception as e:
            if _is_deadlock(e) and attempt < max_retry - 1:
                time.sleep(0.05 * (attempt + 1))  # exponential back-off
                continue
            raise
    return []
```

### 4.4 Five Prevention Principles

| Principle | Description |
| --- | --- |
| **Data partitioning** | Assign data by ID range or hash to each worker so they never touch the same rows |
| **Consistent lock order** | When locking multiple resources, always request them in a fixed order (e.g., ascending primary key) |
| **Short transactions** | Keep only necessary operations in a transaction; avoid I/O waits or expensive computations inside |
| **Atomic claim** | Query and update task status inside one transaction, never read-then-write separately |
| **Deadlock retry** | Catch `OperationalError` (errno 1213) and retry; no need to rely on lock ordering |

> **MariaDB tuning**: `innodb_lock_wait_timeout` (default 50 s) controls row-lock wait time; `innodb_deadlock_detect` (default enabled) controls automatic deadlock detection.

---

## 5. Application Separation Principle

When a system contains two very different kinds of workloads, deploy them as separate applications.

| Workload type | Characteristics | Suitable deployment |
| --- | --- | --- |
| Web API service | Short requests, high concurrency, latency-sensitive | FastAPI / Django + asyncio + connection pools |
| Data analytics batch | Long-running, large datasets, CPU-intensive | Standalone script + multiprocessing + MariaDBBackend |
| Task queue consumer | Periodic polling, independent tasks, horizontally scalable | Celery + MariaDB or custom + multiprocessing |

## See Also

- [Transaction Support: Deadlock](../transaction_support/deadlock.md) — error codes and retry helpers
- [Core Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers.md) — general principles

💡 *AI Prompt:* "Why is the MariaDB `mariadb` driver not thread-safe, and how does multi-processing solve this?"
