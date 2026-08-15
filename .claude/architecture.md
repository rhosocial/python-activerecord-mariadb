# Architecture Guide - python-activerecord-mariadb

> MariaDB backend implementation for rhosocial-activerecord

## Project Overview

| Item | Value |
|------|-------|
| **Database** | MariaDB |
| **Python Driver** | mariadb |
| **Python Version** | 3.8+ |

## Directory Structure

```
python-activerecord-mariadb/
├── src/rhosocial/activerecord/backend/impl/mariadb/
│   ├── __init__.py           # Backend initialization
│   ├── __main__.py           # CLI entry point
│   ├── backend/              # Backend implementation
│   │   ├── __init__.py
│   │   ├── async_backend.py  # Async backend
│   ├── config.py             # Configuration
│   ├── dialect.py            # MariaDB dialect
│   ├── protocols.py          # Protocol definitions
│   ├── transaction.py       # Transaction management
│   ├── adapters.py           # Type adapters
│   ├── mixins.py             # MariaDB-specific mixins
│   ├── cli/                  # CLI commands
│   ├── expression/           # MariaDB-specific expressions
│   ├── functions/            # MariaDB-specific functions
│   ├── introspection/        # Schema introspection
│   └── show/                 # SHOW statements
├── tests/
│   └── rhosocial/activerecord_mariadb_test/
└── pyproject.toml
```

## MariaDB-Specific Features

- **JSON functions**: JSON_ARRAY, JSON_OBJECT, etc.
- **Window functions**: Supported in newer versions
- **Virtual columns**: Generated columns
- **Sequence support**: Auto-increment alternatives

## Expression-Dialect System

Like all backends, MariaDB uses the Expression-Dialect separation:
- Expression classes define query structure
- Dialect classes handle SQL generation

## Reference

- [Core architecture](../python-activerecord/.claude/architecture.md)
- [Backend development guide](../python-activerecord/.claude/backend_development.md)