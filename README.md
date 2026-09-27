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

Server versions this backend is tested against in CI: **10.2, 10.3, 10.4, 10.5,
10.6, 10.11, 11.4, 11.7, 11.8, 12.0, 12.2, 12.3, 13.0** (gating) and
**13.1-rc** (experimental, non-gating).

| Feature | Min Version | Notes |
|---------|-------------|-------|
| Basic operations | 10.2+ | Core functionality |
| CHECK constraints | 10.2.1+ | Enforced |
| Window functions | 10.2+ | ROW_NUMBER, RANK, etc. |
| CTEs | 10.2+ | WITH clauses, incl. recursive |
| Full-text search | 10.2+ | MATCH ... AGAINST |
| Generated columns | 10.2+ | Virtual/Stored columns |
| Spatial types | 10.2+ | GEOMETRY, POINT, spatial index |
| `ST_AsGeoJSON()` | 10.2.3+ | |
| JSON | 10.2.3+ | `JSON` alias for LONGTEXT, JSON functions |
| INTERSECT / EXCEPT | 10.3+ | Set operations |
| Sequences | 10.3+ | `CREATE SEQUENCE`, `NEXT VALUE FOR` |
| System versioning | 10.3+ | `WITH SYSTEM VERSIONING` |
| Invisible columns | 10.3+ | |
| SKIP LOCKED / NOWAIT | 10.3+ | Row-level locking control |
| `TRUNCATE ... WAIT` | 10.3+ | |
| Triggers (FOLLOWS/PRECEDES) | 10.2.3+ | |
| INSTEAD OF triggers | 10.4+ | View triggers |
| RETURNING (INSERT/DELETE/REPLACE) | 10.5+ | |
| `RENAME TABLE ... WAIT` | 10.3+ | |
| `EXPLAIN FORMAT=JSON` / `ANALYZE` | 10.6+ | |
| `ANALYZE TABLE ... PERSISTENT` | 10.5+ | |
| `JSON_TABLE` | 10.6+ | |
| `IS JSON` predicate | 12.3+ | |
| `TO_DATE()` | 12.3+ | |
| `UPDATE ... RETURNING` | 13.0+ | Single-table UPDATE only; pairs with `OLD_VALUE()` |
| `DENY ... ON ... TO ...` | 13.1+ | Negative grants |
| Native `->` / `->>` | 13.1+ | JSON **column** operands only; see JSON note below |

Not implemented: `QUALIFY`, ordered-set aggregates (`WITHIN GROUP`),
`LATERAL VIEW`, `ROW()` composite types, `MBR*` functions, `SOUNDEX`,
`PARTITION BY SYSTEM_TIME`, packages, domains, `SET PATH`,
`SET SESSION AUTHORIZATION`, cursors on prepared statements, optimizer hints
(`/*+ ... */`), the `VECTOR` type, and the `XML` type.

### JSON arrow operators

`->` and `->>` are always rendered as the equivalent
`JSON_EXTRACT(...)` / `JSON_UNQUOTE(JSON_EXTRACT(...))` calls, which behave
identically on every supported version. MariaDB 13.1 added a native
`column -> path` form, but it applies **only to a real JSON column** —
`CAST(x AS JSON) -> '$'` is a syntax error even on 13.1 — so it is not used as
the general-purpose rendering. `supports_json_arrow_operators_native()` reports
whether it is available.

### The `utf8` character set alias

`utf8` is a server-side **alias** whose meaning changed in MariaDB 13.1
(MDEV-30041): it resolved to `utf8mb3` on every release up to 13.0, and
resolves to `utf8mb4` from 13.1, because `old_mode` no longer sets
`UTF8_IS_UTF8MB3` by default.

```sql
CREATE TABLE t (s VARCHAR(50)) CHARACTER SET utf8
-- MariaDB <= 13.0  ->  utf8mb3_uca1400_ai_ci   (4-byte characters rejected)
-- MariaDB >= 13.1  ->  utf8mb4_uca1400_ai_ci   (4-byte characters accepted)
```

This backend resolves the alias to **`utf8mb3`** — the meaning it always had
before 13.1 — before emitting it, so one DDL statement produces one schema on
every supported server. Ask for `utf8mb4` explicitly if you want 4-byte
storage.

Note this affects the DDL context only: `SET NAMES utf8` already resolved to
`utf8mb4` on every version tested, including 12.2.

### Reserved words

Identifiers are quoted by default. The reserved-word check is
version-aware, because MariaDB adds reserved words in otherwise-minor
releases — `conversion` and `to_date` became reserved in **12.3**, and `deny`
in **13.1**. An unquoted identifier matching a reserved word emits an
`IdentifierQuotingWarning`; it is a warning, not an error, so passing
`need_quote=False` remains possible at your own risk.

## Supported Versions Policy

| Line | Status | Rationale |
|------|--------|-----------|
| **12.3** | **Recommended baseline** | LTS, maintained to June 2029 |
| 13.0 | Supported, opt-in | GA (rolling, non-LTS) |
| 13.1 | Not recommended for production | Release candidate; `utf8` alias change and `mariadb-dump` behaviour change need independent validation |
| 11.8 | Supported | Previous LTS |
| 10.2 – 11.7 | Supported | Older lines, CI-covered |

**On unrecognised newer versions.** There is no upper bound: the backend does
not reject a version it has not seen. It behaves as follows.

- Feature gates resolve to "enabled" when the server is newer than a
  feature's introduction version, so **new syntax is assumed available**.
  If that assumption is wrong the server rejects the statement.
- Removals are handled explicitly, per feature. For example
  `supports_function_name("des_encrypt")` returns `False` on 13.0+, where the
  function was removed.
- Behaviour changes that are *not* new syntax cannot be detected from the
  version alone. The `utf8` alias is handled by resolving the alias to an
  unambiguous spelling rather than by branching on version.

When bumping to a new major, check that release's "Incompatible Changes"
section before assuming compatibility.

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