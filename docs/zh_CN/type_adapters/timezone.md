# 时区处理

## 概述

MariaDB 后端保持数据库返回的原始形式，不进行额外的时区转换。

## DATETIME 和 TIMESTAMP 的区别

MariaDB 有两种日期/时间类型：

- **DATETIME**：存储不带时区信息的日期/时间，类似于"日历时间"
- **TIMESTAMP**：存储 UTC 时间戳；MariaDB 会自动在会话时区和 UTC 之间进行转换

```sql
-- 使用特定类型创建表
CREATE TABLE events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255),
    created_at DATETIME,      -- 无时区
    updated_at TIMESTAMP      -- 有时区，自动转换
);
```

## MariaDB 服务器时区

MariaDB 服务器的时区设置会影响 TIMESTAMP 类型的存储和检索方式：

```sql
-- 查看当前时区设置
SHOW VARIABLES LIKE 'time_zone';

-- 设置会话时区
SET time_zone = '+08:00';
```

## Python 端处理

建议在 Python 端使用 UTC 或本地时区：

```python
from datetime import datetime, timezone, timedelta


def to_utc(dt: datetime) -> datetime:
    """转换为 UTC 时间"""
    if dt.tzinfo is None:
        # 假设为本地时区
        local_tz = datetime.now().astimezone().tzinfo
        dt = dt.replace(tzinfo=local_tz)
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """转换为本地时间"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_tz = datetime.now().astimezone().tzinfo
    return dt.astimezone(local_tz)
```

## 最佳实践

1. **以 UTC 存储**：建议在数据库中以 UTC 时间存储
2. **在前端转换**：在应用层或前端进行时区转换
3. **避免混用**：不要在同一个系统中混用不同时区的时间

```python
from datetime import datetime, timezone


class Event(ActiveRecord):
    name: str
    created_at: datetime

    @property
    def created_at_utc(self) -> datetime:
        if self.created_at.tzinfo is None:
            return self.created_at.replace(tzinfo=timezone.utc)
        return self.created_at.astimezone(timezone.utc)
```

## 另请参阅

- [类型映射](mapping.md) — DATETIME / TIMESTAMP 类型映射

💡 *AI 提示词：* "为什么建议以 UTC 而不是本地时区存储时间？"
