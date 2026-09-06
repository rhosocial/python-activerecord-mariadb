# 并行工作器：最佳实践（MariaDB）

在数据处理、任务队列和批量导入等场景中，开发人员通常并行运行多个工作器以提高吞吐量。本章重点介绍 MariaDB 后端的并行工作器模式。

有关通用模式（多进程生命周期、异步行为、死锁预防原则、应用分离），请参阅[核心并行工作器模式](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers.md)。

> **本章设计原则**：同步 `BaseActiveRecord` 和异步 `AsyncBaseActiveRecord` 具有**相同的方法名**——`configure()`、`backend()`、`transaction()`、`save()` 等。异步版本只需 `await` 或 `async with`。

## 目录

1. [MariaDB 并发概述](#1-mariadb-并发概述)
2. [多进程：推荐方法](#2-多进程推荐方法)
3. [MariaDB 异步后端特性](#3-mariadb-异步后端特性)
4. [死锁：MariaDB 自动检测与预防](#4-死锁mariadb-自动检测与预防)
5. [应用分离原则](#5-应用分离原则)

---

## 1. MariaDB 并发概述

`rhosocial-activerecord` 遵循核心设计原则：**一个 ActiveRecord 类绑定一个连接**：

- **同步**：`Post.configure(config, MariaDBBackend)` → 写入 `Post.__backend__`
- **异步**：`await Post.configure(config, AsyncMariaDBBackend)` → 写入 `Post.__backend__`

`mariadb` 驱动报告 `threadsafety=1`——**单个连接不得跨线程共享**。对同一 `__backend__` 的并发访问会破坏游标状态。

| 功能 | SQLite | MariaDB |
| --- | --- | --- |
| 锁粒度 | 文件级锁 | 行级锁（InnoDB） |
| 并发写入 | 需要 WAL 模式；写入仍串行化 | 默认支持；不同行可同时写入 |
| 异步后端 | `aiosqlite`：线程池模拟，无性能提升 | `mariadb` 原生异步：网络 I/O |
| 死锁处理 | 超时等待，抛出 `OperationalError` | 自动检测，回滚成本更低的事务（errno 1213） |
| 连接类型 | 文件路径（本地） | TCP 网络连接（host:port） |

> **请勿跨线程共享 ActiveRecord 配置。多进程是并行工作器场景的正确选择。**

---

## 2. 多进程：推荐方法

每个进程都有自己独立的内存空间；`configure()` 在每个进程内独立执行，建立单独的 TCP 连接。

```python
import multiprocessing
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig
from models import Comment, Post, User

def worker(post_ids: list[int]):
    # 1. 进程启动后，在进程内部配置连接。
    #    每个进程建立自己独立的 TCP 连接。
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
            author = post.author()          # BelongsTo 关系
            approved = len([c for c in post.comments() if c.is_approved])
            post.view_count = 1 + approved
            post.save()
    finally:
        # 2. 在进程退出前断开连接
        User.backend().disconnect()

if __name__ == "__main__":
    post_ids = list(range(1, 101))
    chunk_size = 25
    with multiprocessing.Pool(processes=4) as pool:
        chunks = [post_ids[i:i+chunk_size] for i in range(0, len(post_ids), chunk_size)]
        pool.map(worker, chunks)
```

**关键规则**：

- `configure()` 必须在子进程内部调用，绝不能在任何 `fork` 之前调用
- MariaDB 连接是 TCP 连接；`fork` 后继承文件描述符比 SQLite 更危险
- 在单个进程内，协程自然串行访问数据库（事件循环单线程调度）

---

## 3. MariaDB 异步后端特性

`AsyncMariaDBBackend` 基于 `mariadb` 驱动的原生异步接口构建。每个 ActiveRecord 类绑定**一个连接**。

| 功能 | 单连接 ORM（本项目） | 连接池方法 |
| --- | --- | --- |
| 单进程内 `asyncio.gather` | ❌ 不支持——抛出 `RuntimeError` | ✅ 支持——每个协程使用不同的连接 |
| 配置复杂度 | 低——`configure()` 一行完成 | 高——手动池管理 |
| 多进程并发 | ✅ 每进程独立连接 | ✅ 也支持 |
| 最佳用途 | 批量处理、任务队列、数据管道 | 高并发 Web 服务 |

> **异步单连接限制**：同一进程内的协程必须**串行**执行。通过 `asyncio.gather` 尝试并发访问会抛出：
> ```
> RuntimeError: read() called while another coroutine is already waiting for incoming data
> ```
> 应在**多进程**层面实现并发——每个进程持有自己独立的连接。

---

## 4. 死锁：MariaDB 自动检测与预防

MariaDB InnoDB 内置死锁检测算法。检测到死锁时，会自动回滚成本较低的事务。被回滚的一方收到 `OperationalError`（errno 1213）。

### 4.1 根本原因：行锁顺序不一致

```python
# ❌ 错误：不同工作器以相反顺序锁定行
def worker_a():
    with Post.transaction():
        post1 = Post.find_one(1)  # 先锁定 id=1
        time.sleep(0.01)
        post2 = Post.find_one(2)  # 请求 id=2（B 已持有）

def worker_b():
    with Post.transaction():
        post2 = Post.find_one(2)  # 先锁定 id=2
        time.sleep(0.01)
        post1 = Post.find_one(1)  # 请求 id=1（A 已持有）
```

### 4.2 预防：一致的锁顺序 + 原子认领

```python
# ✅ 正确：始终按主键升序锁定资源
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
# ✅ 正确：事务内原子认领；行级锁防止重复
def claim_posts(batch_size: int = 5) -> list:
    with Post.transaction():
        pending = (
            Post.query()
                .where(Post.c.status == "draft")
                .order_by(Post.c.id)
                .limit(batch_size)
                .for_update()  # MariaDB 支持 FOR UPDATE
                .all()
        )
        if not pending:
            return []
        for post in pending:
            post.status = "processing"
            post.save()
        return pending
```

### 4.3 捕获死锁并重试（生产环境推荐）

```python
import time

def _is_deadlock(exc: Exception) -> bool:
    """检查异常是否为 MariaDB 死锁（errno 1213）。"""
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
                time.sleep(0.05 * (attempt + 1))  # 指数退避
                continue
            raise
    return []
```

### 4.4 五项预防原则

| 原则 | 描述 |
| --- | --- |
| **数据分区** | 通过 ID 范围或哈希将数据分配给每个工作器，使其永远不会触及相同的行 |
| **一致的锁顺序** | 锁定多个资源时，始终按固定顺序请求（例如，主键升序） |
| **短事务** | 事务中只保留必要的操作；避免在内部进行 I/O 等待或昂贵的计算 |
| **原子认领** | 在一个事务内查询并更新任务状态，绝不要分开读后写 |
| **死锁重试** | 捕获 `OperationalError`（errno 1213）并重试；无需依赖锁顺序 |

> **MariaDB 调优**：`innodb_lock_wait_timeout`（默认 50 秒）控制行锁等待时间；`innodb_deadlock_detect`（默认启用）控制自动死锁检测。

---

## 5. 应用分离原则

当系统包含两种非常不同类型的工作负载时，将它们部署为独立的应用程序。

| 工作负载类型 | 特点 | 合适的部署 |
| --- | --- | --- |
| Web API 服务 | 短请求、高并发、对延迟敏感 | FastAPI / Django + asyncio + 连接池 |
| 数据分析批处理 | 长运行、大数据集、CPU 密集 | 独立脚本 + multiprocessing + MariaDBBackend |
| 任务队列消费者 | 周期性轮询、独立任务、水平扩展 | Celery + MariaDB 或自定义 + multiprocessing |

## 另请参阅

- [事务支持：死锁](../transaction_support/deadlock.md) — 错误代码和重试辅助函数
- [核心并行工作器模式](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers.md) — 通用原则

💡 *AI 提示词：* "为什么 MariaDB 的 `mariadb` 驱动程序不是线程安全的，多进程如何解决这个问题？"
