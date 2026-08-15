# rhosocial-activerecord-mariadb ($\rho_{\mathbf{AR}\text{-mariadb}}$)

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord-mariadb.svg)](https://badge.fury.io/py/rhosocial-activerecord-mariadb)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord-mariadb.svg)](https://pypi.org/project/rhosocial-activerecord-mariadb/)
[![Tests](https://github.com/rhosocial/python-activerecord-mariadb/actions/workflows/test.yml/badge.svg)](https://github.com/rhosocial/python-activerecord-mariadb/actions)
[![Coverage Status](https://codecov.io/gh/rhosocial/python-activerecord-mariadb/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rhosocial/python-activerecord-mariadb/tree/main)
[![Apache 2.0 License](https://img.shields.io/github/license/rhosocial/python-activerecord-mariadb.svg)](https://github.com/rhosocial/python-activerecord-mariadb/blob/main/LICENSE)
[![Powered by vistart](https://img.shields.io/badge/Powered_by-vistart-blue.svg)](https://github.com/vistart)

<div align="center">
    <img src="https://raw.githubusercontent.com/rhosocial/python-activerecord/main/docs/images/logo.svg" alt="rhosocial ActiveRecord Logo" width="200"/>
    <h3>MariaDB Backend for rhosocial-activerecord</h3>
    <p><b>MariaDB-Compatible Features · System Versioning · Sync & Async</b></p>
</div>

> **Note**: This is a backend implementation for [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord). It cannot be used standalone.

## Why This Backend?

### 1. MariaDB-Specific Optimizations

| Feature | This Backend | Generic Solutions |
|---------|-------------|-------------------|
| **Full-Text Search** | Native `MATCH ... AGAINST` | LIKE-based workarounds |
| **JSON Operations** | `JSON_EXTRACT`, `->>`, `->` | Serialize/deserialize overhead |
| **Upsert** | `INSERT ... ON DUPLICATE KEY UPDATE` | Manual check-then-insert |
| **System Versioning** | `WITH SYSTEM VERSIONING` | Application-level audit logs |

### 2. True Sync-Async Parity

Same API surface for both sync and async operations:

```python
# Sync
users = User.query().where(User.c.age >= 18).all()

# Async - just add await
users = await User.query().where(User.c.age >= 18).all()
```

### 3. Built for Production

- **Connection pooling** with configurable pool sizes
- **Transaction support** with proper isolation levels
- **Error mapping** from MariaDB error codes to Python exceptions
- **Type adapters** for MariaDB-specific data types

## Quick Start

### Installation

```bash
pip install rhosocial-activerecord-mariadb
```

### Basic Usage

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from typing import Optional

class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    name: str
    email: str

# Configure
config = MariaDBConnectionConfig(
    host="localhost",
    port=3306,
    database="myapp",
    username="user",
    password="password"
)
User.configure(config, MariaDBBackend)

# Use
user = User(name="Alice", email="alice@example.com")
user.save()

# Query with MariaDB full-text search
results = User.query().where(
    "MATCH(name, email) AGAINST(? IN BOOLEAN MODE)",
    ("+Alice",)
).all()
```

> 💡 **AI Prompt**: "Show me how to use JSON operations in MariaDB with this backend"

## MariaDB-Specific Features

### Full-Text Search

Native MariaDB full-text search support:

```python
# Boolean mode full-text search
Article.query().where(
    "MATCH(title, content) AGAINST(? IN BOOLEAN MODE)",
    ("+python -java",)
).all()

# Natural language mode
Article.query().where(
    "MATCH(title, content) AGAINST(?)",
    ("database optimization",)
).all()
```

### JSON Operations

Query JSON columns using MariaDB's native JSON functions:

```python
# Extract JSON value
User.query().where("settings->>'$.theme' = ?", ("dark",)).all()

# JSON contains
Product.query().where("JSON_CONTAINS(tags, ?)", ('"featured"',)).all()
```

### System-Versioned Tables

MariaDB's temporal tables store full row history:

```python
# Query historical rows
User.query().where(
    "user_id = ? FOR SYSTEM_TIME BETWEEN ? AND ?",
    (1, "2026-01-01", "2026-06-30"),
).all()
```

### Upsert (ON DUPLICATE KEY UPDATE)

Efficient insert-or-update operations:

```python
# Will update on duplicate key
User.insert_or_update(
    name="Alice",
    email="alice@example.com",
    update_fields=["name"]  # Only update name on conflict
)
```

## Requirements

- **Python**: 3.9+ (including 3.13t/3.14t free-threaded builds)
- **Core**: `rhosocial-activerecord>=1.0.0`
- **Driver**: `mariadb>=2.0.0`

## MariaDB Version Compatibility

| Feature | Min Version | Notes |
|---------|-------------|-------|
| Basic operations | 10.2+ | Core functionality |
| JSON | 10.2+ | `JSON` alias for LONGTEXT, JSON functions |
| Window functions | 10.2+ | ROW_NUMBER, RANK, etc. |
| CTEs | 10.2+ | WITH clauses |
| Full-text search | 10.2+ | MATCH ... AGAINST |
| Generated columns | 10.2+ | Virtual/Stored columns |
| CHECK constraints | 10.2+ | Enforced |
| DEFAULT expressions | 10.2+ | Expression defaults |
| System versioning | 10.3+ | Temporal tables |
| Sequences | 10.3+ | `CREATE SEQUENCE` |
| GROUPING SETS | 10.3+ | Advanced grouping |
| INET6 type | 10.5+ | Native IPv6 |
| SKIP LOCKED | 10.6+ | Row-level locking control |

**Recommended**: MariaDB 10.6+ for optimal feature support.

## Get Started with AI Code Agents

This project supports AI-assisted development. Clone and open in your preferred tool:

```bash
git clone https://github.com/rhosocial/python-activerecord-mariadb.git
cd python-activerecord-mariadb
```

### Example AI Prompts

- "How do I configure connection pooling for MariaDB?"
- "Show me how to use system-versioned tables"
- "How do I use MariaDB-specific JSON operators?"
- "Create a model with a FULLTEXT index"

### For Any LLM

Feed the documentation files in `docs/` to your preferred LLM for context-aware assistance.

## Testing

> ⚠️ **CRITICAL**: Tests MUST run serially. Do NOT use `pytest -n auto` or parallel execution.

```bash
# Run all tests
PYTHONPATH=src pytest tests/

# Run specific feature tests
PYTHONPATH=src pytest tests/rhosocial/activerecord_mariadb_test/feature/basic/
PYTHONPATH=src pytest tests/rhosocial/activerecord_mariadb_test/feature/query/
```

See the [Testing Documentation](https://github.com/rhosocial/python-activerecord/blob/main/.claude/testing.md) for details.

## Documentation

- **[Getting Started](docs/en_US/getting_started/)** — Installation and configuration
- **[MariaDB Features](docs/en_US/mariadb_specific_features/)** — MariaDB-specific capabilities
- **[Type Adapters](docs/en_US/type_adapters/)** — Data type handling
- **[Transaction Support](docs/en_US/transaction_support/)** — Transaction management

## Comparison with Other Backends

| Feature | MariaDB | MySQL | SQLite |
|---------|---------|-------|--------|
| **Full-Text Search** | ✅ Native | ✅ Native | ⚠️ FTS5 extension |
| **JSON Type** | ✅ JSON | ✅ JSON | ⚠️ JSON1 extension |
| **System Versioning** | ✅ | ❌ | ❌ |
| **Upsert** | ✅ ON DUPLICATE KEY | ✅ ON DUPLICATE KEY | ✅ ON CONFLICT |
| **Returning** | ✅ 10.5+ | ❌ | ✅ RETURNING |

> 💡 **AI Prompt**: "When should I choose MariaDB over MySQL for my project?"

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Apache License 2.0](LICENSE) — Copyright © 2026 [vistart](https://github.com/vistart)

---

<div align="center">
    <p><b>Built with ❤️ by the rhosocial team</b></p>
    <p><a href="https://github.com/rhosocial/python-activerecord-mariadb">GitHub</a> · <a href="https://docs.python-activerecord.dev.rho.social/backends/mariadb.html">Documentation</a> · <a href="https://pypi.org/project/rhosocial-activerecord-mariadb/">PyPI</a></p>
</div>