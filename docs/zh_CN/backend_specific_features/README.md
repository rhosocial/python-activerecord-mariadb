# MariaDB 特有功能

本节介绍与其他后端不同的 MariaDB 特有功能。rhosocial-activerecord 对许多功能使用两层架构：**核心层**提供通用接口和默认实现，而每个后端的**方言层**覆盖格式化并添加后端特定功能。

当您遇到本节中的功能时，请检查它是后端特定的扩展还是具有后端特定格式化的核心功能 -- 文档将指示适用的层。

## 内容

- [方言表达式](dialect.md)：两层表达式系统 -- 通用核心和 MariaDB 特定覆盖
- [字段类型](field_types.md)：核心 DataType 层次结构和 MariaDB 特定类型扩展
- [索引](indexing.md)：MariaDB 特定的索引类型和优化策略
- [EXPLAIN](explain.md)：查询执行计划分析（MariaDB 特定语法）
- [自省](introspection.md)：数据库元数据查询和模式检查
- [分区](partition.md)：表分区（MariaDB 特定）

## 功能亮点

| 功能 | 通用层 | MariaDB 特定层 |
|------|--------|---------------|
| 表达式 | 核心表达式类（Column、Literal、FunctionCall 等） | 方言覆盖和 MariaDB 特定表达式类 |
| 类型系统 | 核心 DataType 层次结构（IntegerType、VarCharType 等） | MariaDB 特定 DataType 子类和类型适配器 |
| EXPLAIN | ExplainExpression 接口 | MariaDB 特定 EXPLAIN 语法和结果解析 |
| 自省 | Introspector 接口 | MariaDB 特定元数据查询（SHOW 命令） |

## MariaDB 特定协议

MariaDB 后端定义了自己的协议接口，用于 MariaDB 独有的功能：

| 协议 | 描述 |
|------|------|
| `MariaDBDMLOperationSupport` | INSERT IGNORE、REPLACE INTO、LOAD DATA |
| `MariaDBTriggerSupport` | 触发器 DDL（BEFORE/AFTER、INSTEAD OF） |
| `MariaDBTableSupport` | MariaDB 表 DDL 选项 |
| `MariaDBSetTypeSupport` | SET 数据类型支持 |
| `MariaDBJSONFunctionSupport` | JSON 函数支持 |
| `MariaDBSpatialSupport` | 空间数据类型和函数 |
| `MariaDBFullTextSearchSupport` | 全文搜索 MATCH AGAINST |
| `MariaDBLockingSupport` | FOR UPDATE、FOR SHARE、SKIP LOCKED |
| `MariaDBModifyColumnSupport` | MODIFY/CHANGE COLUMN 支持 |
| `MariaDBSequenceSupport` | SEQUENCE 对象（10.3+） |
| `MariaDBReturningSupport` | RETURNING 子句（10.5+，仅 INSERT/DELETE） |
| `MariaDBIntersectExceptSupport` | INTERSECT/EXCEPT（10.3+） |
| `MariaDBSystemVersioningSupport` | 系统版本化表（10.3+） |
| `MariaDBWindowFunctionSupport` | 窗口函数（10.2+） |
| `MariaDBCTESupport` | 公共表表达式（10.2+） |
| `MariaDBPartitionSupport` | 表分区 |

## 相关主题

- [类型适配器](../type_adapters/README.md) -- 类型映射和自定义适配器
- [DDL 操作](../ddl/README.md) -- 模式管理
- [核心：表达式系统](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/expression)
- [核心：后端系统](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend)
