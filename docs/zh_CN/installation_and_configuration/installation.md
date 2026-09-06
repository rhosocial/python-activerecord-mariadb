# 安装指南

## 系统要求

- Python 3.8+
- MariaDB 10.2+（推荐 MariaDB 10.5+ 以获得完整功能支持）
- pip 或 poetry

## 安装步骤

### 1. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

### 2. 安装核心库和 MariaDB 后端

```bash
# 安装核心库
pip install rhosocial-activerecord

# 安装 MariaDB 后端
pip install rhosocial-activerecord-mariadb
```

### 3. 安装 MariaDB 驱动

此后端使用 `mariadb` Python 包（v2.0.0+）同时支持同步和异步：

```bash
pip install mariadb>=2.0.0
```

`mariadb` 包提供：
- 通过 `mariadb.connect()` 的同步连接
- 通过 `mariadb.asyncConnect()` 的异步连接（v2.0.0+）

**注意**：异步驱动是同一包 -- 不需要单独的异步包。

## 验证安装

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

backend = MariaDBBackend(
    host='localhost',
    port=3306,
    database='test_db',
    username='root',
    password='password'
)
backend.connect()
print(f"MariaDB 版本: {backend.get_server_version()}")
backend.disconnect()
```

## 版本特定功能

MariaDB 后端会根据服务器版本进行适配。关键功能边界：

| 功能 | 最低版本 |
|------|---------|
| 窗口函数 | 10.2 |
| CTE | 10.2 |
| JSON 函数 | 10.2.3 |
| JSON 箭头运算符 | 10.2.7 |
| INTERSECT/EXCEPT | 10.3 |
| SEQUENCE | 10.3 |
| 系统版本化表 | 10.3 |
| SKIP LOCKED | 10.3 |
| RETURNING 子句 | 10.5 |
| EXPLAIN FORMAT/ANALYZE | 10.6 |

方言通过 `introspect_and_adapt()` 自动检测服务器版本，并相应调整功能可用性。

AI Prompt: "生产环境应该使用哪个 MariaDB 版本？"
