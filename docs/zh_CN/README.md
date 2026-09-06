# rhosocial-activerecord MariaDB 后端文档

> **AI 学习助手**: 本文档中的关键概念以 AI 提示标注。当您遇到不理解的概念时，可以直接向 AI 助手提问。
>
> **示例:** "MariaDB 后端如何处理事务？它与 MySQL 有什么不同？"

## 目录

1. **[简介](introduction/README.md)**
    *   **[MariaDB 后端概述](introduction/README.md)**: 架构、同步/异步对等性和快速示例
    *   **[与核心库的关系](introduction/relationship.md)**: 后端如何与 rhosocial-activerecord 集成
    *   **[支持的版本](introduction/supported_versions.md)**: MariaDB、Python 和依赖版本矩阵

2. **[安装与配置](installation_and_configuration/README.md)**
    *   **[安装指南](installation_and_configuration/installation.md)**: pip 安装和驱动程序设置
    *   **[连接配置](installation_and_configuration/configuration.md)**: 主机、端口、数据库、凭据和高级选项
    *   **[SSL/TLS 配置](installation_and_configuration/ssl.md)**: 安全连接设置
    *   **[连接管理](installation_and_configuration/pool.md)**: 按需连接生命周期和异步池路线图
    *   **[字符集/编码](installation_and_configuration/charset.md)**: utf8mb4 配置和最佳实践

3. **[MariaDB 特有功能](backend_specific_features/README.md)**
    *   **[字段类型](backend_specific_features/field_types.md)**: SET、ENUM、JSON、TEXT 与 VARCHAR、YEAR
    *   **[方言表达式](backend_specific_features/dialect.md)**: MariaDB 特定的 SQL 语法和函数
    *   **[索引](backend_specific_features/indexing.md)**: 索引类型和优化策略
    *   **[EXPLAIN](backend_specific_features/explain.md)**: 查询执行计划分析
    *   **[自省](backend_specific_features/introspection.md)**: 数据库元数据查询
    *   **[分区](backend_specific_features/partition.md)**: 表分区策略

4. **[DDL 操作](ddl/README.md)**
    *   **[DDL 概述](ddl/README.md)**: CREATE TABLE、ALTER TABLE、DROP TABLE

5. **[事务支持](transaction_support/README.md)**
    *   **[隔离级别](transaction_support/isolation_level.md)**: READ COMMITTED、REPEATABLE READ 等
    *   **[保存点](transaction_support/savepoint.md)**: 嵌套事务
    *   **[死锁处理](transaction_support/deadlock.md)**: 自动检测和重试策略

6. **[类型适配器](type_adapters/README.md)**
    *   **[类型映射](type_adapters/mapping.md)**: MariaDB 到 Python 类型转换
    *   **[自定义适配器](type_adapters/custom.md)**: 扩展类型支持
    *   **[时区处理](type_adapters/timezone.md)**: UTC 和本地时区

7. **[测试](testing/README.md)**
    *   **[测试配置](testing/configuration.md)**: MariaDB 特定的测试设置
    *   **[本地测试](testing/local.md)**: 基于 Docker 的本地测试环境

8. **[故障排除](troubleshooting/README.md)**
    *   **[连接错误](troubleshooting/connection.md)**: 错误代码和诊断
    *   **[性能问题](troubleshooting/performance.md)**: 慢查询分析

9. **[应用场景](scenarios/README.md)**
    *   **[并行工作器](scenarios/parallel_workers.md)**: 多进程和异步并发模式

10. **[自定义](customization/README.md)**
    *   **[自定义表达式](customization/custom_expressions.md)**: MariaDB 特定的 SQL 扩展类
    *   **[自定义数据类型](customization/custom_types.md)**: 自定义 DataType 子类
    *   **[自定义类型适配器](customization/custom_adapters.md)**: 自定义 Python 到 MariaDB 转换器

11. **[命令行界面](cli/README.md)**
    *   **[CLI 概述](cli/README.md)**: 查询、自省和管理 MariaDB 的命令

> **核心库文档**: 完整的 ActiveRecord 框架（建模、查询、关系、性能、工作池）请参阅 [rhosocial-activerecord 文档](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN)。
