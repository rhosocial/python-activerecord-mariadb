# MariaDB Specific Features

This section covers MariaDB-specific features that differ from other backends. rhosocial-activerecord uses a two-layer architecture for many features: a **core layer** provides common interfaces and default implementations, while each backend's **dialect layer** overrides formatting and adds backend-specific capabilities.

When you encounter a feature in this section, check whether it is a backend-specific extension or a core feature with backend-specific formatting -- the documentation will indicate which layer applies.

## Contents

- [Dialect Expressions](dialect.md): Two-layer expression system -- common core and MariaDB-specific overrides
- [Field Types](field_types.md): Core DataType hierarchy and MariaDB-specific type extensions
- [Indexing](indexing.md): MariaDB-specific index types and optimization strategies
- [EXPLAIN](explain.md): Query execution plan analysis (MariaDB-specific syntax)
- [Introspection](introspection.md): Database metadata queries and schema inspection
- [Partitioning](partition.md): Table partitioning (MariaDB-specific)

## Feature Highlights

| Feature | Common Layer | MariaDB-Specific Layer |
|---------|-------------|------------------------|
| Expressions | Core expression classes (Column, Literal, FunctionCall, etc.) | Dialect overrides and MariaDB-specific expression classes |
| Type System | Core DataType hierarchy (IntegerType, VarCharType, etc.) | MariaDB-specific DataType subclasses and type adapters |
| EXPLAIN | ExplainExpression interface | MariaDB-specific EXPLAIN syntax and result parsing |
| Introspection | Introspector interface | MariaDB-specific metadata queries (SHOW commands) |

## MariaDB-Specific Protocols

The MariaDB backend defines its own protocol interfaces for features unique to MariaDB:

| Protocol | Description |
|----------|-------------|
| `MariaDBDMLOperationSupport` | INSERT IGNORE, REPLACE INTO, LOAD DATA |
| `MariaDBTriggerSupport` | Trigger DDL (BEFORE/AFTER, INSTEAD OF) |
| `MariaDBTableSupport` | MariaDB table DDL options |
| `MariaDBSetTypeSupport` | SET data type support |
| `MariaDBJSONFunctionSupport` | JSON function support |
| `MariaDBSpatialSupport` | Spatial data types and functions |
| `MariaDBFullTextSearchSupport` | Full-text search with MATCH AGAINST |
| `MariaDBLockingSupport` | FOR UPDATE, FOR SHARE, SKIP LOCKED |
| `MariaDBModifyColumnSupport` | MODIFY/CHANGE COLUMN support |
| `MariaDBSequenceSupport` | SEQUENCE objects (10.3+) |
| `MariaDBReturningSupport` | RETURNING clause (10.5+, INSERT/DELETE only) |
| `MariaDBIntersectExceptSupport` | INTERSECT/EXCEPT (10.3+) |
| `MariaDBSystemVersioningSupport` | System-versioned tables (10.3+) |
| `MariaDBWindowFunctionSupport` | Window functions (10.2+) |
| `MariaDBCTESupport` | Common Table Expressions (10.2+) |
| `MariaDBPartitionSupport` | Table partitioning |

## Related Topics

- [Type Adapters](../type_adapters/README.md) -- type mapping and custom adapters
- [DDL Operations](../ddl/README.md) -- schema management
- [Core: Expression System](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/expression)
- [Core: Backend System](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend)
