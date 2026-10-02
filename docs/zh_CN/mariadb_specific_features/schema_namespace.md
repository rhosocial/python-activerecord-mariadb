# docs/zh_CN/mariadb_specific_features/schema_namespace.md

> 在 MariaDB 上 `schema_name` 指的是什么，它如何进入生成 SQL，以及哪些 MariaDB
> 专有选项附着在带限定的对象上。

与后端无关的那一半内容——命名空间从哪里来、什么时候被读取、为什么 DDL 需要自己带一个
`schema_name`——见 core 仓库的 `docs/modeling/schema_namespace.md`。本页只记录 MariaDB
与通用行为不一致的部分。

## 1. MariaDB 上的 schema 就是 database

MariaDB 没有 schema 这一层。`schema` 与 `database` 是同一个事物的两种叫法，官方文档把
两个词写在同一条语句的语法里：

```
CREATE [OR REPLACE] {DATABASE | SCHEMA} [IF NOT EXISTS] db_name
    [create_specification] ...
```

> `CREATE SCHEMA` 是 `CREATE DATABASE` 的同义词。

由此可以推出三点，三点都在真实服务器上核对过：

- `CREATE SCHEMA app` 建出来的就是名为 `app` 的数据库。MariaDB 文档没有单独的
  `CREATE SCHEMA` 页面，这条语句被记在 `CREATE DATABASE` 下。
- `SHOW DATABASES` 与 `SHOW SCHEMAS` 返回同一份列表，以 schema 方式新建的库会同时出现在
  两份列表里。
- 带 schema 限定的引用就是**跨 database** 的引用。`` `shop`.`orders` `` 读的是 `shop` 这个
  数据库里的表，而不是当前数据库内的某个 schema。

第三点是与 PostgreSQL 的全部差别所在。在 PostgreSQL 里，schema 是当前所连数据库**内部**
的命名空间：未限定名解析到哪一个由 `search_path` 决定，数据库本身由连接固定。在 MariaDB
里，连接的默认 database 承担了 PostgreSQL 中 `search_path` 的职责，而写出一个 schema
意味着指向**另一个**数据库。不存在一种连接级设置能列出多个 database 并按顺序检索。

MariaDB 方言的 `supports_schema()` 返回 `True`，并实现了 `SchemaSupport` 协议，因此
`schema_name` 会被接受并渲染出来，而不是被拒绝。这个值具体指向什么由后端定义，不由这个
标志位定义。

## 2. 在模型上读写

用 `__schema_name__` 在模型上声明命名空间：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.model import ActiveRecord

