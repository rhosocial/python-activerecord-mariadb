# 与核心库的关系

## 架构概述

rhosocial-activerecord 采用模块化设计：核心库（`rhosocial-activerecord`）提供与数据库无关的 ActiveRecord 实现，而数据库后端作为独立的扩展包存在。

MariaDB 后端的命名空间位于 `rhosocial.activerecord.backend.impl.mariadb` 下，与其他后端（如 `sqlite`、`mysql`、`dummy`）处于同一层级。这意味着：

- 后端不参与 ActiveRecord 层的变更
- 后端严格遵守后端接口协议
- 后端更新与核心库的 ActiveRecord 功能解耦

```
rhosocial.activerecord
├── backend.impl.sqlite    # SQLite 后端
├── backend.impl.mysql     # MySQL 后端
├── backend.impl.dummy     # Dummy 后端（用于测试）
└── backend.impl.mariadb   # MariaDB 后端（本包）
    ├── MariaDBBackend
    ├── AsyncMariaDBBackend
    └── ...
```

## 后端职责

MariaDB 后端负责以下内容：

### 1. SQL 方言生成

将通用查询构建器转换为 MariaDB 特定的 SQL 语句（使用反引号引用）：

```python
# 核心库：通用查询构建
query = User.query().where(User.c.age >= 18).order_by(User.c.created_at)

# MariaDB 后端：转换为 MariaDB SQL
# SELECT * FROM `users` WHERE `age` >= 18 ORDER BY `created_at`
```

### 2. 数据类型映射

处理 MariaDB 特定的数据类型，包括：

- TINYINT、SMALLINT、MEDIUMINT、INT、BIGINT
- FLOAT、DOUBLE、DECIMAL
- CHAR、VARCHAR、TEXT、TINYTEXT、MEDIUMTEXT、LONGTEXT
- DATE、TIME、DATETIME、TIMESTAMP、YEAR
- BINARY、VARBINARY、BLOB
- JSON（MariaDB 10.2.3+）
- ENUM、SET

### 3. 连接管理

提供 MariaDB 连接的建立、断开及其他底层操作。

### 4. 事务控制

实现 MariaDB 事务的 BEGIN、COMMIT、ROLLBACK 逻辑，包括保存点和隔离级别。

## 快速入门

### 1. 安装

```bash
pip install rhosocial-activerecord
pip install rhosocial-activerecord-mariadb
```

### 2. 定义模型

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin


class User(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

### 3. 配置后端

```python
from rhosocial.activerecord.backend.impl.mariadb import (
    MariaDBBackend,
    MariaDBConnectionConfig,
)

# 配置 MariaDB 连接
config = MariaDBConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
)

# 为模型配置后端
User.configure(config, MariaDBBackend)
```

### 4. CRUD 操作

```python
# 创建
user = User(username='tom', email='tom@example.com')
user.save()

# 读取
user = User.query().where(User.c.username == 'tom').one()

# 更新
user.email = 'tom.new@example.com'
user.save()

# 删除
user.delete()
```

💡 *AI 提示词：* "什么是 ActiveRecord 模式？它的优点和缺点是什么？"
