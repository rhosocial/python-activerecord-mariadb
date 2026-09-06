# Performance Issues

## Overview

This section covers MariaDB performance issues and optimization methods.

## Slow Query Analysis

### Enabling Slow Query Log

```sql
-- View slow query configuration
SHOW VARIABLES LIKE 'slow_query_log%';

-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
```

### Using EXPLAIN to Analyze Queries

Use the expression system to build EXPLAIN statements rather than executing raw SQL. Build the query with expression classes first, then wrap it in an `ExplainExpression`:

```python
from rhosocial.activerecord.backend.expression.statements.explain import (
    ExplainExpression,
    ExplainOptions,
    ExplainFormat,
)

# Build a query expression using the expression system
query = User.query().where(User.c.name == "Tom").select(User.c.id, User.c.name)

# Basic EXPLAIN
explain = ExplainExpression(dialect, statement=query)
sql, params = explain.to_sql()
# sql: EXPLAIN SELECT `id`, `name` FROM `users` WHERE `name` = %s
# params: ('Tom',)

# EXPLAIN FORMAT=JSON (MariaDB 10.6+)
explain_json = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(format=ExplainFormat.JSON),
)

# EXPLAIN ANALYZE (MariaDB 10.6+)
explain_analyze = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(analyze=True),
)
```

> **Note**: `EXPLAIN FORMAT=JSON` and `EXPLAIN ANALYZE` require MariaDB 10.6+.

## Common Performance Issues

### 1. Missing Index

```sql
-- Add index
CREATE INDEX idx_name ON users(name);
```

### 2. SELECT *

```python
# Avoid SELECT *, only query required columns
users = User.query().select(User.c.id, User.c.name).all()
```

### 3. N+1 Query Problem

```python
# Use with_() to eagerly load related data and avoid N+1 queries
users = User.query().with_('posts').all()

# Load nested relations
users = User.query().with_('posts.comments').all()

# Load with query modifier
users = User.query().with_(('posts', lambda q: q.limit(5))).all()
```

### 4. JSON Type Performance

MariaDB supports native JSON storage since 10.2.3. `dict`/`list` fields are serialized via the `MariaDBJSONAdapter`:

```python
from rhosocial.activerecord.backend.impl.mariadb.adapters import MariaDBJSONAdapter

adapter = MariaDBJSONAdapter()
data = {"name": "Tom", "tags": ["admin"]}

# Convert to database value
db_value = adapter.to_database(data, dict)
# Output: '{"name": "Tom", "tags": ["admin"]}'

# Convert back to Python
python_value = adapter.from_database(db_value, dict)
# Output: {'name': 'Tom', 'tags': ['admin']}
```

**Recommendation**: For new projects, use MariaDB 10.2.3+ (preferably 10.6+ LTS) for full JSON support including arrow operators (`->>`) and `JSON_TABLE`.

## Connection Timeouts

```python
config = MariaDBConnectionConfig(
    connect_timeout=30,
    read_timeout=60,
    write_timeout=60,
)
```

## See Also

- [EXPLAIN Support](../backend_specific_features/explain.md) — query execution plan analysis
- [Indexing](../backend_specific_features/indexing.md) — index types and optimization

💡 *AI Prompt:* "How to optimize MariaDB query performance?"
