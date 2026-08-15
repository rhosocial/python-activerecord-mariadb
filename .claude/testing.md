# Testing Guide - python-activerecord-mariadb

> AI Assistant Note: This document covers MariaDB backend-specific testing requirements.

## Project-Specific Information

| Item | Value |
|------|-------|
| **Python Version** | 3.8+ |
| **Database Driver** | mariadb |
| **Free-Threading Support** | ✅ Yes |

## Dependencies

```toml
dependencies = [
    "rhosocial-activerecord>=1.0.0.dev0,<2.0.0",
    "mariadb>=2.0.0rc2"
]
```

## Quick Test Commands

```bash
# Activate virtual environment and set PYTHONPATH
cd /mnt/i/GitHubRepositories/rhosocial/python-activerecord-mariadb
source .venv/bin/activate
export PYTHONPATH=src

# Run tests
pytest
```

## Key Differences from Core

- Uses MariaDB-specific dialect in `src/rhosocial/activerecord/backend/impl/mariadb/dialect.py`
- Schema files in `tests/rhosocial/activerecord_mariadb_test/`
- Provider implementation in `tests/providers/`

## Reference

- [Core testing guide](../python-activerecord/.claude/testing.md)
- [MariaDB backend development](../python-activerecord/.claude/backend_development.md)