# DDL Operations

## Overview

This section covers DDL (Data Definition Language) operations for the MariaDB backend. DDL defines your database schema -- tables, indexes, views, and other objects.

**Important**: All DDL in rhosocial-activerecord is **expression-based**. You define your schema in Python, the framework generates the SQL, and you execute it via the backend. The examples below use `ActiveRecord` for brevity, but `AsyncActiveRecord` works identically -- the DDL generation is pure computation with no I/O involved.

The DDL chapter is divided into two parts:

1. **Backend DDL Capabilities** -- The complete set of DDL operations the MariaDB backend supports, expressed through backend-specific expression classes. This is the backend's full power.
2. **ActiveRecord DDL Derivation** -- What the framework can automatically generate from model class declarations. This is a convenient subset that covers most common use cases.

---

# Part 1: Backend DDL Capabilities

The MariaDB backend supports the following DDL operations. Each operation is expressed through a corresponding expression class -- you construct the expression, then execute it via the backend.

## Supported Operations

| Operation | MariaDB Support | Expression Class |
|-----------|----------------|-----------------|
| CREATE TABLE | Yes | `CreateTableExpression` |
| ALTER TABLE | Yes | `AlterTableExpression` |
| DROP TABLE | Yes | `DropTableExpression` |
| CREATE INDEX | Yes | `CreateIndexExpression` |
| DROP INDEX | Yes | `DropIndexExpression` |
| CREATE VIEW | Yes | `CreateViewExpression` |
| DROP VIEW | Yes | `DropViewExpression` |
| TRUNCATE | Yes | `TruncateExpression` |

## CREATE TABLE

### IF NOT EXISTS

MariaDB supports `CREATE TABLE IF NOT EXISTS`.

### Temporary Tables

MariaDB supports `CREATE TEMPORARY TABLE`.

### Engine and Charset Options

MariaDB supports table options like `ENGINE`, `DEFAULT CHARSET`, `COLLATE`, and `COMMENT`:

```sql
CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User accounts table'
```

## ALTER TABLE

### Adding Columns

| Feature | MariaDB Support |
|---------|----------------|
| ADD COLUMN | Yes |
| ADD COLUMN IF NOT EXISTS | Yes (syntax varies) |

### Dropping Columns

| Feature | MariaDB Support |
|---------|----------------|
| DROP COLUMN | Yes |
| DROP COLUMN IF EXISTS | Yes |

### Renaming Columns

MariaDB supports `RENAME COLUMN` (10.5+) and `CHANGE COLUMN` (all versions).

### Changing Column Types

MariaDB uses `MODIFY COLUMN` to change column types in place:

```sql
ALTER TABLE users MODIFY COLUMN age SMALLINT NOT NULL;
```

## DROP TABLE

| Feature | MariaDB Support |
|---------|----------------|
| IF EXISTS | Yes |
| CASCADE/RESTRICT | Parsed but ignored |

## CREATE INDEX

### Index Types

| Index Type | MariaDB Support |
|-----------|----------------|
| BTREE | Yes |
| HASH | Yes |
| FULLTEXT | Yes |
| SPATIAL | Yes |

### Functional Indexes

MariaDB supports functional indexes (expression indexes).

### Full-Text Indexes

MariaDB supports `FULLTEXT INDEX` on InnoDB tables (since 10.2+).

## CREATE VIEW

| Feature | MariaDB Support |
|---------|----------------|
| OR REPLACE | Yes |
| TEMPORARY | Yes |
| WITH CHECK OPTION | Yes |
| CASCADED/LOCAL | Yes |

## TRUNCATE

| Feature | MariaDB Support |
|---------|----------------|
| TRUNCATE TABLE | Yes |
| RESTART IDENTITY | No |
| CASCADE | No |

## Schema Support

MariaDB has no schema layer distinct from databases. `schema()` maps to `USE database`.

## Sequences

MariaDB supports `CREATE SEQUENCE` since version 10.3:

```sql
CREATE SEQUENCE order_seq START WITH 1 INCREMENT BY 1;
SELECT NEXTVAL(order_seq);
```

## Backend-Specific Expression Classes

| Expression | Purpose |
|-----------|---------|
| `MariaDBLoadDataExpression` | LOAD DATA INFILE |
| `MariaDBShowCreateTableExpression` | SHOW CREATE TABLE |
| `MariaDBShowColumnsExpression` | SHOW COLUMNS |
| Various `Show*Expression` | SHOW command wrappers |

---

# Part 2: ActiveRecord DDL Derivation

`ModelSchemaGenerator` derives DDL from your ActiveRecord model declarations. You define fields, table names, indexes, and constraints on the model class -- the framework generates the SQL.

## What Can Be Derived from Models

| Feature | Model-Integrated | How to Use |
|---------|-----------------|------------|
| Table creation | Yes | `ModelSchemaGenerator.generate_create_table()` |
| Column definitions | Yes | Declare fields on the model class |
| Indexes | Yes | `indexes()` class method |
| Constraints | Yes | `UseConstraint` annotations |
| Engine / CHARSET | Yes | `engine()`, `charset()` class methods |
| Table comment | Yes | `comment()` class method |
| Schema | Yes | `schema()` class method |
| Partitioning | **No** | Backend-specific expression classes only |
| Sequences | **No** | Backend-specific expression classes only |
| Triggers | **No** | Backend-specific expression classes only |
| Stored procedures | **No** | Backend-specific expression classes only |

## Creating a Table

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar

class User(ActiveRecord):
    id: int | None = None
    username: str
    email: str
    age: int
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

The generated SQL for MariaDB:

```sql
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `age` INT NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

## Backend-Specific Table Options

### ENGINE, CHARSET, COLLATE, COMMENT

```python
class User(ActiveRecord):
    @classmethod
    def engine(cls) -> str:
        return 'InnoDB'

    @classmethod
    def charset(cls) -> str:
        return 'utf8mb4'

    @classmethod
    def collate(cls) -> str:
        return 'utf8mb4_unicode_ci'

    @classmethod
    def comment(cls) -> str:
        return 'User accounts table'
```

## Generating DDL SQL

```python
from rhosocial.activerecord.base.ddl_generator import DDLGenerator

create_sql = DDLGenerator.generate_create_table(User)
print(create_sql)
```

## Running DDL

```python
# Sync
with User.connection() as conn:
    conn.execute(create_sql)

# Async
async with User.connection() as conn:
    await conn.execute(create_sql)
```

---

## See Also

- [Field Types](../backend_specific_features/field_types.md) -- DataType hierarchy and backend-specific types
- [Indexing](../backend_specific_features/indexing.md) -- index types and optimization
- [Partitioning](../backend_specific_features/partition.md) -- table partitioning strategies
- [Dialect Expressions](../backend_specific_features/dialect.md) -- feature detection and protocol system
- [Core: DDL](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/ddl)

AI Prompt: "How does DDL generation differ between MariaDB and MySQL?"
