# rhosocial-activerecord MariaDB 后端文档

MariaDB 后端是 [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord)
的 MariaDB 后端实现。它使用 `mariadb` 驱动，在 MySQL 后端之上补充了 MariaDB 专有行为，
包括 `CREATE TRIGGER` 的 `OR REPLACE`、触发器的 `FOLLOWS` / `PRECEDES` 顺序控制，
以及 `ALTER TABLE` 的 `WAIT` / `NOWAIT`。

## 目录 (Table of Contents)

- **[Schema 命名空间](mariadb_specific_features/schema_namespace.md)**：声明
  `__schema_name__`、`schema` 实为 database 另一种叫法、三段式列引用、
  触发器所属 schema，以及 `ALTER TABLE ... WAIT`

## 关键结论速览

| 问题 | 结论 |
|---|---|
| `schema_name` 指什么？ | database；`CREATE SCHEMA` 是 `CREATE DATABASE` 的同义词 |
| 限定表渲染为 | `` `app`.`orders` `` |
| 列引用 | 未取别名的范围为三段：`` `app`.`orders`.`id` `` |
| 取别名之后 | `` `o`.`id` `` |
| 当前 schema | `SELECT DATABASE()` 或 `SELECT SCHEMA()` |
| `CREATE SCHEMA` / `DROP SCHEMA` | 支持 |
| 触发器 | `OR REPLACE`、`FOLLOWS`、`PRECEDES` |

## 相关文档

- **[Schema 命名空间（核心库指南）](https://github.com/rhosocial/python-activerecord/tree/docs/docs/modeling/schema_namespace.md)**：
  所有后端共同遵循的、与方言无关的规则

---

> ⚠️ **依赖说明**：本后端依赖核心库 `rhosocial-activerecord`，请与核心库一并安装，
> 不要单独安装本后端。