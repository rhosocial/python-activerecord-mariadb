# EXPLAIN Support

## Overview

MariaDB provides EXPLAIN support for query execution plan analysis.

## Basic Usage

```python
from rhosocial.activerecord.backend.expression.statements import ExplainFormat

# Simple EXPLAIN
result = User.query().explain().all()

# EXPLAIN FORMAT=JSON
result = User.query().explain(format=ExplainFormat.JSON).all()

# EXPLAIN FORMAT=TREE
result = User.query().explain(format=ExplainFormat.TREE).all()
```

## EXPLAIN ANALYZE

```python
# MariaDB 10.6+ supports EXPLAIN ANALYZE
result = User.query().explain(analyze=True).all()
```

## Output Formats

| Format | Description |
|--------|-------------|
| TEXT | Default format |
| JSON | JSON output |
| TREE | Tree-structured output (MariaDB 10.6+) |

## See Also

- [Troubleshooting](../troubleshooting/performance.md) — Query optimization

💡 *AI Prompt:* "How to analyze slow queries in MariaDB?"