class Order(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = "app"        # 名为 "app" 的数据库
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    user_id: Optional[int] = None
```

`__table_name__` 与 `__schema_name__` 是分开的两个属性。把两者并成一个
（`__table_name__ = "app.orders"`）只会得到一个内部含点号的被引用标识符，那不是限定引用。

**DDL 不读取 `__schema_name__`。** 建表的迁移必须自己写出数据库名：

```python
CreateTableExpression(
    dialect,
    TableExpression(dialect, "orders", schema_name="app"),
    columns,
).to_sql()
# CREATE TABLE `app`.`orders` (`id` INT PRIMARY KEY)
```

`schema_name` 默认是 `None`，含义是「不限定」，与表达式层其它位置一致。

## 3. 生成 SQL 的样子

MariaDB 方言没有覆写 `format_table` 与 `format_column`，两者都继承自 core 的表达式层。
下面这些就是这种继承在本后端产生的结果。

**带限定的范围，与不带限定的范围：**

```python
TableExpression(dialect, "orders", schema_name="app").to_sql()
# `app`.`orders`

TableExpression(dialect, "orders").to_sql()
# `orders`
```

**范围未取别名时，列引用带三段：**

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT `app`.`orders`.`id` FROM `app`.`orders`
```

`FROM` 中的范围没有别名，database 就一路限定到列上。这一点要与 MySQL 后端对照：后者覆写了
`format_column`，只输出两段 `table`.`column`，完全不读 `schema_name`。MariaDB 保留了第三段：

| 后端 | `Column(dialect, "id", table="orders", schema_name="app")` 渲染为 |
|---|---|
| MariaDB | `` `app`.`orders`.`id` `` |
| MySQL | `` `orders`.`id` `` |

**一旦引入了别名，database 就从列引用中去掉**，因为别名已经标识了这个范围：

```python
# FROM `app`.`orders` AS `o`
# SELECT `o`.`id`          而不是 `app`.`orders`.`id`
```

这一步抑制发生在列表达式**构造**时，不是在渲染时。框架在 join 处强制同一条规则：join 带
了别名而连接条件仍在引用未取别名的范围，会以 `ValueError` 拒绝。

**join 可以跨 database，不需要额外配置**，两侧各自限定自己的范围：

```python
Order.query().join(
    User, on=Order.c.user_id == User.c.id
).select(Order.c.id, User.c.name).to_sql()[0]
# SELECT `app`.`orders`.`id`, `crm`.`users`.`name` FROM `app`.`orders`
#   JOIN `crm`.`users` ON `app`.`orders`.`user_id` = `crm`.`users`.`id`
```

上面四种形态——带限定的表、三段列引用、带别名的列引用、跨 database 的 join——都在真实
服务器上执行通过。

**集合操作对每个分支各自限定。** `UNION`、`INTERSECT`、`EXCEPT` 组合的是查询而不是命名某个
对象，操作本身没有可限定的东西：

```sql
SELECT `shop`.`orders`.`id` FROM `shop`.`orders`
UNION
SELECT `crm`.`users`.`id` FROM `crm`.`users`
```

**CTE 的名字不在命名空间里。** CTE 是给余下查询用的名字，不是给 database 用的，所以它
的名字永远不加限定；而它内部的查询照旧带上模型的 database：

```sql
WITH `recent` AS (SELECT `shop`.`orders`.`id` FROM `shop`.`orders`)
SELECT `*` FROM `recent`
```

## 4. `None`、`""` 与其它取值

`schema_name` 必须是 `None` 或非空字符串。校验推迟到渲染阶段才做：表达式在构造过程中只是
收集参数，要等语句渲染出来才知道它是完整的。

`None` 表示不限定。空串是一次失误，而不是「不限定」的另一种写法，因此会被拒绝：

```python
TableExpression(dialect, "orders", schema_name="").to_sql()
# ValueError: TableExpression.schema_name must be a non-empty string;
#              use None for an unqualified reference
```

构造是成功的，错误在语句渲染时抛出。同样的规则也适用于空串从模型这一侧传进来的情形：

```python
class Bad(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = ""          # 这里通过，首次渲染时报错

Bad.schema_name()                 # ''
Bad.c.id.schema_name              # ''
Bad.c.id.to_sql()                 # ValueError
```

非字符串取值以同样方式被拒绝，报错信息里会带上类型名：

```python
Column(dialect, "id", table="orders", schema_name=123).to_sql()
# ValueError: Column.schema_name must be a string or None, not int
```

这项检查在 core 方言层集中实现，而不是分散到每条语句里，因此接受 `schema_name` 的四十多个
表达式会以完全一致的方式拒绝同一批取值。

## 5. `CREATE SCHEMA` 与 `DROP SCHEMA`

两条语句都能渲染，并且各自映射到对应的 database 语句：

```python
CreateSchemaExpression(dialect, "app", if_not_exists=True).to_sql()
# CREATE SCHEMA IF NOT EXISTS `app`

DropSchemaExpression(dialect, "app", if_exists=True).to_sql()
# DROP SCHEMA IF EXISTS `app`
```

两个标准子句不可用，请求时各自抛出 `UnsupportedFeatureError`，而不是从语句里被丢弃：

| 选项 | 在 MariaDB 上的行为 |
|---|---|
| `CREATE SCHEMA IF NOT EXISTS` | 支持 |
| `DROP SCHEMA IF EXISTS` | 支持 |
| `DROP SCHEMA CASCADE` | 拒绝——MariaDB 的 `DROP SCHEMA` 没有 `CASCADE` |
| `CREATE SCHEMA AUTHORIZATION` | 拒绝——MariaDB 没有 `AUTHORIZATION` 子句 |

## 6. 触发器：三个专有选项

`MariaDBCreateTriggerExpression` 在通用 `CreateTriggerExpression` 之上增加了三个 SQL:1999
没有的属性：

| 属性 | 渲染为 | 含义 |
|---|---|---|
| `or_replace=True` | `CREATE OR REPLACE TRIGGER` | 同名触发器已存在时先删除再重建，而不是报错 |
| `ordering=("FOLLOWS" \| "PRECEDES", other_trigger)` | `FOLLOWS`/`PRECEDES other_trigger` | 把本触发器排到同表同事件另一个触发器之后或之前 |
| `body=<表达式>` | `BEGIN` 与 `END` 之间的内联语句 | 要执行的语句，而不是调用存储过程 |

这三个属性声明在 MariaDB 表达式而不是 core 表达式上，因为它们不属于任何其它方言。MySQL 的
`CREATE TRIGGER` 没有 `OR REPLACE`，Oracle 用自己的写法表达替换；`FOLLOWS`/`PRECEDES` 是
MariaDB 对「同一 timing 与 event 上可以有多个触发器」的答案，这个能力 MariaDB 有而 MySQL
没有。`body` 之所以存在，是因为 MariaDB 沿用 MySQL 的内联触发器体，而通用表达式建模的是
对存储函数的调用。格式化器若用 `getattr(expr, name, default)` 去取这三个属性，就会把「本
方言没有这个选项」变成「本语句静默丢弃了调用方要求的东西」，所以 MariaDB 格式化器读到的
每一个属性都声明在它所读取的那个表达式上。

**`schema_name` 同时限定三处**——触发器名、它绑定的表、以及它调用的函数：

```python
MariaDBCreateTriggerExpression(
    dialect, "audit_ins", "orders", TriggerTiming.BEFORE, [TriggerEvent.INSERT],
    function_name="log_order", or_replace=True,
    ordering=("FOLLOWS", "other_trg"), schema_name="app",
).to_sql()[0]
# CREATE OR REPLACE TRIGGER `app`.`audit_ins` BEFORE INSERT ON `app`.`orders`
#   FOR EACH ROW FOLLOWS `other_trg` BEGIN CALL `app`.`log_order`(); END
```

内联语句体渲染在同一位置：

```python
MariaDBCreateTriggerExpression(
    dialect, "audit_ins", "orders", TriggerTiming.BEFORE, [TriggerEvent.INSERT],
    body=RawSQLExpression(dialect, "SET NEW.n = NEW.n + 1"),
    or_replace=True, schema_name="app",
).to_sql()[0]
# CREATE OR REPLACE TRIGGER `app`.`audit_ins` BEFORE INSERT ON `app`.`orders`
#   FOR EACH ROW BEGIN SET NEW.n = NEW.n + 1 END
```

三处都加限定不是修饰。MariaDB 要求触发器与其表位于同一个 database，服务器会强制这一点：

```
CREATE TRIGGER `t` BEFORE INSERT ON `other_db`.`t1` FOR EACH ROW ...
ERROR 1435 (HY000): Trigger in wrong schema
```

只限定表、或只限定触发器名，都会得到这个错误。

`FOLLOWS` / `PRECEDES` 后面那个名字是渲染器唯一不加限定的名字，因为 MariaDB 会在触发器
所属的 database 内解析它。一个裸写的 `FOLLOWS` 引用旁边即使存在连接默认 database 中的同名
触发器，排序仍然跟随触发器所在 database 的那一个。

**版本要求。** 官方 `CREATE TRIGGER` 语法把 `{ FOLLOWS | PRECEDES } other_trigger_name`
放在 `FOR EACH ROW` 之后、语句体之前，格式化器就放在这个位置。当前的参考页面没有给出
`OR REPLACE` 与 `FOLLOWS`/`PRECEDES` 的版本号；MariaDB 发布说明把 `CREATE TRIGGER` 上的
`OR REPLACE` 记在 10.1（MDEV-7286，即统一补齐 `IF EXISTS` / `IF NOT EXISTS` / `OR REPLACE`
的那一批改动），把 `FOLLOWS`/`PRECEDES` 与同 timing/event 多触发器一起记在 10.2
（MDEV-6112）。方言把 `supports_trigger_order()` 的门槛设在 10.2.3，
`supports_or_replace_trigger()` 则无条件返回真。三个选项都在 MariaDB 13.1.1 上实际执行过；
具体最低版本以官方文档为准，不以本页为准。

在 MariaDB 上为 `False` 的能力探针，传入对应参数时都会抛出 `UnsupportedFeatureError`：

| 探针 | 原因 |
|---|---|
| `supports_trigger_if_not_exists()` | 方言引导调用方改用 `or_replace` |
| `supports_trigger_when()` | MariaDB 触发器没有 `WHEN` 条件 |
| `supports_trigger_referencing()` | 没有 `REFERENCING` 子句；直接使用 `OLD` 与 `NEW` |
| `supports_statement_trigger()` | 只有 `FOR EACH ROW` |

`FOR EACH ROW` 无条件输出；`supports_instead_of_trigger()` 从 10.4 起为真。

## 7. `ALTER TABLE ... WAIT n` / `NOWAIT`

`MariaDBAlterTableExpression` 增加了两个通用 `ALTER TABLE` 表达式没有的语句级限定符，两者
都放在带限定的表名之后、各 alter 说明之前：

```python
MariaDBAlterTableExpression(
    dialect, "orders", [RenameObject(dialect, "old_c", "new_c")],
    schema_name="app", wait=5,
).to_sql()[0]
# ALTER TABLE `app`.`orders` WAIT 5  RENAME COLUMN `old_c` TO `new_c`

MariaDBAlterTableExpression(
    dialect, "orders", [RenameObject(dialect, "old_c", "new_c")],
    schema_name="app", nowait=True,
).to_sql()[0]
# ALTER TABLE `app`.`orders` NOWAIT  RENAME COLUMN `old_c` TO `new_c`
```

（渲染器目前在限定符与第一个 alter 说明之间多输出一个空格；上面两处双空格就是它的实际
输出。）

`if_exists=True` 与两者都可组合，得到
``ALTER TABLE IF EXISTS `app`.`orders` WAIT 3  RENAME COLUMN ...``。

这两个限定符控制的是**元数据锁**的等待，与命名空间无关。两者互相正交：`schema_name` 说明
表在哪个 database，`WAIT n` / `NOWAIT` 说明在它上面等锁等多久。`WAIT 0` 等价于 `NOWAIT`。
官方语法为
`ALTER [ONLINE] [IGNORE] TABLE [IF EXISTS] tbl_name [WAIT n | NOWAIT] alter_specification ...`。

`WAIT n` / `NOWAIT` 作为「DDL Fast Fail」在 MariaDB 10.3 引入（MDEV-11379、MDEV-11388），
方言把 `supports_alter_table_wait()` 的门槛设在 10.3.0。在更旧的方言上这两个限定符会被
拒绝：

```python
MariaDBAlterTableExpression(dialect_10_2, "orders", [action], nowait=True).to_sql()
# UnsupportedFeatureError: 'MariaDB' dialect does not support ALTER TABLE
# WAIT/NOWAIT. Suggestion: WAIT/NOWAIT lock wait timeout requires MariaDB 10.3
# or later.
```

本后端的 `RENAME TABLE` 与 `TRUNCATE TABLE` 也带这两个选项。三种 `ALTER TABLE` 形态均在
MariaDB 13.1.1 上执行通过。

## 8. 读取当前 database

`rhosocial.activerecord.backend.impl.mariadb.functions.schema.current_schema`
返回未限定引用所解析到的那个命名空间：

```python
current_schema(dialect).to_sql()
# DATABASE()
```

在 MariaDB 上 `SELECT DATABASE()` 与 `SELECT SCHEMA()` 都返回当前 database——在连到
`test_db` 的会话上核对过，两者都返回 `test_db`。未选中任何 database 时 `DATABASE()` 返回
`NULL`，这也是该函数的文档里专门说明「未选中 database」这一情形、而不是假定一定有值的原因。

## 9. 常见错误

**把 schema 当成当前 database 内部的命名空间。** 在连到 `test_db` 的连接上写
`__schema_name__ = "app"`，并不是在 `test_db` 里找一个叫 `app` 的 schema，而是指向 `app`
这个 database；该 database 不存在、或账号对它没有权限时，语句会失败。

**指望有 `search_path` 式的解析。** MariaDB 没有一个按顺序检索的 database 列表。未限定名
只解析到连接的默认 database，不解析到别处。

**限定一个尚不存在的 database。** 没有任何一处在服务器端校验这个值。`schema_name` 必须是
`None` 或非空字符串，并且方言要能表达命名空间；该 database 是否存在由服务器在语句执行时
判定。

**触发器名与表只限定其中一个。** MariaDB 要求触发器与其表同库，不匹配的一对会得到错误
1435。

**用 `""` 表示「没有 database」。** 它渲染出的是一次报错，而不是一个不限定引用。请用
`None`，或者干脆不设该属性。

**把 `DROP SCHEMA ... CASCADE` 理解成「删库连同内容一起删」。** 这个子句会被拒绝。MariaDB
的 `DROP DATABASE` 本就会连库内的东西一起删除，没有可级联的对象。

**以为连接在任意服务器上都自带 TLS。** 本后端在 `ssl_disabled=True` 之外都会请求 TLS，
这正是启用了 `require_secure_transport=ON` 的服务器所需要的。不带 TLS 连接会在握手阶段
失败：

```
Connections using insecure transport are prohibited while
--require_secure_transport=ON. (errno: 3159, sqlstate: 08004)
```

在 `ssl` 之外一并传入 `tls_version` 即可固定协议版本。

## 交叉引用

core 仓库的 `docs/modeling/schema_namespace.md` 覆盖与后端无关的部分：如何声明
`__schema_name__`、限定符在什么时候被读取、为什么 DDL 需要自己的 `schema_name`，以及后端
支持矩阵。

## 这些结论的核对方式

渲染相关的结论来自 `MariaDBDialect(version=(13, 1, 1))`，验证命令为
`PYTHONPATH=src .venv3.14-ubuntu26.04/bin/python`。服务器侧行为——`SELECT DATABASE()`、
`SELECT SCHEMA()`、以 schema 新建的库同时出现在 `SHOW DATABASES` 与 `SHOW SCHEMAS`、
「生成 SQL 的样子」一节的四种查询形态、创建并执行 `CREATE OR REPLACE TRIGGER`、
`FOLLOWS` 与 `PRECEDES` 及其对 `INFORMATION_SCHEMA.TRIGGERS.ACTION_ORDER` 的影响、错误
1435 的拒绝，以及「`ALTER TABLE ... WAIT n` / `NOWAIT`」一节的三种 `ALTER TABLE`
形态——均通过 TLS 在 MariaDB 13.1.1 上实际执行。`CREATE TRIGGER`、
`CREATE DATABASE`、`ALTER TABLE` 与 `WAIT`/`NOWAIT` 的语法与版本归属，对照 MariaDB 文档
以及 10.1、10.2、10.3 的发布说明核对。
