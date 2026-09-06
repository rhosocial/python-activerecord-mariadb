# Index Types

## Overview

MariaDB supports various index types for query optimization.

## Index Types

### B-Tree Index (Default)

```python
from rhosocial.activerecord.backend.expression import CreateIndexExpression

# Standard B-tree index
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_name",
    table_name="users",
    columns=["name"],
)
sql, params = create_idx.to_sql()
# sql: CREATE INDEX idx_users_name ON users (name)
```

### Hash Index

```python
# Hash index (MEMORY engine only)
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"],
    index_type="HASH",
)
```

### Spatial Index

```python
# Spatial index (MyISAM/InnoDB)
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_locations_coords",
    table_name="locations",
    columns=["coordinates"],
    index_type="SPATIAL",
)
```

### Full-Text Index

```python
# Full-text index
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_articles_content",
    table_name="articles",
    columns=["title", "content"],
    index_type="FULLTEXT",
)
```

## Index Optimization

```sql
-- Check index usage
EXPLAIN SELECT * FROM users WHERE name = 'John';

-- Analyze index
ANALYZE TABLE users;
```

## See Also

- [EXPLAIN](./explain.md) — Query execution plans

💡 *AI Prompt:* "When should I use HASH vs B-Tree indexes in MariaDB?"
