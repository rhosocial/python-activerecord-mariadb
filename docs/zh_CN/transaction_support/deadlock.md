# 自动重试与死锁处理

## 概述

MariaDB 死锁是指两个或多个事务相互等待对方释放锁的情况。MariaDB InnoDB 引擎会自动检测死锁并回滚成本较低的事务，向受影响的一方返回错误代码 **1213**。本节介绍死锁处理和重试策略。

## 死锁处理策略

### 1. 使用事务重试装饰器

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
    # 转账逻辑
    pass
```

### 2. 捕获死锁错误

重试辅助函数会检查 MariaDB 死锁特征（errno 1213）：

```python
import time

def _is_deadlock(exc: Exception) -> bool:
    """检查异常是否为 MariaDB 死锁（errno 1213）。"""
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
                time.sleep(0.05 * (attempt + 1))  # 指数退避
                continue
            raise
```

## 死锁错误代码

| 错误代码 | 描述 |
|------------|-------------|
| 1213 (ER_LOCK_DEADLOCK) | 事务发生死锁；回滚并重试 |
| 1205 (ER_LOCK_WAIT_TIMEOUT) | 锁等待超时（`innodb_lock_wait_timeout`） |

## 避免死锁的建议

1. **按固定顺序访问资源**：始终按相同顺序访问表和行（例如，主键升序）
2. **尽可能使用索引**：减少被锁定的行数
3. **保持事务短小**：减少锁的持有时间
4. **在需要时使用较低的隔离级别**：适当时使用 READ COMMITTED
5. **优先使用原子认领**：在一个事务内查询并更新状态，避免读后写的竞态

## 另请参阅

- [应用场景：并行工作器](../scenarios/parallel_workers.md) — 死锁预防模式和重试示例
- [核心并行工作器模式](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN/scenarios/parallel_workers) — 通用死锁预防原则

💡 *AI 提示词：* "什么是数据库死锁？如何避免死锁？"
