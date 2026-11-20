<!-- docs/zh_CN/migration/README.md -->
# MariaDB 上的迁移

> **范围说明。** 本文是*后端补充文档*，不是迁移系统手册。架构、术语、排序规则、
> dry-run 抓取机制、版本记录存储、异常体系以及 `migrate` CLI 均见
> [核心库迁移章节](https://github.com/rhosocial/python-activerecord/tree/main/docs/zh_CN/migration)。
> 请先阅读该章。本文只回答一个问题：*当迁移目标是 MariaDB 时，有什么不同？*
>
> 这里的所有示例都使用本仓库提供的 `MariaDBBackend`，且需要真实的 MariaDB
> 服务器。可运行脚本汇总在
> [`docs/examples/migration/`](../../examples/migration/README.md)。

## 1. 两套 API，同一个后端

核心章节描述的两种编写路径在这里都可用：

| 路径 | 入口 | 本后端在哪里介入 |
|---|---|---|
| 函数式（推荐） | `@migration` + `run_migration_group()` | 把已连接的 `MariaDBBackend` 作为第一个参数传入 |
| 类式（兼容旧版） | `NamedMigration` + `named-migration` CLI | 后端 CLI 会自动为你构造 `MariaDBBackend` |

这张表只是*MariaDB 从何处介入*的索引，不要据此重新学习整个系统。公共组件
（`MigrationContext`、`MigrationDirection`、`MigrationRecordStore`、类型化异常）
的行为与核心章节所述完全一致。

## 2. 为迁移配置 MariaDB

一次迁移运行需要一个已连接的后端，并且其 dialect 必须知道*所连接服务器*的版本。
连接类为本仓库的 `MariaDBConnectionConfig`：

```python
import os

from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

config = MariaDBConnectionConfig(
    host=os.getenv("MARIADB_HOST", "localhost"),
    port=int(os.getenv("MARIADB_PORT", "3306")),
    database=os.getenv("MARIADB_DATABASE", "test_db"),
    username=os.getenv("MARIADB_USERNAME", "app"),
    password=os.getenv("MARIADB_PASSWORD", ""),
    charset="utf8mb4",
    autocommit=False,
)
backend = MariaDBBackend(connection_config=config)
backend.connect()
backend.introspect_and_adapt()
```

对迁移而言 `introspect_and_adapt()` 不是可选项：正是这一步让版本门禁与内省结果
针对当前服务器给出答案。类式 CLI 会在其 backend factory 中完成该调用；手写脚本
必须自行调用。完整选项（TLS、连接池、时区、`from_env()`）见
[连接配置](../../en_US/installation_and_configuration/configuration.md)。

函数式路径中，后端显式传给 `run_migration_group(backend, ...)`；类式路径中，CLI
接收连接参数（`--host`、`--port`、`--database`、`--user`、`--password`）或对应的
`MARIADB_*` 环境变量。

## 3. DDL 不支持事务 —— 关键注意事项

MariaDB 会隐式提交 `CREATE`、`ALTER`、`DROP` 以及分区维护语句。本后端如实反映
这一事实：

```python
assert backend.dialect.supports_transactional_ddl() is False
```

由此产生的迁移后果（都源自上面这一事实）：

- **DDL 无法回滚。** 把迁移包在 `backend.transaction()` 里并不会让其中的 DDL
  变得可逆。`DOWN` 迁移必须显式发出反向语句（`DROP TABLE`、`DROP INDEX` 等）——
  它是一次方向相反的正向运行，而不是回放 undo 日志。
- **可能部分生效。** 如果一条多语句迁移执行到一半失败，前面的语句已经提交。
  核心库只在成功时写入版本记录，因此该版本*不会*被标记为已应用；重试前请自行
  清理残留对象。请把每个迁移当作一个逻辑变更，并控制语句数量。
- **优先使用幂等写法。** drop 语句使用 `if_exists=True`、create 语句使用
  `IF NOT EXISTS`，可让人工恢复与重跑更安全。
- **先预览再应用。** `dry_run=True` 会渲染所有语句而不接触服务器，这是检查
  MariaDB dialect 实际会生成什么 DDL 的最低成本方式。两条抓取路径各自覆盖什么，
  见核心章节。
- **记录是唯一依据。** 由于没有事务保护，`MigrationRecordStore` 决定一个版本
  是否被视为已应用。请把它放在数据库之外，并像对待 schema 状态一样做好备份。

这与 [DDL 操作](../../en_US/ddl/README.md) 和
[事务支持](../../en_US/transaction_support/README.md) 中描述的隐式提交行为一致；迁移层
不会覆盖它。

## 4. 版本门禁与 DDL

并非每个 MariaDB 版本都接受相同的 DDL，而迁移往往正是旧版本下限暴露出来的地方。
门禁读取的是已连接 dialect 的结果，因此请先调用 `introspect_and_adapt()`：

```python
has_check = backend.dialect.supports_check_constraint()   # floor: 10.2.1
has_json_table = backend.dialect.version_at_least((10, 6, 0))
```

迁移函数可以根据 `ctx.backend.dialect` 分支选择要应用的语句；无法表达某个特性的
渲染器要么回退到等价写法（例如 JSON → `LONGTEXT`），要么抛出
`UnsupportedFeatureError`。切勿根据客户端库版本推断版本下限 —— 它是*所连接服务器*
的属性。完整的下限表与适配流程见
[版本门禁](../../en_US/mariadb_specific_features/version_gates.md)；DDL 表达式本身见
[字段类型](../../en_US/mariadb_specific_features/field_types.md) 与
[存储引擎](../../en_US/mariadb_specific_features/storage_engine.md)。

## 5. 函数式迁移

装饰器、FQN 解析、依赖校验与结果对象都属于核心章节。本后端特有的只是你传入的
后端以及它带来的 dialect：

```python
from rhosocial.activerecord.backend.migration import (
    MigrationDirection,
    run_migration_group,
)
from rhosocial.activerecord.backend.migration.record import JSONFileMigrationRecordStore

store = JSONFileMigrationRecordStore("migration_records.json")
fqn = f"{__name__}:create_users"

preview = run_migration_group(backend, [fqn], dry_run=True)
print(preview.dry_run_total, preview.dry_run_sql)

run_migration_group(backend, [fqn], record_store=store)
run_migration_group(
    backend, [fqn], direction=MigrationDirection.DOWN, record_store=store
)
```

分组在运行结束后会调用 `backend.introspector.clear_cache()`，使后续内省看到新
schema。但它无法撤销已提交的 DDL —— 这正是 `DOWN` 函数必须自行描述反向语句的
原因。完整可运行版本见
[`01_function_migration.py`](../../examples/migration/01_function_migration.py)。

## 6. 类式 `named-migration` 接线

类式 API（`NamedMigration` / `AsyncNamedMigration`、`MigrationRunner`、
`BatchMigrationRunner`）没有变化，只有 CLI 适配层是后端相关的。
`src/rhosocial/activerecord/backend/impl/mariadb/cli/named_migration.py` 向共享 CLI
辅助函数提供 `MariaDBBackend` factory，并在任何迁移运行前调用
`introspect_and_adapt()`。因此下面的命令已经绑定到 MariaDB —— 不需要
`--backend-class` / `--config-class`：

```bash
python -m rhosocial.activerecord.backend.impl.mariadb named-migration \
    rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations \
    --list
python -m rhosocial.activerecord.backend.impl.mariadb named-migration \
    rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations.V001CreateUsers \
    --host 127.0.0.1 --port 3306 --database test_db --user app \
    --direction up --dry-run
python -m rhosocial.activerecord.backend.impl.mariadb named-migration \
    rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations.migrations.V001CreateUsers \
    --host 127.0.0.1 --database test_db \
    --direction up --record-store records.json
```

上面用到的类位于
`src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/`：

| 文件 | 作用 |
|---|---|
| `migrations.py` | `NamedMigration` 子类（`v001_create_users`、`v002_create_posts`、一个带参数的） |
| `expressions.py` | 各子类执行的命名 DDL 表达式 —— 唯一构造语句对象的地方 |
| `run_basic.py`、`run_chain.py`、`run_basic_async.py` | 编程式 `MigrationRunner` 演示 |
| `demo_*.sh` | 端到端 CLI 演示（`--list`、`--describe`、`--dry-run`、UP/DOWN、`--all`、`--param`、异步） |

`--direction`、`--record-store`、`--single-transaction`、`--all` 的含义以及类式 API
本身请阅读核心章节。注意 `--single-transaction` 无法让 MariaDB 的 DDL 原子化：
它只是把一次运行编组，并不提供 `CREATE`/`ALTER`/`DROP` 的回滚。本地的 Python
对应示例是
[`02_named_migration_cli.py`](../../examples/migration/02_named_migration_cli.py)。

## 7. 本地示例

| 脚本 | 演示内容 |
|---|---|
| [`01_function_migration.py`](../../examples/migration/01_function_migration.py) | `@migration` 类方法、MariaDB 配置、版本门禁、dry run → UP → DOWN |
| [`02_named_migration_cli.py`](../../examples/migration/02_named_migration_cli.py) | MariaDB 上的类式 `MigrationRunner`，以及等价的 `named-migration` 命令 |

两者都需要真实服务器（索引中列出了环境变量）。它们在 CI 中只做 `py_compile`
语法检查，不会执行。

> 📖 关于迁移*系统*本身 —— 排序、依赖、记录、异常、dry-run 内部机制 —— 请始终
> 回到 [核心迁移章节](https://github.com/rhosocial/python-activerecord/tree/main/docs/zh_CN/migration)。
