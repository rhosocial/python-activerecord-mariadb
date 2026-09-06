# 测试配置

## 概述

本节介绍如何配置 MariaDB 后端的测试环境。

有关通用测试策略（DummyBackend、SQLite 集成测试），请参阅[核心后端测试指南](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/testing/backend_testing.md)。

## 使用 MariaDB 后端进行端到端测试

如需完整的 MariaDB 行为测试，请使用 MariaDB 后端：

```python
import os
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig


class User(ActiveRecord):
    name: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'


# 从环境变量读取配置
config = MariaDBConnectionConfig(
    host=os.environ.get('MARIADB_HOST', 'localhost'),
    port=int(os.environ.get('MARIADB_PORT', 3306)),
    database=os.environ.get('MARIADB_DATABASE', 'test'),
    username=os.environ.get('MARIADB_USERNAME', 'root'),
    password=os.environ.get('MARIADB_PASSWORD', ''),
)
User.configure(config, MariaDBBackend)
```

## 测试夹具

```python
import pytest
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend, MariaDBConnectionConfig


@pytest.fixture
def mariadb_config():
    return MariaDBConnectionConfig(
        host='localhost',
        port=3306,
        database='test',
        username='root',
        password='password',
    )


@pytest.fixture
def mariadb_backend(mariadb_config):
    backend = MariaDBBackend(connection_config=mariadb_config)
    backend.connect()
    yield backend
    backend.disconnect()


def test_connection(mariadb_backend):
    version = mariadb_backend.get_server_version()
    assert version is not None
```

## 环境变量

| 变量 | 默认值 | 描述 |
|----------|---------|-------------|
| `MARIADB_HOST` | `localhost` | 服务器主机 |
| `MARIADB_PORT` | `3306` | 服务器端口 |
| `MARIADB_DATABASE` | `test` | 数据库名 |
| `MARIADB_USERNAME` | `root` | 用户名 |
| `MARIADB_PASSWORD` | `` | 密码 |

💡 *AI 提示词：* "单元测试、集成测试和端到端测试之间有什么区别？"
