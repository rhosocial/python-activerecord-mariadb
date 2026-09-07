# DDL 特征 Spec

MariaDB 从 `SQLDialectBase` 继承核心 DDL 特征认领协议（`dialect.build_spec`）——
通用 Spec 无需任何 MariaDB 特定代码。

## 认领机制

`Model.generate_create_table(dialect)` 时，生成器把每个声明的 Spec 交给
`dialect.build_spec(spec)`：

- **接受** → 方言构造并返回表达式层实例，进入 `CreateTableExpression`；
- **不接受** → 返回 `None`，该 Spec 被静默忽略。

## 通用 Spec

全部通用 Spec 由核心默认翻译认领：

| Spec | MariaDB 翻译 |
|------|--------------|
| `CheckSpec` | `TableConstraint(CHECK)`，惰性谓词生成时求值 |
| `UniqueSpec` | `TableConstraint(UNIQUE)` |
| `NotNullSpec` | `ColumnConstraint(NOT NULL)` |
| `PrimaryKeySpec` | 单列→列级 PK / 复合→表级 PK |
| `DefaultSpec` | `ColumnConstraint(DEFAULT)`，参数化 `Literal` |
| `ForeignKeySpec` | `ForeignKeyConstraint`（含参照动作） |
| `IndexSpec` | `IndexDefinition` |
| `JsonColumnSpec` | 列类型补丁 → `JsonType` |

## 分区

MariaDB 方言声明了分区能力位，但分区 formatter 尚未实现（已知能力声明失真）；
分区 Spec 不被认领，MariaDB 特定的分区 Spec 类尚未提供。进展见[分区](partition.md)。
