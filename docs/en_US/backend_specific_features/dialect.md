# MariaDB Dialect Expressions

## Overview

MariaDB provides its own SQL dialect with features that extend standard SQL.

## JSON Functions

### JSON Arrow Operators

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.operators import BinaryExpression

# Get JSON value at path (->>)
expr = BinaryExpression(dialect, "=>",
    Column(dialect, "attributes").json_arrow_text("brand"),
    Literal(dialect, "Dell"))
sql, params = expr.to_sql()
# sql: `attributes`->>'brand' = %s
# params: ('Dell',)
```

## System-Versioned Tables

MariaDB 10.3+ supports system-versioned tables:

```sql
CREATE TABLE orders (
    id INT PRIMARY KEY,
    amount DECIMAL(10,2),
    valid_from TIMESTAMP(6) GENERATED ALWAYS AS ROW START,
    valid_to TIMESTAMP(6) GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME(valid_from, valid_to)
) WITH SYSTEM VERSIONING;
```

## RETURNING Clause

MariaDB 10.5+ supports RETURNING for DML operations:

```python
# INSERT RETURNING
user = User(name="John")
user.save()
# Returns the inserted row with generated id

# UPDATE RETURNING
User.query().where(User.c.id == 1).update(name="Jane")
# Returns affected rows
```

## See Also

- [Field Types](./field_types.md) — MariaDB-specific data types
- [Indexing](./indexing.md) — Index types and optimization

💡 *AI Prompt:* "How does MariaDB's system-versioning work?"
