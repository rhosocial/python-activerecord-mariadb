# Installation Guide

## System Requirements

- Python 3.8+
- MariaDB 10.2+ (MariaDB 10.5+ recommended for full feature support)
- pip or poetry

## Installation Steps

### 1. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Core Library and MariaDB Backend

```bash
# Install core library
pip install rhosocial-activerecord

# Install MariaDB backend
pip install rhosocial-activerecord-mariadb
```

### 3. Install MariaDB Driver

This backend uses the `mariadb` Python package (v2.0.0+) for both sync and async:

```bash
pip install mariadb>=2.0.0
```

The `mariadb` package provides:
- Synchronous connection via `mariadb.connect()`
- Asynchronous connection via `mariadb.asyncConnect()` (v2.0.0+)

**Note**: The async driver is the same package -- no separate async package is required.

## Verify Installation

```python
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

backend = MariaDBBackend(
    host='localhost',
    port=3306,
    database='test_db',
    username='root',
    password='password'
)
backend.connect()
print(f"MariaDB version: {backend.get_server_version()}")
backend.disconnect()
```

## Version-Specific Features

The MariaDB backend adapts to the server version. Key feature boundaries:

| Feature | Minimum Version |
|---------|----------------|
| Window functions | 10.2 |
| CTE | 10.2 |
| JSON functions | 10.2.3 |
| JSON arrow operators | 10.2.7 |
| INTERSECT/EXCEPT | 10.3 |
| SEQUENCE | 10.3 |
| System-versioned tables | 10.3 |
| SKIP LOCKED | 10.3 |
| RETURNING clause | 10.5 |
| EXPLAIN FORMAT/ANALYZE | 10.6 |

The dialect automatically detects the server version via `introspect_and_adapt()` and adjusts feature availability accordingly.

AI Prompt: "What MariaDB version should I use for production?"
