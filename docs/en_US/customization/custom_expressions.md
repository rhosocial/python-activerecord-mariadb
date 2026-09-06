# Custom Expressions

## Overview

The MariaDB backend extends core expression classes with MariaDB-specific SQL syntax. You can create new expression types to add support for MariaDB-unique SQL constructs.

## Expression Design Principles

Expressions are **declarative** — they collect all parameters and delegate SQL generation to the dialect:

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, **params):
        self.dialect = dialect
        self.params = params

    def to_sql(self, dialect):
        # Delegate to dialect for SQL generation
        return dialect.format_my_expression(**self.params)
```

## Creating Custom Expressions

### Step 1: Define the Expression Class

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class MariaDBJSONExpression(BaseExpression):
    """MariaDB JSON expression for JSON_EXTRACT."""

    def __init__(self, dialect, column, path):
        self.dialect = dialect
        self.column = column
        self.path = path

    def to_sql(self, dialect):
        return f"JSON_EXTRACT({self.column.to_sql(dialect)}, '{self.path}')"
```

### Step 2: Register with Dialect

```python
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect

class CustomMariaDBDialect(MariaDBDialect):
    def format_json_extract(self, column, path):
        return f"JSON_EXTRACT({column}, '{path}')"
```

### Step 3: Use in Code

MariaDB uses backtick quoting for identifiers:

```python
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.core import FunctionCall

# Build an expression using the expression system
expr = FunctionCall(
    dialect, "JSON_EXTRACT",
    Column(dialect, "data"),
    Literal(dialect, "$.name"),
)
sql, params = expr.to_sql()
# sql: JSON_EXTRACT(`data`, %s)
# params: ('$.name',)
```

## Operator Mixins

Use operator mixins for common comparison and arithmetic operations:

```python
from rhosocial.activerecord.backend.expression.operators import ComparisonMixin, ArithmeticMixin
from rhosocial.activerecord.backend.expression import Column

class MyExpression(ComparisonMixin, ArithmeticMixin, BaseExpression):
    pass

# Now supports ==, !=, <, >, +, -, *, /, etc.
expr = MyExpression(dialect, Column(dialect, "amount")) > 100
sql, params = expr.to_sql()
# sql: `amount` > %s
# params: (100,)
```

## Serialization

Expressions support serialization/deserialization for caching and logging:

```python
# Serialize
data = expr.serialize()

# Deserialize
expr = BaseExpression.deserialize(data)
```

## See Also

- [Core Expression System](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/expression) — expression base classes and operators
- [MariaDB Dialect](../backend_specific_features/dialect.md) — MariaDB-specific SQL functions

💡 *AI Prompt:* "How do I create a custom expression for MariaDB JSON functions?"
